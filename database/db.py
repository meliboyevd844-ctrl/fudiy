import aiosqlite
import secrets
import logging
from config import (
    DB_PATH,
    DEFAULT_SHOP_LAT,
    DEFAULT_SHOP_LON,
    DEFAULT_SHOP_RADIUS_METERS,
    DEFAULT_WORK_START_TIME,
    DEFAULT_WORK_END_TIME,
    DEFAULT_LATE_GRACE_MINUTES,
    ADMIN_PASSWORD,
    ADMIN_ID,
)

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize the SQLite database with required tables, concurrency pragmas, and default settings."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=30000;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA cache_size=-64000;") # 64MB cache
        
        # Settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        
        # Employees table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                full_name TEXT NOT NULL,
                username TEXT,
                phone TEXT,
                login TEXT UNIQUE,
                password TEXT,
                is_approved INTEGER DEFAULT 0,
                is_logged_in INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Attendance table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                arrival_time TEXT,
                departure_time TEXT,
                arrival_lat REAL,
                arrival_lon REAL,
                arrival_distance_m REAL,
                departure_lat REAL,
                departure_lon REAL,
                departure_distance_m REAL,
                selfie_file TEXT,
                status TEXT DEFAULT 'keldi',
                total_work_minutes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(employee_id, date),
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );
        """)
        
        # Safely ensure selfie_file column exists for existing tables
        try:
            await db.execute("ALTER TABLE attendance ADD COLUMN selfie_file TEXT;")
        except Exception:
            pass
        
        # Absence Reasons table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS absence_reasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                reason_text TEXT NOT NULL,
                is_reviewed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );
        """)

        # Admin sessions / authorized IDs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                telegram_id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Performance Indexes for High Traffic Concurrency
        await db.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_attendance_emp_date ON attendance(employee_id, date);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_employees_tg_id ON employees(telegram_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_employees_login ON employees(login);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_absence_emp_date ON absence_reasons(employee_id, date);")
        
        # Seed default settings if not exists
        default_qr_token = "SHOP_QR_" + secrets.token_hex(6).upper()
        defaults = [
            ("shop_lat", str(DEFAULT_SHOP_LAT)),
            ("shop_lon", str(DEFAULT_SHOP_LON)),
            ("shop_radius_m", str(DEFAULT_SHOP_RADIUS_METERS)),
            ("shop_qr_token", default_qr_token),
            ("work_start_time", DEFAULT_WORK_START_TIME),
            ("work_end_time", DEFAULT_WORK_END_TIME),
            ("late_grace_minutes", str(DEFAULT_LATE_GRACE_MINUTES)),
            ("admin_login", "admin"),
            ("admin_password", "adminzohid"),
        ]
        if ADMIN_ID:
            defaults.append(("admin_chat_id", str(ADMIN_ID)))
            
        for key, val in defaults:
            await db.execute("""
                INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?);
            """, (key, val))
            
        if ADMIN_ID:
            await db.execute("""
                INSERT OR IGNORE INTO admin_users (telegram_id, is_active) VALUES (?, 1);
            """, (ADMIN_ID,))
            
        await db.commit()
        logger.info("Database initialized successfully at %s", DB_PATH)
