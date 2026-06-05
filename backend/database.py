import pymongo
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class DatabaseManager:
    def __init__(self):
        self.uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        self.db_name = os.getenv('MONGO_DB_NAME', 'deepfake_detection')
        self.client = None
        self.db = None

    def connect(self):
        """ Initializes a MongoDB connection and verifies connectivity. """
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Force a call to check connectivity
            self.client.server_info()
            self.db = self.client[self.db_name]

            # Create index on image_hash for fast duplicate lookups
            self.db.predictions.create_index("image_hash", sparse=True)
            # Compound index for per-user duplicate detection
            self.db.predictions.create_index(
                [("image_hash", pymongo.ASCENDING), ("user_email", pymongo.ASCENDING)],
                sparse=True,
            )
            # Unique user email index for auth
            self.db.users.create_index("email", unique=True)
            # OTP record cleanup and lookup indexes
            self.db.otps.create_index("expires_at", expireAfterSeconds=0)
            self.db.otps.create_index(
                [("email", pymongo.ASCENDING), ("otp_type", pymongo.ASCENDING)],
                sparse=True,
            )

            print(f"Connected to MongoDB at '{self.uri}' and database '{self.db_name}'.")
            return True
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            return False

    def get_db(self):
        if self.db is None:
            if not self.connect():
                return None
        return self.db

    # ── Duplicate detection ──────────────────────────────────────
    def find_by_hash(self, image_hash, user_email=None):
        """
        Look up a prediction document by image_hash and user_email when provided.
        Returns the document dict if found, else None.
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
            print(f"Error querying by image_hash and user_email: {e}")
            return None

    # ── Store prediction with Base64 image ───────────────────────
    def log_prediction(self, file_name, file_type, mime_type,
                       prediction, confidence_score,
                       image_base64, image_hash, user_email=None):
        """
        Inserts a new prediction document into the `predictions` collection.
        The uploaded image is stored as a Base64-encoded string.
        """
        db = self.get_db()
        if db is None:
            print("Warning: Database not connected. Prediction not logged.")
            return False

        try:
            log_entry = {
                "timestamp": datetime.now(),
                "file_name": file_name,
                "file_type": file_type,
                "mime_type": mime_type,
                "prediction": prediction,
                "confidence_score": float(confidence_score),
                "image_base64": image_base64,
                "image_hash": image_hash,
                "user_email": user_email,
            }
            db.predictions.insert_one(log_entry)
            return True
        except Exception as e:
            print(f"Error inserting into MongoDB: {e}")
            return False

    # ── History retrieval ────────────────────────────────────────
    def get_history(self, limit=50, email=None):
        """
        Returns the most recent prediction documents, newest first.
        Safely handles legacy records that may lack image_base64 or
        other new fields.
        """
        db = self.get_db()
        if db is None:
            return []

        try:
            query = {"user_email": email} if email else {}
            cursor = (
                db.predictions
                .find(query)
                .sort("timestamp", pymongo.DESCENDING)
                .limit(limit)
            )

            history = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])

                # Guarantee every record has these keys (safe for old docs)
                doc.setdefault("file_type", "image")
                doc.setdefault("mime_type", "image/jpeg")
                doc.setdefault("image_base64", None)
                doc.setdefault("image_hash", None)
                doc.setdefault("user_email", None)

                history.append(doc)
            return history
        except Exception as e:
            print(f"Error retrieving history from MongoDB: {e}")
            return []

    # ── OTP support ───────────────────────────────────────────────
    def create_otp_record(self, email, otp_type, otp, payload=None, expiry_minutes=5):
        db = self.get_db()
        if db is None:
            return False

        try:
            db.otps.delete_many({"email": email, "otp_type": otp_type})
            record = {
                "email": email,
                "otp_type": otp_type,
                "otp": str(otp).zfill(6),
                "payload": payload or {},
                "expires_at": datetime.utcnow() + timedelta(minutes=expiry_minutes),
                "used": False,
                "attempts": 0,
            }
            db.otps.insert_one(record)
            return True
        except Exception as e:
            print(f"Error creating OTP record: {e}")
            return False

    def get_otp_record(self, email, otp_type):
        db = self.get_db()
        if db is None:
            return None

        try:
            return db.otps.find_one({"email": email, "otp_type": otp_type, "used": False})
        except Exception as e:
            print(f"Error fetching OTP record: {e}")
            return None

    def validate_otp(self, email, otp, otp_type, max_attempts=5):
        db = self.get_db()
        if db is None:
            return None, "Database unavailable."

        try:
            record = db.otps.find_one({"email": email, "otp_type": otp_type, "used": False})
            if not record:
                return None, "OTP not found or already used."

            if record.get("expires_at") and record["expires_at"] < datetime.utcnow():
                db.otps.update_one({"_id": record["_id"]}, {"$set": {"used": True}})
                return None, "OTP has expired. Please request a new code."

            if record.get("attempts", 0) >= max_attempts:
                return None, "Too many invalid OTP attempts. Request a new code."

            if str(record.get("otp")) != str(otp).zfill(6):
                db.otps.update_one({"_id": record["_id"]}, {"$inc": {"attempts": 1}})
                return None, "Invalid OTP code."

            return record, None
        except Exception as e:
            print(f"Error validating OTP: {e}")
            return None, "OTP validation failed."

    def mark_otp_used(self, otp_id):
        db = self.get_db()
        if db is None:
            return False

        try:
            db.otps.update_one({"_id": otp_id}, {"$set": {"used": True}})
            return True
        except Exception as e:
            print(f"Error marking OTP used: {e}")
            return False

    # ── User auth ────────────────────────────────────────────────
    def create_user(self, username, email, password_hash):
        db = self.get_db()
        if db is None:
            return False, "Database connection failed."

        try:
            existing_user = db.users.find_one({"email": email})
            if existing_user:
                return False, "Email already registered."

            user_doc = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "created_at": datetime.now(),
            }
            db.users.insert_one(user_doc)
            return True, "Registration successful."
        except Exception as e:
            print(f"Error creating user: {e}")
            return False, "Failed to register user."

    def get_user_by_email(self, email):
        db = self.get_db()
        if db is None:
            return None

        try:
            user = db.users.find_one({"email": email})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            print(f"Error fetching user by email: {e}")
            return None

    def update_user_password(self, email, password_hash):
        db = self.get_db()
        if db is None:
            return False

        try:
            result = db.users.update_one(
                {"email": email},
                {"$set": {"password_hash": password_hash}},
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating password for {email}: {e}")
            return False

    def close(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")


# A global database instance
db = DatabaseManager()
