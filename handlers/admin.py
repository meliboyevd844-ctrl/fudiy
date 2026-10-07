import logging
import datetime
import secrets
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from database.queries import (
    is_admin,
    add_admin,
    get_setting,
    set_setting,
    get_all_approved_employees,
    get_all_pending_employees,
    get_employee_by_id,
    approve_employee,
    delete_employee,
    get_today_attendance_all,
    get_monthly_attendance_all,
    get_recent_absence_reasons,
)
from keyboards import (
    get_admin_dashboard_keyboard,
    get_main_role_keyboard,
    get_cancel_keyboard,
    get_pending_employee_inline,
    get_employee_dashboard_keyboard,
)
from states import AdminStates
from services.qr_service import generate_shop_qr_image
from services.excel_service import generate_monthly_excel_report
from services.scheduler_service import run_daily_absence_check

logger = logging.getLogger(__name__)
router = Router()


# --- Admin Authentication in 2 Steps ---

@router.message(F.text == "👑 Admin")
async def start_admin_flow(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_admin_login_step)
    await message.answer(
        "👑 <b>Admin Paneliga Kirish</b>\n\n"
        "1️⃣ <b>Admin Loginingizni kiriting:</b>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_admin_login_step)
async def process_admin_step1_login(message: Message, state: FSMContext):
    login_attempt = message.text.strip()
    await state.update_data(admin_login_attempt=login_attempt)
    await state.set_state(AdminStates.waiting_for_admin_password_step)

    await message.answer(
        "2️⃣ <b>Admin Parolingizni kiriting:</b>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_admin_password_step)
async def process_admin_step2_password(message: Message, state: FSMContext):
    from database.queries import verify_admin_credentials
    pass_attempt = message.text.strip()
    data = await state.get_data()
    login_attempt = data.get("admin_login_attempt", "admin")

    is_valid = await verify_admin_credentials(login_attempt, pass_attempt)

    if is_valid:
        await add_admin(message.from_user.id)
        await state.clear()
        await message.answer(
            "✅ <b>Muvaffaqiyatli kirdingiz!</b>\nAdmin boshqaruv paneliga xush kelibsiz.",
            reply_markup=get_admin_dashboard_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Login yoki parol noto'g'ri!</b>\n\n"
            "Iltimos, qaytadan loginingizni kiriting:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_admin_login_step)


# --- Change Admin Login and Password ---

@router.message(F.text == "🔑 Admin Login/Parol o'zgartirish")
async def start_change_admin_creds(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    cur_login = await get_setting("admin_login", "admin")
    await state.set_state(AdminStates.waiting_for_new_admin_login)
    await message.answer(
        f"🔑 <b>Admin kirish ma'lumotlarini o'zgartirish</b>\n\n"
        f"• Hozirgi login: <code>{cur_login}</code>\n\n"
        f"Yangi <b>Admin Logini</b>ni kiriting:\n<i>(Masalan: boshliq, manager, admin1)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_new_admin_login)
async def process_new_admin_login(message: Message, state: FSMContext):
    new_login = message.text.strip()
    if len(new_login) < 3:
        await message.answer("❌ Login kamida 3 ta belgidan iborat bo'lishi kerak:")
        return

    await state.update_data(new_admin_login=new_login)
    await state.set_state(AdminStates.waiting_for_new_admin_password)
    await message.answer(
        f"Yangi login: <b>{new_login}</b>\n\n"
        f"Endi yangi <b>Admin Paroli</b>ni kiriting:\n<i>(Masalan: parol2026, do'kon777)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_new_admin_password)
async def process_new_admin_password(message: Message, state: FSMContext):
    new_password = message.text.strip()
    if len(new_password) < 4:
        await message.answer("❌ Parol kamida 4 ta belgidan iborat bo'lishi kerak:")
        return

    data = await state.get_data()
    new_login = data.get("new_admin_login")

    from database.queries import update_admin_credentials
    await update_admin_credentials(new_login, new_password)
    await state.clear()

    await message.answer(
        f"✅ <b>Admin kirish ma'lumotlari muvaffaqiyatli yangilandi!</b>\n\n"
        f"🔑 <b>Yangi Login:</b> <code>{new_login}</code>\n"
        f"🔒 <b>Yangi Parol:</b> <code>{new_password}</code>",
        reply_markup=get_admin_dashboard_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🚪 Admin paneldan chiqish")
async def logout_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Bosh menyuga qaytdingiz:",
        reply_markup=get_main_role_keyboard()
    )


# --- 1. Today's Report ---

@router.message(F.text == "📊 Bugungi hisobot")
async def show_today_report(message: Message):
    if not await is_admin(message.from_user.id):
        return

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    records = await get_today_attendance_all(today_str)

    if not records:
        await message.answer(
            f"ℹ️ <b>Bugun ({today_str}) uchun hech qanday xodim mavjud emas yoki tasdiqlanmagan.</b>",
            parse_mode="HTML"
        )
        return

    text_lines = [f"📊 <b>BUGUNGI KELDI-KETDI HISOBOTI</b>\n📅 <i>Sana: {today_str}</i>\n"]
    
    arrived_count = 0
    left_count = 0
    absent_count = 0

    for idx, r in enumerate(records, 1):
        name = r.get("full_name", "Noma'lum")
        arr = r.get("arrival_time")
        dep = r.get("departure_time")
        status = r.get("status")

        if arr:
            arrived_count += 1
            status_icon = "🟢" if status == "keldi" else "🟡"
            arr_info = f"Keldi: {arr}"
            dep_info = f"Ketdi: {dep}" if dep else "Ishlamoqda ⏳"
            if dep:
                left_count += 1
            line = f"{idx}. {status_icon} <b>{name}</b>\n   └ ⏰ {arr_info} | {dep_info} ({r.get('arrival_distance_m', 0):.0f}m)"
        else:
            absent_count += 1
            line = f"{idx}. 🔴 <b>{name}</b>\n   └ ❌ Kelmadi / Qayd etilmadi"

        text_lines.append(line)

    summary = (
        f"\n━━━━━━━━━━━━━━━\n"
        f"👥 Jami xodimlar: <b>{len(records)}</b>\n"
        f"🟢 Kelganlar: <b>{arrived_count}</b>\n"
        f"🔴 Kelmaganlar: <b>{absent_count}</b>\n"
        f"🚪 Ishdan ketganlar: <b>{left_count}</b>"
    )
    text_lines.append(summary)

    await message.answer("\n".join(text_lines), parse_mode="HTML")


# --- 2. Monthly Excel Report ---

@router.message(F.text == "📅 1 oylik hisobot (Excel)")
async def generate_monthly_report(message: Message):
    if not await is_admin(message.from_user.id):
        return

    now = datetime.datetime.now()
    year_month = now.strftime("%Y-%m")
    
    await message.answer("⏳ 1 oylik Excel hisobot shakllantirilmoqda, iltimos kuting...")

    records = await get_monthly_attendance_all(year_month)
    if not records:
        await message.answer(f"ℹ️ {year_month} oyi uchun hali ma'lumotlar mavjud emas.")
        return

    excel_path = generate_monthly_excel_report(records, now.year, now.month)
    doc_file = FSInputFile(excel_path)

    caption = (
        f"📁 <b>{year_month} Oylik Keldi-Ketdi Hisoboti</b>\n\n"
        f"• Jami yozuvlar soni: <b>{len(records)}</b> ta\n"
        f"• Shakllantirilgan vaqt: {now.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Ushbu faylni Microsoft Excel yoki WPS Office dasturi orqali ochib ko'rishingiz mumkin."
    )
    await message.answer_document(document=doc_file, caption=caption, parse_mode="HTML")


# --- 3. Shop QR Code Generation ---

@router.message(F.text == "🖨️ Do'kon QR Kodini olish")
async def send_shop_qr_code(message: Message):
    if not await is_admin(message.from_user.id):
        return

    shop_token = await get_setting("shop_qr_token", "")
    if not shop_token:
        shop_token = "SHOP_QR_" + secrets.token_hex(6).upper()
        await set_setting("shop_qr_token", shop_token)

    qr_image_path = generate_shop_qr_image(shop_token, shop_name="DO'KON KELDI-KETDI")
    photo = FSInputFile(qr_image_path)

    caption = (
        f"🖨️ <b>DO'KON UCHUN RASMIY QR KOD</b>\n\n"
        f"🔑 <b>Maxsus Token:</b> <code>{shop_token}</code>\n\n"
        f"📌 <b>Qo'llanma:</b>\n"
        f"1. Ushbu QR kod rasmini printerdan qog'ozga chiqarib oling.\n"
        f"2. Do'koningiz kirish qismiga yoki kassaga yopishtirib qo'ying.\n"
        f"3. Xodimlar kelganda va ketganda bot orqali ushbu QR kodni skanerlashadi.\n\n"
        f"<i>Eslatma: Xodim skaner qilganda uning GPS lokatsiyasi ham 50 metr radiusda bo'lishi shart!</i>"
    )
    await message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")


# --- 4. Pending Employee Registrations & Approval Flow ---

@router.message(F.text == "➕ Xodim qo'shish (So'rovlar)")
@router.message(F.text == "⏳ Kutilayotgan so'rovlar")
async def show_pending_requests(message: Message):
    if not await is_admin(message.from_user.id):
        return

    pending = await get_all_pending_employees()
    if not pending:
        await message.answer("ℹ️ Hozircha yangi so'rov yuborgan xodimlar yo'q.", parse_mode="HTML")
        return

    await message.answer(f"📋 <b>Tasdiqlash kutilayotgan xodimlar ({len(pending)} ta):</b>", parse_mode="HTML")

    for emp in pending:
        emp_id = emp["id"]
        msg = (
            f"👤 <b>F.I.SH:</b> {emp['full_name']}\n"
            f"📞 <b>Telefon:</b> {emp.get('phone', '-')}\n"
            f"🆔 <b>Telegram:</b> @{emp.get('username') or '-'}\n"
            f"📅 <b>So'rov vaqti:</b> {emp.get('created_at', '-')}"
        )
        await message.answer(msg, reply_markup=get_pending_employee_inline(emp_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("approve_emp:"))
async def approve_emp_callback(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Ruxsat berilmagan", show_alert=True)
        return

    emp_id = int(callback.data.split(":")[1])
    emp = await get_employee_by_id(emp_id)
    if not emp:
        await callback.answer("Xodim topilmadi!", show_alert=True)
        return

    await state.update_data(target_emp_id=emp_id, target_emp_name=emp["full_name"], target_emp_tg_id=emp["telegram_id"])
    await state.set_state(AdminStates.waiting_for_emp_login)

    prompt = (
        f"👤 <b>Xodim:</b> {emp['full_name']}\n"
        f"📞 <b>Telefon:</b> {emp.get('phone', '-')}\n\n"
        f"1️⃣ <b>Ushbu xodim uchun LOGIN kiriting:</b>\n"
        f"<i>(Masalan: xodim_{emp_id}, jasur, botir)</i>"
    )
    await callback.message.answer(prompt, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_for_emp_login)
async def process_emp_step1_login(message: Message, state: FSMContext):
    login = message.text.strip()
    if len(login) < 2:
        await message.answer("❌ Login juda qisqa. Iltimos, kamida 2 ta belgi kiriting:")
        return

    data = await state.get_data()
    emp_name = data.get("target_emp_name", "Xodim")

    await state.update_data(emp_login=login)
    await state.set_state(AdminStates.waiting_for_emp_password)

    await message.answer(
        f"👤 <b>Xodim:</b> {emp_name}\n"
        f"🔑 <b>Login:</b> <code>{login}</code> qabul qilindi!\n\n"
        f"2️⃣ <b>Endi ushbu xodim uchun PAROL kiriting:</b>\n"
        f"<i>(Masalan: 123456, parol777, do'kon123)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_emp_password)
async def process_emp_step2_password(message: Message, state: FSMContext, bot: Bot):
    password = message.text.strip()
    if len(password) < 3:
        await message.answer("❌ Parol juda qisqa. Iltimos, kamida 3 ta belgi kiriting:")
        return

    data = await state.get_data()
    emp_id = data.get("target_emp_id")
    emp_name = data.get("target_emp_name")
    emp_tg_id = data.get("target_emp_tg_id")
    login = data.get("emp_login")

    # Approve and save credentials in DB
    await approve_employee(emp_id, login, password)
    await state.clear()

    await message.answer(
        f"✅ <b>Xodimga login va parol muvaffaqiyatli berildi!</b>\n\n"
        f"👤 <b>Xodim:</b> {emp_name}\n"
        f"🔑 <b>Login:</b> <code>{login}</code>\n"
        f"🔒 <b>Parol:</b> <code>{password}</code>\n\n"
        f"Ushbu ma'lumotlar xodimning Telegramiga avtomatik yuborildi.",
        reply_markup=get_admin_dashboard_keyboard(),
        parse_mode="HTML"
    )

    # Send Notification to Employee
    if emp_tg_id:
        try:
            from keyboards import get_employee_auth_keyboard
            emp_msg = (
                f"🎉 <b>Hurmatli {emp_name}!</b>\n\n"
                f"Sizning xodimlik so'rovingiz admin tomonidan tasdiqlandi va sizga kirish ma'lumotlari berildi:\n\n"
                f"🔑 <b>Sizning Loginingiz:</b> <code>{login}</code>\n"
                f"🔒 <b>Sizning Parolingiz:</b> <code>{password}</code>\n\n"
                f"Tizimga kirish uchun pastdagi <b>'🔑 Login orqali kirish'</b> tugmasini bosing va ushbu login/parolni kiriting:"
            )
            await bot.send_message(
                chat_id=emp_tg_id,
                text=emp_msg,
                reply_markup=get_employee_auth_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error("Failed to notify approved employee: %s", e)


@router.callback_query(F.data.startswith("reject_emp:"))
async def reject_emp_callback(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return

    emp_id = int(callback.data.split(":")[1])
    emp = await get_employee_by_id(emp_id)
    if emp:
        await delete_employee(emp_id)
        await callback.message.edit_text(f"❌ Xodim <b>{emp['full_name']}</b> so'rovi rad etildi va o'chirildi.", parse_mode="HTML")
    await callback.answer()


# --- 5. Employee List ---

@router.message(F.text == "👥 Xodimlar ro'yxati")
async def show_all_employees(message: Message):
    if not await is_admin(message.from_user.id):
        return

    employees = await get_all_approved_employees()
    if not employees:
        await message.answer("ℹ️ Tasdiqlangan faol xodimlar mavjud emas.")
        return

    text_lines = [f"👥 <b>TASDIQLANGAN XODIMLAR RO'YXATI ({len(employees)} nafar)</b>\n"]
    for idx, e in enumerate(employees, 1):
        line = (
            f"{idx}. 👤 <b>{e['full_name']}</b>\n"
            f"   📞 {e.get('phone', '-')}\n"
            f"   🔑 Login: <code>{e.get('login', '-')}</code> | Parol: <code>{e.get('password', '-')}</code>"
        )
        text_lines.append(line)

    await message.answer("\n".join(text_lines), parse_mode="HTML")


# --- 6. Set Store Geolocation & Radius ---

@router.message(F.text == "📍 Do'kon lokatsiyasini sozlash (GPS)")
@router.message(F.text == "📍 Do'kon lokatsiyasini sozlash")
async def prompt_store_location(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    from keyboards import get_admin_location_keyboard
    cur_lat = await get_setting("shop_lat", "41.311081")
    cur_lon = await get_setting("shop_lon", "69.240562")
    cur_radius = await get_setting("shop_radius_m", "50")

    await state.set_state(AdminStates.waiting_for_shop_location)
    await message.answer(
        f"📍 <b>DO'KON / QR KOD JOYLANISHINI BELGILASH</b>\n\n"
        f"• Hozirgi koordinata: <code>{cur_lat}, {cur_lon}</code>\n"
        f"• Ruxsat etilgan radius: <b>{cur_radius} metr</b>\n\n"
        f"📌 <b>Qo'llanma:</b>\n"
        f"Do'koningizda (QR kod yopishtirilgan joyda) turib, pastdagi <b>'📍 Hozirgi joylashuvimni (Do'kon lokatsiyasini) yuborish'</b> tugmasini 1 marta bosing:",
        reply_markup=get_admin_location_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_shop_location, F.location)
async def process_shop_location(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude

    await set_setting("shop_lat", str(lat))
    await set_setting("shop_lon", str(lon))
    radius = float(await get_setting("shop_radius_m", "50"))

    await state.clear()
    await message.answer(
        f"✅ <b>Do'kon lokatsiyasi muvaffaqiyatli belgilandi va tasdiqlandi!</b>\n\n"
        f"📍 <b>Do'kon markazi:</b>\n"
        f"• Kenglik (Lat): <code>{lat}</code>\n"
        f"• Uzunlik (Lon): <code>{lon}</code>\n"
        f"📏 <b>Ruxsat etilgan radius:</b> <b>{radius:.0f} metr</b>\n\n"
        f"Endi xodimlar do'kondan {radius:.0f} metr radius ichida bo'lgandagina kelish va ketishni qayd eta oladilar.",
        reply_markup=get_admin_dashboard_keyboard(),
        parse_mode="HTML"
    )


# --- 7. Work Hours Settings ---

@router.message(F.text == "⏰ Ish vaqti (Kelish/Ketish)")
@router.message(F.text == "⏰ Ish vaqti sozlamalari")
async def show_work_time_settings(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    start_time = await get_setting("work_start_time", "09:00")
    end_time = await get_setting("work_end_time", "18:00")
    grace = await get_setting("late_grace_minutes", "15")

    await state.set_state(AdminStates.waiting_for_work_times)
    await message.answer(
        f"⏰ <b>XODIMLAR ISH VAQTI SOZLAMALARI:</b>\n\n"
        f"• 🟢 Ish boshlanish vaqti (Kelish): <b>{start_time}</b>\n"
        f"• 🔴 Ish tugash vaqti (Ketish): <b>{end_time}</b>\n"
        f"• ⏳ Kechikishga ruxsat (daqiqa): <b>{grace} daqiqa</b>\n\n"
        f"O'zgartirish uchun yangi vaqtlarni quyidagi formatda yozib yuboring:\n"
        f"<code>kelish_vaqti ketish_vaqti kechikish_daqiqasi</code>\n\n"
        f"<i>Masalan:</i> <code>09:00 18:00 15</code> yoki <code>08:30 19:00 10</code>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_work_times)
async def process_work_times(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer(
            "❌ Format noto'g'ri!\n"
            "Iltimos, probel bilan ajratib yozing: <code>09:00 18:00 15</code>",
            parse_mode="HTML"
        )
        return

    start_t, end_t, grace = parts[0], parts[1], parts[2]
    await set_setting("work_start_time", start_t)
    await set_setting("work_end_time", end_t)
    await set_setting("late_grace_minutes", grace)
    await state.clear()

    await message.answer(
        f"✅ <b>Ish vaqtlari yangilandi!</b>\n\n"
        f"• 🟢 Kelish vaqti: <b>{start_t}</b>\n"
        f"• 🔴 Ketish vaqti: <b>{end_t}</b>\n"
        f"• ⏳ Kechikish chegarasi: <b>{grace} daqiqa</b>\n\n"
        f"Xodimlar ushbu vaqtdan kechiksa avtomatik 'Kechikdi' deb belgilanadi va sababi so'raladi.",
        reply_markup=get_admin_dashboard_keyboard(),
        parse_mode="HTML"
    )


# --- 8. Absent Reasons List ---

@router.message(F.text == "📨 Kelmaganlar sabablari")
async def show_absence_reasons(message: Message):
    if not await is_admin(message.from_user.id):
        return

    reasons = await get_recent_absence_reasons(limit=15)
    if not reasons:
        await message.answer("ℹ️ Hozircha xodimlardan kelmaganlik sabablari xabari kelmagan.")
        return

    text_lines = ["📨 <b>XODIMLARDAN KELGAN SABABLAR RO'YXATI:</b>\n"]
    for idx, r in enumerate(reasons, 1):
        line = (
            f"{idx}. 👤 <b>{r['full_name']}</b> ({r.get('phone', '-')})\n"
            f"   📅 Sana: {r['date']}\n"
            f"   💬 Sabab: <i>\"{r['reason_text']}\"</i>\n"
            f"   ⏰ Yozilgan vaqti: {r.get('created_at', '-')}\n"
        )
        text_lines.append(line)

    await message.answer("\n".join(text_lines), parse_mode="HTML")


# --- 9. Trigger Absence Check Manually ---

@router.message(F.text == "🔔 Kelmaganlarni tekshirish")
async def trigger_absence_check(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    await message.answer("🔍 Bugun kelmagan xodimlar tekshirilmoqda va ularga sabab so'rab xabar yuborilmoqda...")
    await run_daily_absence_check(bot)
    await message.answer("✅ Tekshiruv yakunlandi!")
