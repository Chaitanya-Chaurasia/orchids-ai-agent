import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

_config_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_config_dir))

SRC_PATH = os.path.join(PROJECT_ROOT, "src")
QDRANT_PATH = os.path.join(PROJECT_ROOT, "orchid_db")

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}"
EMBEDDING_MODEL = 'models/text-embedding-004'

