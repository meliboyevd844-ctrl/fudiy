import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from keyboards import (
    get_main_role_keyboard,
    get_employee_dashboard_keyboard,
    get_employee_auth_keyboard,
    get_admin_dashboard_keyboard,
)
from database.queries import (
    is_admin,
    get_employee_by_tg_id,
)
from states import AdminStates, EmployeeStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - always shows role selection buttons."""
    await state.clear()
    first_name = message.from_user.first_name or "Foydalanuvchi"

    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
        f"🏬 <b>Do'kon Keldi-Ketdi Tizimiga xush kelibsiz.</b>\n\n"
        f"Iltimos, kerakli bo'limni tanlang:"
    )
    await message.answer(welcome_text, reply_markup=get_main_role_keyboard(), parse_mode="HTML")


@router.message(F.text == "⬅️ Bosh menyuga qaytish")
@router.message(F.text == "⬅️ Bosh menyu")
@router.message(F.text == "⬅️ Bekor qilish")
async def back_to_main(message: Message, state: FSMContext):
    """Cancel current action and return to main role selection."""
    await state.clear()
    await message.answer(
        "Bosh menyu:",
        reply_markup=get_main_role_keyboard()
    )
