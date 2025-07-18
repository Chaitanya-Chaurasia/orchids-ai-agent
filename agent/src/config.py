import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

PROJECT_PATH = "../"
SRC_PATH = os.path.join(PROJECT_PATH, "src")
QDRANT_PATH = os.path.join(PROJECT_PATH, "orchid_db")

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}"
EMBEDDING_MODEL = 'models/text-embedding-004'