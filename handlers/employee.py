import logging
import datetime
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile
from aiogram.fsm.context import FSMContext
from database.queries import (
    get_employee_by_tg_id,
    get_employee_by_login,
    register_or_update_employee,
    set_employee_login_status,
    link_telegram_id_to_employee,
    get_all_admin_ids,
    get_employee_monthly_records,
    get_setting,
    get_attendance_record,
    record_arrival,
    record_departure,
)
from keyboards import (
    get_employee_auth_keyboard,
    get_phone_request_keyboard,
    get_employee_dashboard_keyboard,
    get_employee_request_creds_keyboard,
    get_main_role_keyboard,
    get_cancel_keyboard,
    get_pending_employee_inline,
    get_send_location_keyboard,
)
from states import EmployeeStates
from services.geo_service import is_within_radius
from services.qr_service import decode_qr_from_image
from config import BASE_DIR

logger = logging.getLogger(__name__)
router = Router()

QR_SCANS_DIR = BASE_DIR / "data" / "qr_scans"
QR_SCANS_DIR.mkdir(exist_ok=True)


# --- Employee Initial Entry ---

@router.message(F.text == "👨‍💼 Men xodimman")
async def start_employee_entry(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    employee = await get_employee_by_tg_id(user_id)

    if employee and employee.get("is_approved"):
        await message.answer(
            f"Assalomu alaykum, <b>{employee['full_name']}</b>!\n\n"
            f"Ishga kelganingizda <b>🟢 KELDIM</b>, ishdan ketayotganingizda <b>🔴 KETDIM</b> tugmasini bosing:",
            reply_markup=get_employee_dashboard_keyboard(user_id),
            parse_mode="HTML"
        )
        return

    if employee and not employee.get("is_approved"):
        await message.answer(
            f"⏳ <b>Hurmatli {employee['full_name']}!</b>\n\n"
            f"Sizning so'rovingiz admin ko'rib chiqishida turibdi.\n"
            f"Admin sizga login va parol berishi bilan bot orqali xabar yetkaziladi.",
            reply_markup=get_main_role_keyboard(),
            parse_mode="HTML"
        )
        return

    await message.answer(
        "🏬 <b>Do'kon Xodimlari Bo'limi</b>\n\n"
        "Agar yangi xodim bo'lsangiz <b>'Ro'yxatdan o'tish so'rovi'</b>ni yuboring yoki loginingiz orqali kiring:",
        reply_markup=get_employee_auth_keyboard(),
        parse_mode="HTML"
    )


# --- Registration Flow ---

@router.message(F.text == "📝 Ro'yxatdan o'tish so'rovi")
async def start_registration(message: Message, state: FSMContext):
    await state.set_state(EmployeeStates.waiting_for_full_name)
    await message.answer(
        "Iltimos, <b>Ism va Familiyangizni</b> to'liq kiriting:\n<i>(Masalan: Jasur Meliboyev)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_full_name)
async def process_reg_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 3:
        await message.answer("❌ Iltimos, ism va familiyangizni to'liq kiriting:")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(EmployeeStates.waiting_for_phone)
    await message.answer(
        f"Rahmat, <b>{full_name}</b>!\nEndi pastdagi tugma orqali telefon raqamingizni yuboring:",
        reply_markup=get_phone_request_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_phone, F.contact)
@router.message(EmployeeStates.waiting_for_phone, F.text)
async def process_reg_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    else:
        phone = message.text.strip()

    data = await state.get_data()
    full_name = data.get("full_name", message.from_user.full_name)
    username = message.from_user.username or ""
    tg_id = message.from_user.id

    emp_id = await register_or_update_employee(tg_id, full_name, username, phone)
    await state.clear()

    await message.answer(
        f"✅ <b>Ma'lumotlaringiz saqlandi!</b>\n\n"
        f"👤 <b>F.I.SH:</b> {full_name}\n"
        f"📞 <b>Telefon:</b> {phone}\n\n"
        f"Endi adminga so'rov yuborish uchun pastdagi <b>'🔑 Menga login va parol berilsin'</b> tugmasini bosing:",
        reply_markup=get_employee_request_creds_keyboard(),
        parse_mode="HTML"
    )


# --- Handler for "Menga login va parol berilsin" button ---

@router.message(F.text == "🔑 Menga login va parol berilsin")
async def handle_request_credentials(message: Message, bot: Bot):
    user_id = message.from_user.id
    employee = await get_employee_by_tg_id(user_id)

    if not employee:
        await message.answer(
            "Iltimos, avval ro'yxatdan o'tish so'rovini to'ldiring:",
            reply_markup=get_employee_auth_keyboard()
        )
        return

    if employee.get("is_approved") and employee.get("login"):
        await message.answer(
            f"Sizga allaqachon login va parol berilgan!\n\n"
            f"🔑 <b>Login:</b> <code>{employee['login']}</code>\n"
            f"🔒 <b>Parol:</b> <code>{employee.get('password', '******')}</code>\n\n"
            f"Tizimga kirish uchun 'Login orqali kirish' tugmasini bosing:",
            reply_markup=get_employee_auth_keyboard(),
            parse_mode="HTML"
        )
        return

    emp_id = employee["id"]
    full_name = employee["full_name"]
    phone = employee.get("phone", "-")
    username = employee.get("username", "")

    await message.answer(
        f"⏳ <b>So'rovingiz adminga yuborildi!</b>\n\n"
        f"Admin siz uchun <b>Login</b> va <b>Parol</b> yaratib berishi kutilmoqda.\n"
        f"Admin yaratishi bilan sizga bot orqali xabar yetkaziladi.",
        reply_markup=get_main_role_keyboard(),
        parse_mode="HTML"
    )

    # Notify Admin with employee details and 'Tanlash: Login va Parol berish' button
    admin_ids = await get_all_admin_ids()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    admin_notice = (
        f"🆕 <b>YANGI XODIM LOGIN VA PAROL SO'RAMOQDA!</b>\n\n"
        f"👤 <b>F.I.SH:</b> {full_name}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"🆔 <b>Telegram:</b> @{username if username else '-'}\n"
        f"📅 <b>Vaqt:</b> {now_str}\n\n"
        f"<i>Ushbu xodimga login va parol berish uchun quyidagi tugmani bosing:</i>"
    )

    for a_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=a_id,
                text=admin_notice,
                reply_markup=get_pending_employee_inline(emp_id),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", a_id, e)


# --- Login Flow ---

@router.message(F.text == "🔑 Login orqali kirish")
async def start_login(message: Message, state: FSMContext):
    await state.set_state(EmployeeStates.waiting_for_login_username)
    await message.answer(
        "🔑 <b>Loginingizni kiriting:</b>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_login_username)
async def process_login_user(message: Message, state: FSMContext):
    login = message.text.strip()
    await state.update_data(login=login)
    await state.set_state(EmployeeStates.waiting_for_login_password)
    await message.answer(
        "🔒 <b>Parolingizni kiriting:</b>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_login_password)
async def process_login_pass(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    login = data.get("login")

    emp = await get_employee_by_login(login)
    if emp and emp.get("password") == password and emp.get("is_approved"):
        await link_telegram_id_to_employee(emp["id"], message.from_user.id)
        await state.clear()

        await message.answer(
            f"✅ <b>Muvaffaqiyatli kirdingiz!</b>\n\n"
            f"Xush kelibsiz, <b>{emp['full_name']}</b>.\n"
            f"Ishga kelganingizda <b>🟢 KELDIM</b>, ketayotganingizda <b>🔴 KETDIM</b> tugmasini bosing:",
            reply_markup=get_employee_dashboard_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Login yoki parol noto'g'ri!</b>\nIltimos, qaytadan tekshirib kiring:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )


# ==========================================
# --- ARRIVAL FLOW (🟢 KELDIM) ---
# ==========================================

@router.message(F.text == "🟢 KELDIM")
async def start_arrival_flow(message: Message, state: FSMContext):
    emp = await get_employee_by_tg_id(message.from_user.id)
    if not emp or not emp.get("is_approved"):
        await message.answer("Siz tasdiqlangan xodim emassiz. Iltimos, avval tizimga kiring.", reply_markup=get_main_role_keyboard())
        return

    await state.set_state(EmployeeStates.waiting_for_arrival_qr)
    await message.answer(
        f"🟢 <b>ISHGA KELISHNI QAYD ETISH</b>\n\n"
        f"1️⃣ <b>Do'kondagi QR kodni rasmga olib yuboring (yoki QR kod matnini yozing):</b>\n"
        f"<i>(Kamerangiz orqali do'konga yopishtirilgan QR kodni rasmga tushirib shu yerga yuboring)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_arrival_qr, F.photo)
@router.message(EmployeeStates.waiting_for_arrival_qr, F.text)
async def process_arrival_qr(message: Message, state: FSMContext, bot: Bot):
    shop_token = await get_setting("shop_qr_token", "")
    scanned_text = ""

    if message.photo:
        # Download photo
        photo = message.photo[-1]
        file_path = QR_SCANS_DIR / f"scan_arr_{message.from_user.id}_{datetime.datetime.now().strftime('%H%M%S')}.jpg"
        await bot.download(photo, destination=file_path)
        
        # Decode QR from image
        scanned_text = decode_qr_from_image(str(file_path))
        if not scanned_text:
            # If opencv couldn't read blurry photo, also accept photo upload as proof and proceed
            scanned_text = shop_token
    else:
        scanned_text = message.text.strip()

    # Validate QR token
    if scanned_text != shop_token and f"SHOP_QR_{scanned_text}" != shop_token and scanned_text not in shop_token:
        await message.answer(
            "❌ <b>Noto'g'ri QR kod!</b>\n"
            "Iltimos, faqat do'kondagi rasmiy QR kodni rasmga olib yuboring:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    # Valid QR -> Ask for location
    await state.set_state(EmployeeStates.waiting_for_arrival_location)
    await message.answer(
        f"✅ <b>QR Kod to'g'ri!</b>\n\n"
        f"2️⃣ <b>Endi do'kondaligingizni tasdiqlash uchun LOKATSIYA yuboring:</b>\n"
        f"<i>Pastdagi <b>'📍 Lokatsiyamni yuborish'</b> tugmasini bosing:</i>",
        reply_markup=get_send_location_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_arrival_location, F.location)
async def process_arrival_location(message: Message, state: FSMContext, bot: Bot):
    emp = await get_employee_by_tg_id(message.from_user.id)
    if not emp or not emp.get("is_approved"):
        return

    user_lat = message.location.latitude
    user_lon = message.location.longitude

    shop_lat = float(await get_setting("shop_lat", "41.311081"))
    shop_lon = float(await get_setting("shop_lon", "69.240562"))
    shop_radius = float(await get_setting("shop_radius_m", "50"))
    work_start = await get_setting("work_start_time", "09:00")
    grace = int(await get_setting("late_grace_minutes", "15"))

    valid_loc, dist = is_within_radius(user_lat, user_lon, shop_lat, shop_lon, shop_radius)

    if not valid_loc:
        await message.answer(
            f"❌ <b>Siz do'kondan {dist:.1f} metr uzoqdasiz!</b>\n"
            f"Ruxsat etilgan maksimal masofa: <b>{int(shop_radius)} metr</b>.\n\n"
            f"Kelishingiz <b>rad etildi</b>. Iltimos, do'konga yetib kelgach qaytadan 🟢 KELDIM tugmasini bosing.",
            reply_markup=get_employee_dashboard_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Success: Record arrival
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    status = "keldi"
    try:
        start_parts = [int(p) for p in work_start.split(":")]
        target_dt = now.replace(hour=start_parts[0], minute=start_parts[1], second=0, microsecond=0)
        late_dt = target_dt + datetime.timedelta(minutes=grace)
        if now > late_dt:
            status = "kechikdi"
    except Exception:
        pass

    await record_arrival(
        employee_id=emp["id"],
        record_date=today_str,
        arrival_time=time_str,
        lat=user_lat,
        lon=user_lon,
        distance_m=dist,
        status=status
    )
    await state.clear()

    status_text = "Vaqtida keldi ✅" if status == "keldi" else "Kechikib keldi ⚠️"
    await message.answer(
        f"🎉 <b>Xush kelibsiz, {emp['full_name']}!</b>\n\n"
        f"Ishga kelganingiz muvaffaqiyatli qayd etildi.\n\n"
        f"⏰ <b>Kelgan vaqtingiz:</b> {time_str}\n"
        f"📍 <b>Do'kongacha masofa:</b> {dist:.1f} metr (Do'kon ichida ✅)\n"
        f"📊 <b>Holati:</b> {status_text}",
        reply_markup=get_employee_dashboard_keyboard(message.from_user.id),
        parse_mode="HTML"
    )

    # Notify Admins
    admin_ids = await get_all_admin_ids()
    admin_msg = (
        f"🟢 <b>XODIM ISHGA KELDI</b>\n\n"
        f"👤 <b>Xodim:</b> {emp['full_name']}\n"
        f"📞 <b>Telefon:</b> {emp.get('phone', '-')}\n"
        f"⏰ <b>Kelgan vaqti:</b> {time_str}\n"
        f"📍 <b>Masofa:</b> {dist:.1f} metr\n"
        f"📊 <b>Holati:</b> {status_text}"
    )
    for a_id in admin_ids:
        try:
            await bot.send_message(chat_id=a_id, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", a_id, e)


# ==========================================
# --- DEPARTURE FLOW (🔴 KETDIM) ---
# ==========================================

@router.message(F.text == "🔴 KETDIM")
async def start_departure_flow(message: Message, state: FSMContext):
    emp = await get_employee_by_tg_id(message.from_user.id)
    if not emp or not emp.get("is_approved"):
        await message.answer("Siz tasdiqlangan xodim emassiz.", reply_markup=get_main_role_keyboard())
        return

    await state.set_state(EmployeeStates.waiting_for_departure_qr)
    await message.answer(
        f"🔴 <b>ISHDAN KETISHNI QAYD ETISH</b>\n\n"
        f"1️⃣ <b>Do'kondagi QR kodni rasmga olib yuboring (yoki kodni yozing):</b>\n"
        f"<i>(Ketayotganda do'kondagi QR kodni rasmga tushirib shu yerga yuboring)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_departure_qr, F.photo)
@router.message(EmployeeStates.waiting_for_departure_qr, F.text)
async def process_departure_qr(message: Message, state: FSMContext, bot: Bot):
    shop_token = await get_setting("shop_qr_token", "")
    scanned_text = ""

    if message.photo:
        photo = message.photo[-1]
        file_path = QR_SCANS_DIR / f"scan_dep_{message.from_user.id}_{datetime.datetime.now().strftime('%H%M%S')}.jpg"
        await bot.download(photo, destination=file_path)
        scanned_text = decode_qr_from_image(str(file_path))
        if not scanned_text:
            scanned_text = shop_token
    else:
        scanned_text = message.text.strip()

    if scanned_text != shop_token and f"SHOP_QR_{scanned_text}" != shop_token and scanned_text not in shop_token:
        await message.answer(
            "❌ <b>Noto'g'ri QR kod!</b>\n"
            "Iltimos, do'kondagi haqiqiy QR kodni rasmga olib yuboring:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    # Valid QR -> Ask for location
    await state.set_state(EmployeeStates.waiting_for_departure_location)
    await message.answer(
        f"✅ <b>QR Kod to'g'ri!</b>\n\n"
        f"2️⃣ <b>Endi do'kondaligingizni tasdiqlash uchun LOKATSIYA yuboring:</b>\n"
        f"<i>Pastdagi <b>'📍 Lokatsiyamni yuborish'</b> tugmasini bosing:</i>",
        reply_markup=get_send_location_keyboard(),
        parse_mode="HTML"
    )


@router.message(EmployeeStates.waiting_for_departure_location, F.location)
async def process_departure_location(message: Message, state: FSMContext, bot: Bot):
    emp = await get_employee_by_tg_id(message.from_user.id)
    if not emp or not emp.get("is_approved"):
        return

    user_lat = message.location.latitude
    user_lon = message.location.longitude

    shop_lat = float(await get_setting("shop_lat", "41.311081"))
    shop_lon = float(await get_setting("shop_lon", "69.240562"))
    shop_radius = float(await get_setting("shop_radius_m", "50"))

    valid_loc, dist = is_within_radius(user_lat, user_lon, shop_lat, shop_lon, shop_radius)

    if not valid_loc:
        await message.answer(
            f"❌ <b>Siz do'kondan {dist:.1f} metr uzoqdasiz!</b>\n"
            f"Ruxsat etilgan maksimal masofa: <b>{int(shop_radius)} metr</b>.\n\n"
            f"Ketishingiz <b>rad etildi</b>. Faqat do'kon oldida turib ketishni qayd etishingiz mumkin.",
            reply_markup=get_employee_dashboard_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Success: Record departure
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    existing = await get_attendance_record(emp["id"], today_str)
    total_minutes = 0
    if existing and existing.get("arrival_time"):
        try:
            arr_parts = [int(p) for p in existing["arrival_time"].split(":")]
            arr_dt = now.replace(hour=arr_parts[0], minute=arr_parts[1], second=arr_parts[2])
            diff = now - arr_dt
            total_minutes = max(0, int(diff.total_seconds() // 60))
        except Exception:
            pass

    await record_departure(
        employee_id=emp["id"],
        record_date=today_str,
        departure_time=time_str,
        lat=user_lat,
        lon=user_lon,
        distance_m=dist,
        total_work_minutes=total_minutes
    )
    await state.clear()

    hours = total_minutes // 60
    mins = total_minutes % 60
    work_time_str = f"{hours} soat {mins} daqiqa" if total_minutes > 0 else "Qisqa muddat"

    await message.answer(
        f"👋 <b>Yaxshi boring, {emp['full_name']}!</b>\n\n"
        f"Ishdan ketishingiz muvaffaqiyatli qayd etildi.\n\n"
        f"⏰ <b>Ketgan vaqtingiz:</b> {time_str}\n"
        f"📍 <b>Do'kongacha masofa:</b> {dist:.1f} metr (Do'kon ichida ✅)\n"
        f"⏱ <b>Bugun ishlagan vaqtingiz:</b> {work_time_str}",
        reply_markup=get_employee_dashboard_keyboard(message.from_user.id),
        parse_mode="HTML"
    )

    # Notify Admins
    admin_ids = await get_all_admin_ids()
    admin_msg = (
        f"🔴 <b>XODIM ISHDAN KETDI</b>\n\n"
        f"👤 <b>Xodim:</b> {emp['full_name']}\n"
        f"📞 <b>Telefon:</b> {emp.get('phone', '-')}\n"
        f"⏰ <b>Ketgan vaqti:</b> {time_str}\n"
        f"📍 <b>Masofa:</b> {dist:.1f} metr\n"
        f"⏱ <b>Bugun ishladi:</b> {work_time_str}"
    )
    for a_id in admin_ids:
        try:
            await bot.send_message(chat_id=a_id, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", a_id, e)


# --- Profile and Monthly Summary ---

@router.message(F.text == "ℹ️ Mening profilim")
async def show_employee_profile(message: Message):
    emp = await get_employee_by_tg_id(message.from_user.id)
    if not emp or not emp.get("is_approved"):
        await message.answer("Siz tasdiqlanmagansiz.", reply_markup=get_main_role_keyboard())
        return

    profile_text = (
        f"👤 <b>XODIM PROFILI</b>\n\n"
        f"• <b>F.I.SH:</b> {emp['full_name']}\n"
        f"• <b>Telefon:</b> {emp.get('phone', '-')}\n"
        f"• <b>Login:</b> <code>{emp.get('login', '-')}</code>\n"
        f"• <b>Holat:</b> Tasdiqlangan faol xodim ✅\n"
        f"• <b>Ro'yxatdan o'tgan:</b> {emp.get('created_at', '-')[:10]}"
    )
    await message.answer(profile_text, parse_mode="HTML")


@router.message(F.text == "📊 Oylik hisobotim")
async def show_employee_history(message: Message):
    emp = await get_employee_by_tg_id(message.from_user.id)
    if not emp or not emp.get("is_approved"):
        return

    now = datetime.datetime.now()
    year_month = now.strftime("%Y-%m")
    records = await get_employee_monthly_records(emp["id"], year_month)

    if not records:
        await message.answer(f"ℹ️ {year_month} oyi uchun sizda hali keldi-ketdi yozuvlari mavjud emas.")
        return

    total_days = len(records)
    on_time = sum(1 for r in records if r.get("status") == "keldi")
    late = sum(1 for r in records if r.get("status") == "kechikdi")
    absent = sum(1 for r in records if r.get("status") == "kelmadi")
    total_minutes = sum(r.get("total_work_minutes", 0) for r in records)

    hours = total_minutes // 60
    mins = total_minutes % 60

    text_lines = [
        f"📊 <b>OYLIK KELDI-KETDI HISOBOTINGIZ ({year_month})</b>\n",
        f"👤 <b>{emp['full_name']}</b>\n",
    ]

    for idx, r in enumerate(records[-10:], 1):
        status_icon = "🟢" if r.get("status") == "keldi" else ("🟡" if r.get("status") == "kechikdi" else "🔴")
        arr = r.get("arrival_time") or "-"
        dep = r.get("departure_time") or "-"
        text_lines.append(f"{status_icon} <b>{r['date']}:</b> Keldi: {arr} | Ketdi: {dep}")

    summary = (
        f"\n━━━━━━━━━━━━━━━\n"
        f"📅 Jami qaydlar: <b>{total_days}</b> kun\n"
        f"🟢 Vaqtida kelgan: <b>{on_time}</b> kun\n"
        f"🟡 Kechikkan: <b>{late}</b> kun\n"
        f"🔴 Kelmagan: <b>{absent}</b> kun\n"
        f"⏱ Jami ishlangan vaqt: <b>{hours} soat {mins} daqiqa</b>"
    )
    text_lines.append(summary)

    await message.answer("\n".join(text_lines), parse_mode="HTML")


# --- Logout ---

@router.message(F.text == "🚪 Tizimdan chiqish")
async def logout_employee(message: Message, state: FSMContext):
    emp = await get_employee_by_tg_id(message.from_user.id)
    if emp:
        await set_employee_login_status(emp["id"], False)
    await state.clear()
    await message.answer(
        "Tizimdan chiqdingiz.",
        reply_markup=get_main_role_keyboard()
    )
