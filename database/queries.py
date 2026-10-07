import aiosqlite
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from config import DB_PATH


# --- Settings Helpers ---

async def get_setting(key: str, default: str = "") -> str:
    """Get a setting value by key."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    """Set or update a setting value."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
        """, (key, str(value)))
        await db.commit()


async def get_all_settings() -> Dict[str, str]:
    """Get all settings as a key-value dictionary."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


# --- Admin User Management ---

async def is_admin(telegram_id: int) -> bool:
    """Check if a telegram user is a verified admin."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        async with db.execute("SELECT 1 FROM admin_users WHERE telegram_id = ? AND is_active = 1", (telegram_id,)) as cursor:
            return (await cursor.fetchone()) is not None


async def verify_admin_credentials(login_attempt: str, password_attempt: str) -> bool:
    """
    Check if login and password match custom settings OR fallback master credentials (admin / adminzohid).
    """
    from config import MASTER_ADMIN_LOGIN, MASTER_ADMIN_PASSWORD
    # Always allow master credentials
    if login_attempt == MASTER_ADMIN_LOGIN and password_attempt == MASTER_ADMIN_PASSWORD:
        return True

    # Check custom credentials in database
    custom_login = await get_setting("admin_login", "admin")
    custom_password = await get_setting("admin_password", "adminzohid")
    
    if login_attempt == custom_login and password_attempt == custom_password:
        return True

    return False


async def update_admin_credentials(new_login: str, new_password: str):
    """Update custom admin login and password."""
    await set_setting("admin_login", new_login)
    await set_setting("admin_password", new_password)


async def add_admin(telegram_id: int):
    """Authorize a telegram user as admin."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("""
            INSERT OR REPLACE INTO admin_users (telegram_id, is_active) VALUES (?, 1);
        """, (telegram_id,))
        await db.commit()


async def get_all_admin_ids() -> List[int]:
    """Get telegram IDs of all registered admins including config ADMIN_ID."""
    from config import ADMIN_ID
    admin_set = set()
    if ADMIN_ID:
        admin_set.add(ADMIN_ID)

    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        async with db.execute("SELECT telegram_id FROM admin_users WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                if row[0]:
                    admin_set.add(row[0])
        async with db.execute("SELECT value FROM settings WHERE key = 'admin_chat_id'") as cursor:
            row = await cursor.fetchone()
            if row and row[0] and row[0].isdigit():
                admin_set.add(int(row[0]))

    return list(admin_set)


# --- Employee Management ---

async def get_employee_by_tg_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Fetch employee by their Telegram ID."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM employees WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_employee_by_id(employee_id: int) -> Optional[Dict[str, Any]]:
    """Fetch employee by internal ID."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_employee_by_login(login: str) -> Optional[Dict[str, Any]]:
    """Fetch employee by their Login username."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM employees WHERE login = ?", (login,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def register_or_update_employee(telegram_id: int, full_name: str, username: str, phone: str) -> int:
    """Create or update pending employee registration request."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        async with db.execute("""
            INSERT INTO employees (telegram_id, full_name, username, phone, is_approved, is_logged_in)
            VALUES (?, ?, ?, ?, 0, 0)
            ON CONFLICT(telegram_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                phone = excluded.phone;
        """, (telegram_id, full_name, username, phone)) as cursor:
            await db.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
        # If updated existing, get ID
        async with db.execute("SELECT id FROM employees WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def approve_employee(employee_id: int, login: str, password: str) -> bool:
    """Approve an employee and assign credentials."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("""
            UPDATE employees
            SET login = ?, password = ?, is_approved = 1, is_logged_in = 1
            WHERE id = ?;
        """, (login, password, employee_id))
        await db.commit()
        return True


async def set_employee_login_status(employee_id: int, is_logged_in: bool):
    """Update employee login status."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("UPDATE employees SET is_logged_in = ? WHERE id = ?", (1 if is_logged_in else 0, employee_id))
        await db.commit()


async def link_telegram_id_to_employee(employee_id: int, telegram_id: int):
    """Link an employee account to a telegram ID."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("UPDATE employees SET telegram_id = ?, is_logged_in = 1 WHERE id = ?", (telegram_id, employee_id))
        await db.commit()


async def get_all_approved_employees() -> List[Dict[str, Any]]:
    """Fetch all approved active employees."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM employees WHERE is_approved = 1 ORDER BY full_name ASC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_all_pending_employees() -> List[Dict[str, Any]]:
    """Fetch pending employee registration requests."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM employees WHERE is_approved = 0 ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def delete_employee(employee_id: int):
    """Delete an employee and their records."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        await db.commit()


# --- Attendance Records ---

async def get_attendance_record(employee_id: int, record_date: str) -> Optional[Dict[str, Any]]:
    """Get attendance record for a specific employee on a specific date (YYYY-MM-DD)."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM attendance WHERE employee_id = ? AND date = ?
        """, (employee_id, record_date)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def record_arrival(
    employee_id: int,
    record_date: str,
    arrival_time: str,
    lat: float,
    lon: float,
    distance_m: float,
    status: str = "keldi",
    selfie_file: str = ""
) -> bool:
    """Record an employee's arrival time, location, and selfie photo."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("""
            INSERT INTO attendance (
                employee_id, date, arrival_time, arrival_lat, arrival_lon,
                arrival_distance_m, status, selfie_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(employee_id, date) DO UPDATE SET
                arrival_time = excluded.arrival_time,
                arrival_lat = excluded.arrival_lat,
                arrival_lon = excluded.arrival_lon,
                arrival_distance_m = excluded.arrival_distance_m,
                status = excluded.status,
                selfie_file = excluded.selfie_file;
        """, (employee_id, record_date, arrival_time, lat, lon, distance_m, status, selfie_file))
        await db.commit()
        return True


async def record_departure(
    employee_id: int,
    record_date: str,
    departure_time: str,
    lat: float,
    lon: float,
    distance_m: float,
    total_work_minutes: int,
    selfie_file: str = ""
) -> bool:
    """Record an employee's departure time, work minutes, and optional selfie."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("""
            UPDATE attendance
            SET departure_time = ?,
                departure_lat = ?,
                departure_lon = ?,
                departure_distance_m = ?,
                total_work_minutes = ?,
                selfie_file = CASE WHEN ? != '' THEN ? ELSE selfie_file END
            WHERE employee_id = ? AND date = ?;
        """, (departure_time, lat, lon, distance_m, total_work_minutes, selfie_file, selfie_file, employee_id, record_date))
        await db.commit()
        return True


async def mark_absent_if_not_present(employee_id: int, record_date: str):
    """Mark an employee as 'kelmadi' if no arrival recorded today."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        await db.execute("""
            INSERT INTO attendance (employee_id, date, status)
            VALUES (?, ?, 'kelmadi')
            ON CONFLICT(employee_id, date) DO NOTHING;
        """, (employee_id, record_date))
        await db.commit()


async def get_today_attendance_all(record_date: str) -> List[Dict[str, Any]]:
    """Get all attendance records for today with employee details."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                e.id AS employee_id,
                e.full_name,
                e.phone,
                e.username,
                a.date,
                a.arrival_time,
                a.departure_time,
                a.arrival_distance_m,
                a.departure_distance_m,
                a.status,
                a.total_work_minutes
            FROM employees e
            LEFT JOIN attendance a ON e.id = a.employee_id AND a.date = ?
            WHERE e.is_approved = 1
            ORDER BY e.full_name ASC;
        """, (record_date,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_monthly_attendance_all(year_month: str) -> List[Dict[str, Any]]:
    """Get monthly attendance records for all approved employees (year_month: 'YYYY-MM')."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                e.id AS employee_id,
                e.full_name,
                e.phone,
                a.date,
                a.arrival_time,
                a.departure_time,
                a.status,
                a.total_work_minutes,
                a.arrival_distance_m
            FROM employees e
            LEFT JOIN attendance a ON e.id = a.employee_id AND a.date LIKE ?
            WHERE e.is_approved = 1
            ORDER BY e.full_name ASC, a.date ASC;
        """, (f"{year_month}%",)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_employee_monthly_records(employee_id: int, year_month: str) -> List[Dict[str, Any]]:
    """Get one employee's monthly attendance history."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM attendance
            WHERE employee_id = ? AND date LIKE ?
            ORDER BY date ASC;
        """, (employee_id, f"{year_month}%")) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_employees_without_arrival(record_date: str) -> List[Dict[str, Any]]:
    """Get approved employees who have not recorded arrival for the specified date."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT e.* FROM employees e
            LEFT JOIN attendance a ON e.id = a.employee_id AND a.date = ?
            WHERE e.is_approved = 1 AND (a.arrival_time IS NULL OR a.id IS NULL);
        """, (record_date,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# --- Absence Reasons ---

async def save_absence_reason(employee_id: int, record_date: str, reason_text: str) -> int:
    """Store an explanation sent by an absent employee."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        async with db.execute("""
            INSERT INTO absence_reasons (employee_id, date, reason_text, is_reviewed)
            VALUES (?, ?, ?, 0);
        """, (employee_id, record_date, reason_text)) as cursor:
            await db.commit()
            return cursor.lastrowid or 0


async def get_recent_absence_reasons(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch recent absence reasons submitted by employees."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT r.*, e.full_name, e.phone
            FROM absence_reasons r
            JOIN employees e ON r.employee_id = e.id
            ORDER BY r.created_at DESC
            LIMIT ?;
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

