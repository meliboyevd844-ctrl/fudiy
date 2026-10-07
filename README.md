# 🏬 Do'kon Keldi-Ketdi Telegram Bot Tizimi

Ushbu loyiha do'kon xodimlarining ishga kelishi va ketishini **GPS Lokatsiya (50 metr radius)** hamda **Do'kon QR Kodi** orqali aniq va avtomatlashtirilgan tarzda qayd etuvchi zamonaviy Telegram bot tizimidir.

---

## 🚀 Asosiy Imkoniyatlar

### 👨‍💼 Xodimlar uchun:
1. **Oson ro'yxatdan o'tish:** Ism-familiya va telefon raqami yuboriladi.
2. **"🔑 Menga login va parol berilsin" tugmasi:** Adminga so'rov boradi va admin tasdiqlab login/parol beradi.
3. **🟢 KELDIM (Ishga kelish):**
   - 1-qadam: Do'konga yopishtirilgan rasmiy QR kodni rasmga olib yuborish.
   - 2-qadam: `[📍 Lokatsiyamni yuborish]` tugmasini 1 marta bosish.
   - Agar xodim do'kondan 50 metr radius ichida bo'lsa — muvaffaqiyatli qabul qilinadi va adminga bildirishnoma boradi.
4. **🔴 KETDIM (Ishdan ketish):**
   - Do'kon oldida turib QR kod va Lokatsiya yuboriladi.
   - Bugun ishlagan jami vaqti (soat va daqiqa) hisoblab chiqariladi.
5. **📊 Oylik hisobotim:** O'zining oylik davomati va ishlagan vaqtlarini ko'rish.
6. **💬 Sabab yuborish:** Ishga kelmagan taqdirda botga sababini yozib qoldirish (adminga yetkaziladi).

### 👑 Admin Boshqaruvi:
1. **2 bosqichli xavfsiz kirish:** Admin login va paroli so'raladi (asl parollar ekranda ko'rinmaydi).
2. **➕ Xodim qo'shish (So'rovlar):** Yangi ro'yxatdan o'tgan xodimlarga 1 tugma orqali Login va Parol berish.
3. **📍 Do'kon lokatsiyasini sozlash (GPS):** Admin do'konda turib 1 marta `[📍 Hozirgi joylashuvimni yuborish]` tugmasini bosadi va do'kon koordinatasi (50m radius) saqlanadi.
4. **🖨️ Do'kon QR Kodini olish:** Do'konga yopishtirish uchun tayyor chiroyli rasmiy QR kod rasmini generatsiya qilish.
5. **📊 Bugungi hisobot:** Kimlar kelgan, kimlar ishlamoqda, kimlar ketgan va kimlar kelmaganini jonli ko'rish.
6. **📅 1 oylik hisobot (Excel):** Rangli, jadvallangan rasmiy `.xlsx` Excel faylni yuklab olish.
7. **⏰ Ish vaqti sozlamalari:** Ish boshlanish/tugash vaqtlari va kechikish chegarasini belgilash.
8. **🔔 Kelmaganlarni avtomatik nazorat qilish:** Ertalab kelmagan xodimlardan avtomatik sabab so'rash va adminga yetkazish.

---

## ⚡ Yuqori Yuklama (High-Concurrency) va Barqarorlik
- **SQLite WAL Mode (`PRAGMA journal_mode=WAL;`):** Yuzlab xodimlar bir vaqtda (masalan soat 09:00 da) so'rov yuborganda ham baza qotib qolmaydi va bloklanmaydi.
- **30 soniyalik Busy Timeout (`timeout=30.0`):** Hech qanday so'rov yo'qolmaydi.
- **Database Indekslari:** `date`, `employee_id`, `telegram_id` ustunlariga indekslar o'rnatilgan bo'lib, hisobotlar bir zumda ochiladi.
- **Avtomatik Reconnect:** Tarmoqda uzilish bo'lsa bot o'z-o'zidan qayta ulanadi.

---

## 🛠️ O'rnatish va Ishga Tushirish

### 1. Loyihani yuklab olish:
```bash
git clone https://github.com/meliboyevd844-ctrl/fudiy.git
cd fudiy
```

### 2. Virtual muhit va kutubxonalarni o'rnatish:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. `.env` faylini sozlash:
Loyiha papkasida `.env` faylini oching yoki yarating:
```env
BOT_TOKEN=8477072563:AAFuLJMMyR4gWY1mVLtbQauk9WzhYngPKSM
ADMIN_ID=6767118452
ADMIN_LOGIN=admin
ADMIN_PASSWORD=adminzohid

# Do'kon sozlamalari
SHOP_LATITUDE=41.311081
SHOP_LONGITUDE=69.240562
SHOP_RADIUS_METERS=50.0

# Ish vaqti
WORK_START_TIME=09:00
WORK_END_TIME=18:00
LATE_GRACE_MINUTES=15
```

### 4. Botni ishga tushirish:
```bash
python main.py
```

---

## ☁️ Render.com da 24/7 Bepul Serverga Joylash (Deploy)

1. [Render.com](https://render.com) ga kiring va **GitHub** profilingiz bilan ulaning.
2. **New +** -> **Web Service** ni tanlang.
3. `fudiy` repozitoriyasini tanlang.
4. Quyidagi parametrlarni kiriting:
   - **Name:** `keldi-ketdi-bot`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
5. **Environment Variables** bo'limiga `.env` dagi o'zgaruvchilarni qo'shing (`BOT_TOKEN`, `ADMIN_ID`, `ADMIN_PASSWORD` va h.k.).
6. **Deploy Web Service** tugmasini bosing.

Bot 24/7 rejimda to'xtovsiz ishlaydi! 🚀
