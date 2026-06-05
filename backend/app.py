from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import cv2
import hashlib
import base64
import numpy as np
import asyncio
import secrets
import re
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import logging

try:
    from pydantic import EmailStr
except ImportError:
    # Fallback when optional email-validator dependency is missing.
    EmailStr = str

# Load environment variables from dotenv.
# This will load .env from current/parent folders and also explicitly load backend/.env if available.
load_dotenv()
backend_env = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(backend_env):
    load_dotenv(backend_env)
    print(f"Loading backend environment from: {backend_env}")
else:
    print("backend/.env not found, falling back to root or parent .env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path so IDE can resolve database and inference imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db
from email_service import send_otp_email, validate_email_config
from inference import detector

app = FastAPI(title="Deepfake Detection API", version="2.0")

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB
EMAIL_OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def validate_password_strength(password: str) -> Optional[str]:
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must include at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must include at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must include at least one special character."
    return None


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


class HealthResponse(BaseModel):
    status: str
    database: str
    model_loaded: bool


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SendRegisterOtpRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str


class VerifyRegisterOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str


@app.on_event("startup")
async def startup_event():
    db.connect()

    # Validate email configuration
    email_valid, email_msg = validate_email_config()
    if email_valid:
        logger.info(f"Email service: {email_msg}")
    else:
        logger.warning(f"Email service: {email_msg}")
        print(f"WARNING: {email_msg}")


@app.on_event("shutdown")
async def shutdown_event():
    db.close()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    db_status = "connected" if db.db is not None else "disconnected"
    model_status = detector.model_loaded
    return {
        "status": "online",
        "database": db_status,
        "model_loaded": model_status,
    }


async def dispatch_otp_email(email: str, otp: str, subject: str, purpose: str):
    try:
        await send_otp_email(email, otp)
    except Exception as e:
        logger.exception(f"Failed to send OTP email to {email}: {e}")
        raise RuntimeError(f"Unable to send OTP email: {str(e)}")


@app.post("/send-register-otp")
async def send_register_otp(payload: SendRegisterOtpRequest):
    username = payload.username.strip()
    email = payload.email.strip().lower()
    password = payload.password
    confirm_password = payload.confirm_password

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    password_error = validate_password_strength(password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    existing_user = db.get_user_by_email(email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    otp_code = generate_otp_code()
    hashed_password = hash_password(password)
    payload_data = {"username": username, "password_hash": hashed_password}
    saved = db.create_otp_record(email, "register", otp_code, payload=payload_data, expiry_minutes=EMAIL_OTP_EXPIRY_MINUTES)
    if not saved:
        raise HTTPException(status_code=500, detail="Unable to create OTP record.")

    try:
        await dispatch_otp_email(email, otp_code, "Your registration OTP", "account registration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to send OTP email: {e}")

    return {"status": "success", "message": "OTP sent to your email."}


@app.post("/verify-register-otp")
async def verify_register_otp(payload: VerifyRegisterOtpRequest):
    email = payload.email.strip().lower()
    otp = payload.otp.strip()

    record, error = db.validate_otp(email, otp, "register", max_attempts=MAX_OTP_ATTEMPTS)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not record:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    payload_data = record.get("payload") or {}
    username = payload_data.get("username")
    password_hash = payload_data.get("password_hash")

    if not username or not password_hash:
        raise HTTPException(status_code=500, detail="Registration payload is missing.")

    success, message = db.create_user(username, email, password_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    db.mark_otp_used(record["_id"])
    user = db.get_user_by_email(email)
    return {"status": "success", "message": "Registration completed.", "user": {"username": user["username"], "email": user["email"]}}


@app.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.strip().lower()
    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="Email is not registered.")

    otp_code = generate_otp_code()
    saved = db.create_otp_record(email, "reset", otp_code, expiry_minutes=EMAIL_OTP_EXPIRY_MINUTES)
    if not saved:
        raise HTTPException(status_code=500, detail="Unable to create OTP record.")

    try:
        await dispatch_otp_email(email, otp_code, "Your password reset OTP", "password reset")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to send OTP email: {e}")

    return {"status": "success", "message": "OTP sent to your email."}


@app.post("/verify-reset-otp")
async def verify_reset_otp(payload: VerifyResetOtpRequest):
    email = payload.email.strip().lower()
    otp = payload.otp.strip()
    _, error = db.validate_otp(email, otp, "reset", max_attempts=MAX_OTP_ATTEMPTS)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {"status": "success", "message": "OTP verified. You can reset your password."}


@app.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    email = payload.email.strip().lower()
    otp = payload.otp.strip()
    new_password = payload.new_password
    confirm_password = payload.confirm_password

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    password_error = validate_password_strength(new_password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    record, error = db.validate_otp(email, otp, "reset", max_attempts=MAX_OTP_ATTEMPTS)
    if error:
        raise HTTPException(status_code=400, detail=error)

    success = db.update_user_password(email, hash_password(new_password))
    if not success:
        raise HTTPException(status_code=500, detail="Unable to update password.")

    db.mark_otp_used(record["_id"])
    return {"status": "success", "message": "Password reset successfully."}


@app.post("/predict-image")
async def predict_image(file: UploadFile = File(...), user_email: Optional[str] = Form(None)):
    """
    Accepts an image upload, checks for duplicates, runs inference,
    and stores the result + Base64 image in MongoDB.
    """

    if not detector.model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model is unavailable. Train the model and place it at models/best_model.pth.",
        )

    # ── 1. Validate MIME type ────────────────────────────────────
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    # ── 2. Read raw bytes once ───────────────────────────────────
    raw_bytes = await file.read()

    # ── 3. File-size validation (must be ≤ 8 MB) ────────────────
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File too large. Please upload image below 8MB.",
        )

    # ── 4. Deterministic hash for duplicate detection ────────────
    image_hash = hashlib.sha256(raw_bytes).hexdigest()

    # ── 5. Check for duplicate for this user ─────────────────────
    existing = db.find_by_hash(image_hash, user_email)
    if existing:
        stored_confidence = existing["confidence_score"]

        if str(existing["prediction"]).lower() == "real":
            display_confidence = 1 - stored_confidence
        else:
            display_confidence = stored_confidence

        return {
            "status": "success",
            "prediction": existing["prediction"],
            "confidence": f"{display_confidence * 100:.2f}%",
            "confidence_score": display_confidence,
            "duplicate": True,
            "message": "This image was already analyzed. Showing previous result.",
}
    # ── 6. Decode to numpy for inference ─────────────────────────
    try:
        np_arr = np.frombuffer(raw_bytes, np.uint8)
        image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise ValueError("Could not decode image file.")
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    # ── 7. Run model inference ───────────────────────────────────
    try:
        prediction, confidence = detector.predict_image(image_rgb)
        if str(prediction).lower() == "real":
            display_confidence = 1 - confidence
        else:
            display_confidence = confidence
    except Exception as e:
        logger.exception("Inference error")
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    # ── 8. Encode image as Base64 for MongoDB storage ────────────
    image_base64 = base64.b64encode(raw_bytes).decode("utf-8")

    # ── 9. Store in MongoDB ──────────────────────────────────────
    db.log_prediction(
        file_name=file.filename,
        file_type="image",
        mime_type=file.content_type,
        prediction=prediction,
        confidence_score=confidence,
        image_base64=image_base64,
        image_hash=image_hash,
        user_email=user_email,
    )

    return {
        "status": "success",
        "prediction": prediction,
        "confidence": f"{display_confidence * 100:.2f}%",
        "confidence_score": display_confidence,
        "duplicate": False,
    }


@app.get("/history")
async def get_history(limit: int = 50, email: Optional[str] = None):
    """
    Returns prediction history with embedded Base64 image data.
    Old records without image_base64 will have that field set to null.
    """
    try:
        history = db.get_history(limit, email)
        return {"status": "success", "data": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/register")
async def register(payload: RegisterRequest):
    username = payload.username.strip()
    email = payload.email.strip().lower()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    password_hash = hash_password(payload.password)
    success, message = db.create_user(username, email, password_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "status": "success",
        "message": message,
        "user": {
            "username": username,
            "email": email,
        },
    }


@app.post("/login")
async def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    is_valid_password = verify_password(payload.password, user["password_hash"])
    if not is_valid_password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "status": "success",
        "message": "Login successful.",
        "user": {
            "username": user["username"],
            "email": user["email"],
        },
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    reload = os.getenv("API_RELOAD", "True").lower() == "true"

    uvicorn.run("app:app", host=host, port=port, reload=reload)
