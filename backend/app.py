from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import cv2
import hashlib
import base64
import numpy as np
import secrets
import re
from typing import Optional
from dotenv import load_dotenv
import logging

try:
    from pydantic import EmailStr
except ImportError:
    EmailStr = str

# ── Environment ──────────────────────────────────────────────────────
load_dotenv()
backend_env = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(backend_env):
    load_dotenv(backend_env)
    print(f"Loaded backend env: {backend_env}")
else:
    print("backend/.env not found, using root .env")

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Internal imports ─────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db
from email_service import send_otp_email, validate_email_config
from inference import detector


# ════════════════════════════════════════════════════════════════════
# LIFESPAN  (replaces deprecated @app.on_event)
# ════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────
    logger.info("Starting up Deepfake Detection API...")
    db.connect()

    email_valid, email_msg = validate_email_config()
    if email_valid:
        logger.info(f"Email service: {email_msg}")
    else:
        logger.warning(f"Email service misconfigured: {email_msg}")

    logger.info(f"Model status: {'ready' if detector.is_ready() else 'NOT loaded'}")
    logger.info(f"Detector: {detector}")

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("Shutting down...")
    db.close()


# ════════════════════════════════════════════════════════════════════
# APP
# ════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Deepfake Detection API",
    version="2.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
# allow_origins=["*"] + allow_credentials=True is rejected by browsers.
# List explicit origins instead.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",   # alternate dev
        FRONTEND_URL,              # production frontend from .env
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES      = 8 * 1024 * 1024   # 8 MB
EMAIL_OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS         = 5
MIN_IMAGE_DIMENSION      = 10               # px — reject tiny/corrupt images


# ════════════════════════════════════════════════════════════════════
# AUTH HELPERS
# ════════════════════════════════════════════════════════════════════
def hash_password(password: str) -> str:
    """
    SHA-256 password hash.
    NOTE: For production use bcrypt or argon2 instead.
    This is acceptable for a college/demo project but must be
    upgraded before any real deployment.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def validate_password_strength(password: str) -> Optional[str]:
    """
    Returns an error string if password is weak, else None.
    Applied consistently on BOTH /register and /send-register-otp.
    """
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


# ════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════════
class HealthResponse(BaseModel):
    status: str
    database: str
    model_loaded: bool
    model_device: str


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


# ════════════════════════════════════════════════════════════════════
# EMAIL HELPER
# ════════════════════════════════════════════════════════════════════
async def dispatch_otp_email(email: str, otp: str):
    """Send OTP email. Raises RuntimeError on failure."""
    try:
        await send_otp_email(email, otp)
    except Exception as e:
        logger.exception(f"Failed to send OTP to {email}")
        raise RuntimeError(f"Unable to send OTP email: {e}")


# ════════════════════════════════════════════════════════════════════
# HEALTH
# ════════════════════════════════════════════════════════════════════
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Returns API, database, and model status.
    Useful for frontend loading screens and monitoring.
    """
    status = detector.get_status()
    return {
        "status":       "online",
        "database":     "connected" if db.db is not None else "disconnected",
        "model_loaded": status["model_loaded"],
        "model_device": status["device"],
    }


