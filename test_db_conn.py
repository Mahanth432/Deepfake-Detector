import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv('.env')

def test_db():
    uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    db_name = os.getenv('MONGO_DB_NAME', 'deepfake_detection')

    print(f"Testing connection to {uri}...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        print("Successfully connected to MongoDB server.")
        
        db = client[db_name]
        print(f"Database '{db_name}' accessed.")
        
        client.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if test_db():
        sys.exit(0)
    else:
        sys.exit(1)
