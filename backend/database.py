import secrets
import logging
import os
import time
from datetime import datetime, timezone, timedelta

import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    MongoDB manager for the Deepfake Detection API.

    Collections:
        predictions  — inference results + base64 images
        users        — registered accounts
        otps         — one-time passwords for registration and reset
    """

    def __init__(self):
        self.uri     = os.getenv("MONGO_URI",     "mongodb://localhost:27017/")
        self.db_name = os.getenv("MONGO_DB_NAME", "deepfake_detection")
        self.client  = None
        self.db      = None

    # ════════════════════════════════════════════════════════════
    # CONNECTION
    # ════════════════════════════════════════════════════════════

    def connect(self, retries: int = 3, delay: float = 2.0) -> bool:
        """
        Connect to MongoDB with retry logic.
        Retries `retries` times with `delay` seconds between attempts.
        """
        for attempt in range(1, retries + 1):
            try:
                self.client = MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=5000,
                )
                self.client.server_info()   # force connection check
                self.db = self.client[self.db_name]
                self._create_indexes()
                logger.info(
                    f"Connected to MongoDB | uri='{self.uri}' | db='{self.db_name}'"
                )
                return True

            except Exception as e:
                logger.warning(
                    f"MongoDB connection attempt {attempt}/{retries} failed: {e}"
                )
                if attempt < retries:
                    time.sleep(delay)

        logger.error("All MongoDB connection attempts failed.")
        return False

    def _create_indexes(self):
        """Create indexes in background — non-blocking on large collections."""
        try:
            # predictions: fast hash lookup + per-user dedup
            self.db.predictions.create_index(
                "image_hash", sparse=True, background=True
            )
            # Unique index on (user_email, image_hash) prevents duplicates atomically
            # This ensures only ONE record per image per user
            self.db.predictions.create_index(
                [
                    ("user_email",  pymongo.ASCENDING),
                    ("image_hash",  pymongo.ASCENDING),
                ],
                sparse=True,
                unique=True,
                background=True,
            )

            # users: unique email
            self.db.users.create_index(
                "email", unique=True, background=True
            )

            # otps: TTL auto-expiry + lookup
            self.db.otps.create_index(
                "expires_at",
                expireAfterSeconds=0,
                background=True,
            )
            self.db.otps.create_index(
                [
                    ("email",    pymongo.ASCENDING),
                    ("otp_type", pymongo.ASCENDING),
                ],
                sparse=True,
                background=True,
            )
            logger.info("MongoDB indexes verified.")

        except Exception as e:
            logger.warning(f"Index creation warning (non-fatal): {e}")

    def get_db(self):
        """Return db handle, reconnecting once if disconnected."""
        if self.db is None:
            logger.warning("Database not connected — attempting reconnect...")
            self.connect()
        return self.db

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    def __repr__(self) -> str:
        return (
            f"DatabaseManager("
            f"db='{self.db_name}', "
            f"connected={self.db is not None})"
        )

    # ════════════════════════════════════════════════════════════
    # PREDICTIONS
    # ════════════════════════════════════════════════════════════

    def log_prediction(
        self,
        file_name:        str,
        file_type:        str,
        mime_type:        str,
        prediction:       str,
        confidence_score: float,
        image_base64:     str,
        image_hash:       str,
        user_email:       str = None,
    ) -> bool:
        """
        Store a prediction result.

        confidence_score should always be prob_fake (canonical fakeness
        probability in [0,1]) — set by app.py before calling this.
        """
        db = self.get_db()
        if db is None:
            logger.warning("DB unavailable — prediction not logged.")
            return False

        try:
            doc = {
                # Always store UTC — consistent across timezones
                "timestamp":        datetime.now(timezone.utc),
                "file_name":        file_name,
                "file_type":        file_type,
                "mime_type":        mime_type,
                "prediction":       prediction,
                "confidence_score": float(confidence_score),
                "image_base64":     image_base64,
                "image_hash":       image_hash,
                "user_email":       user_email,
            }
            db.predictions.insert_one(doc)
            return True

        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")
            return False

    def find_by_hash(self, image_hash: str, user_email: str = None):
        """
        Find an existing prediction by image hash.
        Scoped to user_email when provided.
        Returns document dict or None.
        """
        db = self.get_db()
        if db is None:
            return None

        query = {"image_hash": image_hash}
        if user_email:
            query["user_email"] = user_email

        try:
            doc = db.predictions.find_one(query)
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc

        except Exception as e:
            logger.error(f"Error in find_by_hash: {e}")
            return None

    def upsert_prediction(
        self,
        file_name:        str,
        file_type:        str,
        mime_type:        str,
        prediction:       str,
        confidence_score: float,
        image_base64:     str,
        image_hash:       str,
        user_email:       str = None,
    ) -> tuple:
        """
        Atomically insert or update a prediction using upsert.
        Prevents race conditions by using MongoDB's atomic upsert.
        
        Returns:
            (document_dict, is_duplicate)
            - document_dict: the inserted/updated record (with _id as string)
            - is_duplicate: True if record already existed, False if new insert
        """
        db = self.get_db()
        if db is None:
            logger.warning("DB unavailable — prediction not logged.")
            return None, None

        try:
            doc = {
                # Always store UTC — consistent across timezones
                "timestamp":        datetime.now(timezone.utc),
                "file_name":        file_name,
                "file_type":        file_type,
                "mime_type":        mime_type,
                "prediction":       prediction,
                "confidence_score": float(confidence_score),
                "image_base64":     image_base64,
                "image_hash":       image_hash,
                "user_email":       user_email,
            }

            # Upsert query uses the unique index (user_email, image_hash)
            query = {
                "user_email": user_email,
                "image_hash": image_hash,
            }

            result = db.predictions.replace_one(
                query,
                doc,
                upsert=True  # Atomic: insert if not exists, update if exists
            )

            # Check if this was an update (matched existing) or insert (new)
            is_duplicate = result.matched_count > 0
            
            if is_duplicate:
                logger.info(
                    f"Duplicate prediction detected → "
                    f"user={user_email} | hash={image_hash[:16]}... | "
                    f"SKIPPED (existing record kept)"
                )
            else:
                logger.info(
                    f"New prediction saved → "
                    f"user={user_email} | hash={image_hash[:16]}... | "
                    f"label={prediction}"
                )

            # Retrieve the document to return
            saved_doc = db.predictions.find_one(query)
            if saved_doc:
                saved_doc["_id"] = str(saved_doc["_id"])
                return saved_doc, is_duplicate
            
            return None, is_duplicate

        except pymongo.errors.DuplicateKeyError as e:
            # Shouldn't happen with upsert, but handle just in case
            logger.warning(f"Duplicate key error (shouldn't happen with upsert): {e}")
            existing = db.predictions.find_one(query)
            if existing:
                existing["_id"] = str(existing["_id"])
                return existing, True
            return None, None

        except Exception as e:
            logger.error(f"Failed to upsert prediction: {e}")
            return None, None

    def get_history(self, limit: int = 50, email: str = None, include_images: bool = False):
        """
        Return recent predictions, newest first.

        Args:
            limit          : max records to return
            email          : filter by user (None = all records)
            include_images : if False (default), strips image_base64
                             to keep response size small for list views.
                             Pass True only when fetching a single record
                             for detail view.
        """
        db = self.get_db()
        if db is None:
            return []

        try:
            query = {"user_email": email} if email else {}

            # Exclude large base64 field unless explicitly requested
            projection = None if include_images else {"image_base64": 0}

            cursor = (
                db.predictions
                .find(query, projection)
                .sort("timestamp", pymongo.DESCENDING)
                .limit(limit)
            )

            history = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])

                # Safe defaults for legacy records
                doc.setdefault("file_type",    "image")
                doc.setdefault("mime_type",    "image/jpeg")
                doc.setdefault("image_base64", None)
                doc.setdefault("image_hash",   None)
                doc.setdefault("user_email",   None)

                history.append(doc)

            return history

        except Exception as e:
            logger.error(f"Error retrieving history: {e}")
            return []

    # ════════════════════════════════════════════════════════════
    # OTP
    # ════════════════════════════════════════════════════════════

    def create_otp_record(
        self,
        email:           str,
        otp_type:        str,
        otp:             str,
        payload:         dict = None,
        expiry_minutes:  int  = 5,
    ) -> bool:
        """
        Create a new OTP record, replacing any existing unverified one.
        TTL index handles cleanup automatically.
        """
        db = self.get_db()
        if db is None:
            return False

        try:
            # Remove any previous unused OTP for this email+type
            db.otps.delete_many({"email": email, "otp_type": otp_type})

            record = {
                "email":      email,
                "otp_type":   otp_type,
                "otp":        str(otp).zfill(6),
                "payload":    payload or {},
                # Use UTC consistently
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
                "used":       False,
                "attempts":   0,
            }
            db.otps.insert_one(record)
            return True

        except Exception as e:
            logger.error(f"Error creating OTP record: {e}")
            return False

    def validate_otp(self, email: str, otp: str, otp_type: str, max_attempts: int = 5):
        """
        Validate an OTP submission.

        Returns:
            (record, None)       on success
            (None,  error_msg)   on failure
        """
        db = self.get_db()
        if db is None:
            return None, "Database unavailable."

        try:
            record = db.otps.find_one(
                {"email": email, "otp_type": otp_type, "used": False}
            )

            if not record:
                return None, "OTP not found or already used."

            # Expiry check — compare UTC to UTC
            expires_at = record.get("expires_at")
            if expires_at:
                # Handle both aware and naive datetimes in existing records
                now_utc = datetime.now(timezone.utc)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < now_utc:
                    db.otps.update_one(
                        {"_id": record["_id"]},
                        {"$set": {"used": True}}
                    )
                    return None, "OTP has expired. Please request a new code."

            if record.get("attempts", 0) >= max_attempts:
                return None, "Too many invalid attempts. Please request a new code."

            # Constant-time comparison — prevents timing attacks
            submitted = str(otp).zfill(6)
            stored    = str(record.get("otp", "")).zfill(6)

            if not secrets.compare_digest(stored, submitted):
                db.otps.update_one(
                    {"_id": record["_id"]},
                    {"$inc": {"attempts": 1}}
                )
                remaining = max_attempts - record.get("attempts", 0) - 1
                return None, f"Invalid OTP. {remaining} attempt(s) remaining."

            return record, None

        except Exception as e:
            logger.error(f"Error validating OTP: {e}")
            return None, "OTP validation failed."

    def mark_otp_used(self, otp_id) -> bool:
        db = self.get_db()
        if db is None:
            return False

        try:
            db.otps.update_one(
                {"_id": otp_id},
                {"$set": {"used": True}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking OTP used: {e}")
            return False

    # ════════════════════════════════════════════════════════════
    # USERS
    # ════════════════════════════════════════════════════════════

    def create_user(self, username: str, email: str, password_hash: str):
        """
        Create a new user.
        Returns (True, success_msg) or (False, error_msg).
        """
        db = self.get_db()
        if db is None:
            return False, "Database connection failed."

        try:
            if db.users.find_one({"email": email}):
                return False, "Email already registered."

            db.users.insert_one({
                "username":      username,
                "email":         email,
                "password_hash": password_hash,
                "created_at":    datetime.now(timezone.utc),
            })
            return True, "Registration successful."

        except pymongo.errors.DuplicateKeyError:
            # Unique index race condition safeguard
            return False, "Email already registered."
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            return False, "Failed to register user."

    def get_user_by_email(self, email: str):
        db = self.get_db()
        if db is None:
            return None

        try:
            user = db.users.find_one({"email": email})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            logger.error(f"Error fetching user {email}: {e}")
            return None

    def update_user_password(self, email: str, password_hash: str) -> bool:
        db = self.get_db()
        if db is None:
            return False

        try:
            result = db.users.update_one(
                {"email": email},
                {"$set": {"password_hash": password_hash}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating password for {email}: {e}")
            return False


# ── Global singleton ─────────────────────────────────────────────────
db = DatabaseManager()