# ════════════════════════════════════════════════════════════════════
# REGISTRATION (OTP flow)
# ════════════════════════════════════════════════════════════════════
@app.post("/send-register-otp")
async def send_register_otp(payload: SendRegisterOtpRequest):
    username         = payload.username.strip()
    email            = payload.email.strip().lower()
    password         = payload.password
    confirm_password = payload.confirm_password

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    password_error = validate_password_strength(password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    if db.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email is already registered.")

    otp_code        = generate_otp_code()
    hashed_password = hash_password(password)
    payload_data    = {"username": username, "password_hash": hashed_password}

    saved = db.create_otp_record(
        email,
        "register",
        otp_code,
        payload=payload_data,
        expiry_minutes=EMAIL_OTP_EXPIRY_MINUTES,
    )
    if not saved:
        raise HTTPException(status_code=500, detail="Unable to create OTP record.")

    try:
        await dispatch_otp_email(email, otp_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "message": "OTP sent to your email."}


@app.post("/verify-register-otp")
async def verify_register_otp(payload: VerifyRegisterOtpRequest):
    email = payload.email.strip().lower()
    otp   = payload.otp.strip()

    record, error = db.validate_otp(email, otp, "register", max_attempts=MAX_OTP_ATTEMPTS)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not record:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    payload_data  = record.get("payload") or {}
    username      = payload_data.get("username")
    password_hash = payload_data.get("password_hash")

    if not username or not password_hash:
        raise HTTPException(status_code=500, detail="Registration payload is missing.")

    success, message = db.create_user(username, email, password_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    db.mark_otp_used(record["_id"])
    user = db.get_user_by_email(email)

    return {
        "status":  "success",
        "message": "Registration completed.",
        "user":    {"username": user["username"], "email": user["email"]},
    }


# ════════════════════════════════════════════════════════════════════
# REGISTRATION (direct — no OTP)
# ════════════════════════════════════════════════════════════════════
@app.post("/register")
async def register(payload: RegisterRequest):
    """
    Direct registration without OTP.
    Uses the same password validation as the OTP flow.
    """
    username = payload.username.strip()
    email    = payload.email.strip().lower()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    # Consistent with OTP path — same strength requirements
    password_error = validate_password_strength(payload.password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    password_hash = hash_password(payload.password)
    success, message = db.create_user(username, email, password_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "status":  "success",
        "message": message,
        "user":    {"username": username, "email": email},
    }


# ════════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════════
@app.post("/login")
async def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    user  = db.get_user_by_email(email)

    # Same error message for missing user and wrong password
    # prevents user enumeration attacks
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "status":  "success",
        "message": "Login successful.",
        "user":    {"username": user["username"], "email": user["email"]},
    }


# ════════════════════════════════════════════════════════════════════
# PASSWORD RESET
# ════════════════════════════════════════════════════════════════════
@app.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.strip().lower()

    if not db.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email is not registered.")

    otp_code = generate_otp_code()
    saved    = db.create_otp_record(
        email, "reset", otp_code, expiry_minutes=EMAIL_OTP_EXPIRY_MINUTES
    )
    if not saved:
        raise HTTPException(status_code=500, detail="Unable to create OTP record.")

    try:
        await dispatch_otp_email(email, otp_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "message": "OTP sent to your email."}


@app.post("/verify-reset-otp")
async def verify_reset_otp(payload: VerifyResetOtpRequest):
    email = payload.email.strip().lower()
    otp   = payload.otp.strip()

    _, error = db.validate_otp(email, otp, "reset", max_attempts=MAX_OTP_ATTEMPTS)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {"status": "success", "message": "OTP verified. You may now reset your password."}


@app.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    email            = payload.email.strip().lower()
    otp              = payload.otp.strip()
    new_password     = payload.new_password
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


# ════════════════════════════════════════════════════════════════════
# PREDICT IMAGE
# ════════════════════════════════════════════════════════════════════
@app.post("/predict-image")
async def predict_image(
    file: UploadFile = File(...),
    user_email: Optional[str] = Form(None),
):
    """
    Accepts an image upload, checks for duplicates, runs ViT inference,
    stores result + Base64 image in MongoDB, and returns the prediction.

    Response fields:
        prediction      : "Real" or "Fake"
        confidence      : confidence in the predicted label (formatted %)
        confidence_score: same as float [0, 1]
        prob_fake       : raw fakeness probability [0, 1] — stable metric
        inference_ms    : model inference time in milliseconds
        duplicate       : true if this image was already analyzed
    """

    # ── 1. Model availability ────────────────────────────────────
    if not detector.is_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Model is unavailable. "
                "Train the model and place best_model.pth in models/, then restart."
            ),
        )

    # ── 2. MIME type check ───────────────────────────────────────
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    # ── 3. Read bytes ────────────────────────────────────────────
    raw_bytes = await file.read()

    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 8MB.",
        )

    # ── 4. Duplicate detection (atomic with upsert) ──────────────
    image_hash = hashlib.sha256(raw_bytes).hexdigest()
    
    # ── 5. Decode image ──────────────────────────────────────────
    try:
        np_arr    = np.frombuffer(raw_bytes, np.uint8)
        image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image_bgr is None:
            raise ValueError("Could not decode image data. File may be corrupt.")

        h, w = image_bgr.shape[:2]
        if h < MIN_IMAGE_DIMENSION or w < MIN_IMAGE_DIMENSION:
            raise ValueError(
                f"Image too small ({w}x{h}px). "
                f"Minimum is {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}px."
            )

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    # ── 6. Inference ─────────────────────────────────────────────
    try:
        result = detector.predict_image(image_rgb)
    except ValueError as e:
        # Preprocessing error — bad input
        raise HTTPException(status_code=400, detail=f"Image preprocessing failed: {e}")
    except RuntimeError as e:
        # Model error
        logger.error(f"Inference RuntimeError: {e}")
        raise HTTPException(status_code=500, detail="Inference failed. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected inference error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during inference.")

    # result is a dict: {label, prob_fake, confidence, inference_ms}
    label        = result["label"]           # "Real" or "Fake"
    prob_fake    = result["prob_fake"]       # always fakeness score [0, 1]
    confidence   = result["confidence"]      # confidence in predicted label [0, 1]
    inference_ms = result["inference_ms"]

    logger.info(
        f"Inference | file={file.filename} | label={label} | "
        f"prob_fake={prob_fake:.4f} | confidence={confidence:.4f} | "
        f"{inference_ms}ms"
    )

    # ── 7. Store result (atomic upsert) ──────────────────────────
    # Use upsert for atomic deduplication — prevents race conditions
    image_base64 = base64.b64encode(raw_bytes).decode("utf-8")

    saved_doc, is_duplicate = db.upsert_prediction(
        file_name=file.filename,
        file_type="image",
        mime_type=file.content_type,
        prediction=label,
        confidence_score=prob_fake,     # canonical: always prob_fake
        image_base64=image_base64,
        image_hash=image_hash,
        user_email=user_email,
    )

    # If this was a duplicate, return stored result instead of fresh inference
    if is_duplicate and saved_doc:
        stored_prob_fake = saved_doc["confidence_score"]
        stored_label     = saved_doc["prediction"]
        stored_confidence = (
            stored_prob_fake if stored_label == "Fake" else 1.0 - stored_prob_fake
        )
        logger.info(f"Returning stored result for duplicate image")
        return {
            "status":           "success",
            "prediction":       stored_label,
            "confidence":       f"{stored_confidence * 100:.2f}%",
            "confidence_score": round(stored_confidence, 4),
            "prob_fake":        round(stored_prob_fake, 4),
            "inference_ms":     0,
            "duplicate":        True,
            "message":          "This image was already analyzed. Showing previous result.",
        }

    # ── 8. Response ──────────────────────────────────────────────
    return {
        "status":           "success",
        "prediction":       label,
        "confidence":       f"{confidence * 100:.2f}%",
        "confidence_score": round(confidence, 4),
        "prob_fake":        round(prob_fake, 4),
        "inference_ms":     inference_ms,
        "duplicate":        False,
    }


