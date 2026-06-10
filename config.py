from dotenv import load_dotenv
import os

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials/google_service_account.json")
UAZAPI_BASE_URL = os.getenv("UAZAPI_BASE_URL", "")
UAZAPI_TOKEN = os.getenv("UAZAPI_TOKEN", "")
UAZAPI_INSTANCE = os.getenv("UAZAPI_INSTANCE", "")
PORT = int(os.getenv("PORT", 8000))
