import logging
import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database.queries import (
    get_employee_by_tg_id,
    save_absence_reason,
    get_all_admin_ids,
)

logger = logging.getLogger(__name__)
router = Router()

# List of known button texts to ignore in this catch-all text handler
IGNORED_TEXTS = {
    "👨‍💼 Men xodimman", "👑 Admin", "⬅️ Bosh menyuga qaytish", "⬅️ Bosh menyu", "⬅️ Bekor qilish",
    "📝 Ro'yxatdan o'tish so'rovi", "🔑 Login orqali kirish", "🔑 Menga login va parol berilsin",
    "🟢 KELDIM", "🔴 KETDIM", "📊 Oylik hisobotim", "ℹ️ Mening profilim", "🚪 Tizimdan chiqish",
    "➕ Xodim qo'shish (So'rovlar)", "📊 Bugungi hisobot", "📅 1 oylik hisobot (Excel)",
    "👥 Xodimlar ro'yxati", "⏳ Kutilayotgan so'rovlar", "🖨️ Do'kon QR Kodini olish",
    "📍 Do'kon lokatsiyasini sozlash", "📍 Do'kon lokatsiyasini sozlash (GPS)",
    "⏰ Ish vaqti sozlamalari", "⏰ Ish vaqti (Kelish/Ketish)", "🔑 Admin Login/Parol o'zgartirish",
    "📨 Kelmaganlar sabablari", "🔔 Kelmaganlarni tekshirish", "🚪 Admin paneldan chiqish",
    "📍 Lokatsiya orqali qayd etish (Fallback)"
}

@router.message(F.text)
async def handle_employee_explanation(message: Message, state: FSMContext, bot: Bot):
    """
    Catch any plain text message from an approved employee and treat it
    as an explanation/reason for absence or general communication with admin.
    """
    current_state = await state.get_state()
    if current_state is not None:
        # User is in an active FSM conversation, let other handlers process
        return

    text = message.text.strip()
    if text in IGNORED_TEXTS:
        return

    user_id = message.from_user.id
    employee = await get_employee_by_tg_id(user_id)

    if not employee or not employee.get("is_approved"):
        return

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now_time = datetime.datetime.now().strftime("%H:%M:%S")

    # Save reason to database
    await save_absence_reason(
        employee_id=employee["id"],
        record_date=today_str,
        reason_text=text
    )

    # Notify Admins
    admin_ids = await get_all_admin_ids()
    notice_text = (
        f"📩 <b>XODIMDAN KELMAGANLIK SABABI / XABAR:</b>\n\n"
        f"👤 <b>Xodim:</b> {employee['full_name']}\n"
        f"📞 <b>Telefon:</b> {employee.get('phone', '-')}\n"
        f"📅 <b>Sana:</b> {today_str} ({now_time})\n\n"
        f"💬 <b>Sababi:</b>\n<i>\"{text}\"</i>"
    )

    for a_id in admin_ids:
        try:
            await bot.send_message(chat_id=a_id, text=notice_text, parse_mode="HTML")
        except Exception as e:
            logger.error("Failed to forward reason to admin %s: %s", a_id, e)

    await message.answer(
        "✅ <b>Sababingiz qabul qilindi va rahbariyatga yetkazildi.</b>",
        parse_mode="HTML"
    )
