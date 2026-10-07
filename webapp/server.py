import os
import json
import logging
import datetime
from pathlib import Path
from aiohttp import web
from aiogram import Bot
from config import BASE_DIR, WEBAPP_PORT, WEBAPP_HOST
from database.queries import (
    get_setting,
    get_employee_by_tg_id,
    record_arrival,
    record_departure,
    get_attendance_record,
    get_all_admin_ids,
)
from services.geo_service import is_within_radius

logger = logging.getLogger(__name__)

STATIC_DIR = BASE_DIR / "webapp" / "static"


async def handle_index(request: web.Request) -> web.Response:
    """Serve the WebApp scanner HTML page."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return web.Response(text="WebApp index.html not found", status=404)
    return web.FileResponse(index_file)


async def handle_checkin(request: web.Request) -> web.Response:
    """
    Handle checkin/checkout API submission from the WebApp.
    Validates QR code and 50m radius GPS location.
    """
    bot: Bot = request.app["bot"]
    try:
        data = await request.json()
    except Exception as e:
        logger.error("Invalid JSON checkin request: %s", e)
        return web.json_response({"success": False, "message": "Noto'g'ri so'rov formati"}, status=400)

    action = (data.get("action") or "keldim").lower()
    qr_data = str(data.get("qr_data", "")).strip()
    user_lat = data.get("lat")
    user_lon = data.get("lon")
    tg_id = data.get("tg_id")
    init_data = data.get("init_data", "")

    # Try extracting user ID from Telegram initData if available
    if init_data and not tg_id:
        try:
            import urllib.parse
            parsed = urllib.parse.parse_qs(init_data)
            if "user" in parsed:
                user_obj = json.loads(parsed["user"][0])
                tg_id = user_obj.get("id")
        except Exception as e:
            logger.warning("Could not parse initData user: %s", e)

    if not tg_id:
        return web.json_response({
            "success": False,
            "message": "Foydalanuvchi aniqlanmadi. Iltimos, bot orqali qayta kiring."
        })

    # Find employee
    employee = await get_employee_by_tg_id(int(tg_id))
    if not employee or not employee.get("is_approved"):
        return web.json_response({
            "success": False,
            "message": "Siz tasdiqlangan xodim emassiz yoki tizimga kirmagansiz."
        })

    # Fetch store settings
    shop_token = await get_setting("shop_qr_token", "")
    shop_lat = float(await get_setting("shop_lat", "41.311081"))
    shop_lon = float(await get_setting("shop_lon", "69.240562"))
    shop_radius = float(await get_setting("shop_radius_m", "50"))
    work_start_time = await get_setting("work_start_time", "09:00")
    late_grace = int(await get_setting("late_grace_minutes", "15"))

    # 1. Validate QR Token
    if qr_data != shop_token and f"SHOP_QR_{qr_data}" != shop_token and qr_data not in shop_token:
        logger.warning("Invalid QR Code scanned by user %s: '%s' vs '%s'", tg_id, qr_data, shop_token)
        return web.json_response({
            "success": False,
            "message": "Noto'g'ri QR kod! Faqat do'konda o'rnatilgan rasmiy QR kodni skanerlang."
        })

    # 2. Validate GPS Coordinates (50m Radius)
    if user_lat is None or user_lon is None:
        return web.json_response({
            "success": False,
            "message": "GPS koordinatalari olinmadi. Lokatsiyani yoqing."
        })

    valid_location, distance_m = is_within_radius(
        float(user_lat), float(user_lon), shop_lat, shop_lon, shop_radius
    )

    if not valid_location:
        logger.warning("Employee %s is outside store radius: %sm > %sm", employee["full_name"], distance_m, shop_radius)
        return web.json_response({
            "success": False,
            "message": f"Siz do'kondan {distance_m:.1f} metr uzoqdasiz! Ruxsat etilgan maksimal masofa: {int(shop_radius)} metr. Kelish/Ketish rad etildi.",
            "distance_m": round(distance_m, 1)
        })

    # 3. Process Attendance Record
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    emp_id = employee["id"]
    emp_name = employee["full_name"]
    admin_ids = await get_all_admin_ids()

    # Save selfie image if provided
    selfie_b64 = data.get("selfie_image", "")
    saved_selfie_path = None
    if selfie_b64 and "base64," in selfie_b64:
        try:
            import base64
            from config import SELFIES_DIR
            img_data = base64.b64decode(selfie_b64.split("base64,")[1])
            selfie_filename = f"selfie_{emp_id}_{today_str}_{now.strftime('%H%M%S')}.jpg"
            saved_selfie_path = SELFIES_DIR / selfie_filename
            with open(saved_selfie_path, "wb") as f:
                f.write(img_data)
        except Exception as e:
            logger.error("Failed to save selfie image: %s", e)

    if action == "keldim":
        # Check if late
        status = "keldi"
        try:
            start_parts = [int(p) for p in work_start_time.split(":")]
            target_dt = now.replace(hour=start_parts[0], minute=start_parts[1], second=0, microsecond=0)
            late_dt = target_dt + datetime.timedelta(minutes=late_grace)
            if now > late_dt:
                status = "kechikdi"
        except Exception:
            pass

        await record_arrival(
            employee_id=emp_id,
            record_date=today_str,
            arrival_time=time_str,
            lat=float(user_lat),
            lon=float(user_lon),
            distance_m=distance_m,
            status=status,
            selfie_file=str(saved_selfie_path) if saved_selfie_path else ""
        )

        status_text = "Vaqtida keldi" if status == "keldi" else "Kechikib keldi"
        msg_to_admin = (
            f"🟢 <b>XODIM ISHGA KELDI (Jonli Selfie bilan)</b>\n\n"
            f"👤 <b>Xodim:</b> {emp_name}\n"
            f"📞 <b>Tel:</b> {employee.get('phone', '-')}\n"
            f"⏰ <b>Kelgan vaqti:</b> {time_str}\n"
            f"📍 <b>Do'kongacha masofa:</b> {distance_m:.1f} metr\n"
            f"📊 <b>Holati:</b> {status_text}"
        )

        for a_id in admin_ids:
            try:
                if saved_selfie_path and saved_selfie_path.exists():
                    from aiogram.types import FSInputFile
                    await bot.send_photo(
                        chat_id=a_id,
                        photo=FSInputFile(saved_selfie_path),
                        caption=msg_to_admin,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(chat_id=a_id, text=msg_to_admin, parse_mode="HTML")
            except Exception as e:
                logger.error("Failed to notify admin %s: %s", a_id, e)

        return web.json_response({
            "success": True,
            "message": f"Ishga kelishingiz muvaffaqiyatli qayd etildi! ({status_text})",
            "time": time_str,
            "distance_m": round(distance_m, 1),
            "status_text": status_text
        })

    elif action == "ketdim":
        existing = await get_attendance_record(emp_id, today_str)
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
            employee_id=emp_id,
            record_date=today_str,
            departure_time=time_str,
            lat=float(user_lat),
            lon=float(user_lon),
            distance_m=distance_m,
            total_work_minutes=total_minutes,
            selfie_file=str(saved_selfie_path) if saved_selfie_path else ""
        )

        hours = total_minutes // 60
        mins = total_minutes % 60
        work_time_str = f"{hours} soat {mins} daqiqa" if total_minutes > 0 else "Qisqa muddat"

        msg_to_admin = (
            f"🔴 <b>XODIM ISHDAN KETDI (Jonli Selfie bilan)</b>\n\n"
            f"👤 <b>Xodim:</b> {emp_name}\n"
            f"📞 <b>Tel:</b> {employee.get('phone', '-')}\n"
            f"⏰ <b>Ketgan vaqti:</b> {time_str}\n"
            f"📍 <b>Do'kongacha masofa:</b> {distance_m:.1f} metr\n"
            f"⏱ <b>Bugun ishladi:</b> {work_time_str}"
        )

        for a_id in admin_ids:
            try:
                if saved_selfie_path and saved_selfie_path.exists():
                    from aiogram.types import FSInputFile
                    await bot.send_photo(
                        chat_id=a_id,
                        photo=FSInputFile(saved_selfie_path),
                        caption=msg_to_admin,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(chat_id=a_id, text=msg_to_admin, parse_mode="HTML")
            except Exception as e:
                logger.error("Failed to notify admin %s: %s", a_id, e)

        return web.json_response({
            "success": True,
            "message": f"Ishdan ketishingiz qayd etildi! Bugun ishlangan vaqt: {work_time_str}",
            "time": time_str,
            "distance_m": round(distance_m, 1),
            "status_text": f"Ketdi ({work_time_str})"
        })

    return web.json_response({"success": False, "message": "Noma'lum amal"})


def create_webapp_app(bot: Bot) -> web.Application:
    """Create and configure the aiohttp WebApp server."""
    app = web.Application()
    app["bot"] = bot

    # Routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/webapp", handle_index)
    app.router.add_post("/api/checkin", handle_checkin)

    # Static assets
    app.router.add_static("/static", path=str(STATIC_DIR), name="static")

    return app