# ════════════════════════════════════════════════════════════════════
# HISTORY
# ════════════════════════════════════════════════════════════════════
@app.get("/history")
async def get_history(limit: int = 50, email: Optional[str] = None):
    """
    Returns prediction history.
    Requires email param to scope results to a user.
    Without email, returns global history (admin use only).
    """
    try:
        history = db.get_history(limit, email, include_images=True)
        mapped_history = []
        for item in history:
            stored_prob_fake = item.get("confidence_score", 0.0)
            stored_label = item.get("prediction", "Unknown")
            stored_confidence = (
                stored_prob_fake if stored_label == "Fake" else 1.0 - stored_prob_fake
            )
            mapped_item = dict(item)
            mapped_item["confidence_score"] = round(stored_confidence, 4)
            mapped_item["prob_fake"] = round(stored_prob_fake, 4)
            mapped_item["confidence"] = f"{stored_confidence * 100:.2f}%"
            mapped_history.append(mapped_item)
        return {"status": "success", "data": mapped_history}
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history.")


# ════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn

    host   = os.getenv("API_HOST",   "0.0.0.0")
    port   = int(os.getenv("API_PORT", 8000))
    reload = os.getenv("API_RELOAD", "True").lower() == "true"

    uvicorn.run("app:app", host=host, port=port, reload=reload)