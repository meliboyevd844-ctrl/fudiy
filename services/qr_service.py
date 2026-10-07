import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from config import QR_DIR

def generate_shop_qr_image(qr_token: str, shop_name: str = "DO'KON KELDI-KETDI") -> Path:
    """
    Generate a high-quality printable QR code image for the shop.
    Embeds the shop token in the QR code.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(qr_token)
    qr.make(fit=True)

    # Generate QR Image
    qr_img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF").convert("RGB")
    
    # Add Header / Title Canvas
    w, h = qr_img.size
    padding_top = 80
    padding_bottom = 60
    total_w = w
    total_h = h + padding_top + padding_bottom

    canvas = Image.new("RGB", (total_w, total_h), color="#FFFFFF")
    draw = ImageDraw.Draw(canvas)

    # Draw border around the entire sheet
    draw.rectangle([(8, 8), (total_w - 9, total_h - 9)], outline="#0284C7", width=4)

    # Draw Text Title
    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_sub = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Draw Title
    title_text = shop_name.upper()
    draw.text((total_w / 2, 35), title_text, fill="#0F172A", font=font_title, anchor="mm")
    draw.text((total_w / 2, 60), "Xodimlarning kelish va ketishini qayd etish", fill="#64748B", font=font_sub, anchor="mm")

    # Paste QR Code
    canvas.paste(qr_img, (0, padding_top))

    # Draw Bottom Instructions
    draw.text((total_w / 2, total_h - 35), "Telegram bot orqali skanerlang", fill="#0284C7", font=font_sub, anchor="mm")

    output_path = QR_DIR / f"shop_qr_{qr_token[:10]}.png"
    canvas.save(output_path, "PNG", quality=95)
    return output_path


def decode_qr_from_image(image_path: str) -> str:
    """
    Decode QR code from an image file.
    Uses cv2 / pyzbar if available.
    """
    try:
        import cv2
        img = cv2.imread(str(image_path))
        if img is not None:
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(img)
            if data:
                return data.strip()
    except Exception:
        pass

    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
        img = Image.open(image_path)
        decoded = decode(img)
        if decoded:
            return decoded[0].data.decode("utf-8").strip()
    except Exception:
        pass

    return ""
