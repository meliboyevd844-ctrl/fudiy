import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
QR_DIR = DATA_DIR / "qrcodes"
SELFIES_DIR = DATA_DIR / "selfies"

# Ensure runtime directories exist
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
QR_DIR.mkdir(exist_ok=True)
SELFIES_DIR.mkdir(exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin Settings & Master Fallback Credentials
MASTER_ADMIN_LOGIN = "admin"
MASTER_ADMIN_PASSWORD = "adminzohid"
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID", "").strip().isdigit() else None
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "adminzohid").strip()
ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "admin").strip()

# Database
DB_PATH = DATA_DIR / "bot_database.db"

# Store Settings (defaults)
DEFAULT_SHOP_LAT = float(os.getenv("SHOP_LATITUDE", "41.311081"))
DEFAULT_SHOP_LON = float(os.getenv("SHOP_LONGITUDE", "69.240562"))
DEFAULT_SHOP_RADIUS_METERS = float(os.getenv("SHOP_RADIUS_METERS", "50.0"))

# Shift Times
DEFAULT_WORK_START_TIME = os.getenv("WORK_START_TIME", "09:00")
DEFAULT_WORK_END_TIME = os.getenv("WORK_END_TIME", "18:00")
DEFAULT_LATE_GRACE_MINUTES = int(os.getenv("LATE_GRACE_MINUTES", "15"))

# WebApp Settings
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", f"http://localhost:{WEBAPP_PORT}").rstrip("/")
