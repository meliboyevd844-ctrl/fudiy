from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from config import WEBAPP_BASE_URL

# Main Welcome Keyboard
def get_main_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨‍💼 Men xodimman"), KeyboardButton(text="👑 Admin")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# Employee Registration / Login Request Keyboard
def get_employee_auth_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Ro'yxatdan o'tish so'rovi"), KeyboardButton(text="🔑 Login orqali kirish")],
            [KeyboardButton(text="⬅️ Bosh menyu")],
        ],
        resize_keyboard=True,
    )

# Employee Request Credentials Button (After filling Name and Phone)
def get_employee_request_creds_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔑 Menga login va parol berilsin")],
            [KeyboardButton(text="⬅️ Bosh menyu")],
        ],
        resize_keyboard=True,
    )

# Contact Sharing Button
def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)],
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
    )

# Employee Dashboard Keyboard (Standard Reply Buttons - 100% reliable on all devices)
def get_employee_dashboard_keyboard(user_id: int = 0) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🟢 KELDIM"),
                KeyboardButton(text="🔴 KETDIM"),
            ],
            [
                KeyboardButton(text="📊 Oylik hisobotim"),
                KeyboardButton(text="ℹ️ Mening profilim"),
            ],
            [
                KeyboardButton(text="🚪 Tizimdan chiqish"),
                KeyboardButton(text="⬅️ Bosh menyu"),
            ]
        ],
        resize_keyboard=True,
    )

# 1-Tap Geolocation Sending Button for Employees
def get_send_location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiyamni yuborish", request_location=True)],
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
    )

# 1-Tap Geolocation Sending Button for Admin (Store Location)
def get_admin_location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Hozirgi joylashuvimni (Do'kon lokatsiyasini) yuborish", request_location=True)],
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
    )

# Admin Dashboard Keyboard
def get_admin_dashboard_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Xodim qo'shish (So'rovlar)"), KeyboardButton(text="👥 Xodimlar ro'yxati")],
            [KeyboardButton(text="📊 Bugungi hisobot"), KeyboardButton(text="📅 1 oylik hisobot (Excel)")],
            [KeyboardButton(text="📍 Do'kon lokatsiyasini sozlash (GPS)"), KeyboardButton(text="⏰ Ish vaqti (Kelish/Ketish)")],
            [KeyboardButton(text="🖨️ Do'kon QR Kodini olish"), KeyboardButton(text="🔑 Admin Login/Parol o'zgartirish")],
            [KeyboardButton(text="📨 Kelmaganlar sabablari"), KeyboardButton(text="🔔 Kelmaganlarni tekshirish")],
            [KeyboardButton(text="🚪 Admin paneldan chiqish")],
        ],
        resize_keyboard=True,
    )

# Admin Employee Action Inline Keyboard
def get_pending_employee_inline(emp_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔑 Tanlash: Login va Parol berish", callback_data=f"approve_emp:{emp_id}"),
            ],
            [
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_emp:{emp_id}"),
            ]
        ]
    )

# Cancel Keyboard
def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Bekor qilish")]],
        resize_keyboard=True,
    )
