# 🏪 Do'kon Xodimlari Keldi-Ketdi Telegram Boti va WebApp Tizimi

Ushbu tizim do'kon xodimlarining ishga kelishi va ketishini **QR kod skanerlash** hamda **50 metr radiusli GPS geolokatsiyasi** orqali nazorat qilish uchun mo'ljallangan to'liq avtomatlashtirilgan tizim.

---

## 🚀 Asosiy Imkoniyatlar va Funksiyalar

### 1. 📍 QR Kod va GPS Lokatsiya Nazorati (50 metr radius)
* **Aldovdan himoyalangan:** Xodim boshqa joyda turib QR kod rasmini skanerlasa ham tizim qabul qilmaydi! Skanerlash paytida xodimning GPS koordinatasi olinadi.
* Agar xodim admin belgilagan do'kon lokatsiyasidan **50 metr radiusdan tashqarida** bo'lsa, kelish/ketish **rad etiladi** va xodimga do'kondan qancha masofada ekanligi ko'rsatiladi.
* Telegram WebApp orqali kameradan to'g'ridan-to'g'ri QR kodni skanerlash va GPS masofani avtomatik hisoblash.

---

### 2. 🔐 Kirish va Rol Tizimi
Botga kirganda 2 ta asosiy tugma chiqadi:
* **👨‍💼 Men xodimman**
* **👑 Admin**

#### 👑 Admin Bo'limi:
* **Parol bilan himoyalangan:** Admin tugmasi bosilganda parolni so'raydi (`.env` dagi `ADMIN_PASSWORD` yoki standart `admin123`).
* **📊 Bugungi hisobot:** Bugun qaysi xodimlar soat nechada kelgani, ketgani, kimlar ishlayotgani va kimlar kelmaganini jonli ko'rsatadi.
* **📅 1 oylik hisobot (Excel):** Barcha xodimlarning oylik keldi-ketdi jadvalini chiroyli formatlangan **`.xlsx` (Excel)** fayl qilib Telegramga yuboradi (F.I.SH, telefon, sana, hafta kuni, kelgan/ketgan vaqti, holati, ishlagan soatlari).
* **⏳ Kutilayotgan so'rovlar:** Yangi xodim ro'yxatdan o'tmoqchi bo'lganda adminga bildirishnoma boradi. Admin 1 ta tugma orqali tasdiqlab, xodimga **Login** va **Parol** beradi.
* **🖨️ Do'kon QR Kodini olish:** Do'konga yopishtirish uchun tayyor, maxsus tokenli printable QR kod rasmini generatsiya qiladi.
* **📍 Do'kon lokatsiyasini sozlash:** Admin do'konda turib geolokatsiya yuboradi va radiusni (50 metr) belgilaydi.
* **⏰ Ish vaqti sozlamalari:** Ish boshlanish/tugash vaqti va kechikish chegarasini (masalan, 09:00 18:00 15) o'rnatish.
* **📨 Kelmaganlar sabablari:** Kelmagan xodimlar yozgan tushuntirish xatlarini ko'rish.

#### 👨‍💼 Xodim Bo'limi:
* **Ro'yxatdan o'tish:** Yangi xodim Ism-familiyasi va telefon raqamini yuboradi -> Adminga tasdiqlash so'rovi boradi.
* **Login va Parol bilan kirish:** Admin login va parol berganidan so'ng tizimga kiradi.
* **🟢 KELDIM:** Kelganda do'kondagi QR kodni skanerlaydi + GPS tekshiriladi -> Kelgan vaqti saqlanadi va Adminga xabar boradi.
* **🔴 KETDIM:** Ketayotganda QR kodni skanerlaydi -> Ketgan vaqti va bugun necha soat ishlagani hisoblanib Adminga xabar boradi.
* **📊 Oylik hisobotim:** Xodim o'zining kelgan/ketgan kunlari va jami ishlagan soatlarini ko'ra oladi.
* **ℹ️ Mening profilim:** O'z ma'lumotlarini tekshirish.

---

### 3. ⏰ Avtomatik Eslatmalar va Sabab So'rash (Scheduler)
* Agar xodim belgilangan ish boshlanish vaqtigacha (masalan 09:15) kelib skaner qilmasa, tizim uni avtomatik tarzda **"Kelmadi"** deb belgilaydi.
* Bot xodimga avtomatik xabar yuboradi:
  > *"⚠️ Hurmatli Jasur, siz bugun ishga kelmadingiz. Kelmaganligingiz sababi bormi? Iltimos, sababini ushbu botga yozib yuboring."*
* Xodim sababini yozib botga yuborishi bilan, ushbu sabab zudlik bilan **Adminga bildirishnoma** bo'lib boradi!

---

## 📁 Loyiha Tuzilishi

```
keldi keti bot/
├── .env                     # Sozlamalar (Bot token, admin parol, port...)
├── .env.example             # Namunaviy sozlamalar fayli
├── requirements.txt         # Kerakli Python kutubxonalari
├── run.bat                  # Windows uchun 1-bosishda ishga tushirish fayli
├── main.py                  # Asosiy ishga tushirish nuqtasi
├── config.py                # Konfiguratsiya moduli
├── keyboards.py             # Telegram tugmalari va menyular
├── states.py                # FSM holatlari (Step-by-step jarayonlar)
│
├── database/
│   ├── db.py                # SQLite bazasini ishga tushirish va jadvallar
│   └── queries.py           # Barcha async CRUD so'rovlari
│
├── handlers/
│   ├── start.py             # /start va asosiy rol tanlash
│   ├── admin.py             # Admin paneli funksiyalari
│   ├── employee.py          # Xodim ro'yxatdan o'tishi, kirishi va harakatlari
│   └── reasons.py           # Kelmaganlik sabablarini qabul qilish va adminga uzatish
│
├── services/
│   ├── geo_service.py       # Haversine GPS masofa hisoblagich (50m tekshirish)
│   ├── qr_service.py        # Printable QR kod rasm generatori
│   ├── excel_service.py     # Oylik rangli Excel (.xlsx) hisobot generatori
│   └── scheduler_service.py # Avtomatik eslatma va kelmaganlarni tekshirish jadvali
│
├── webapp/
│   ├── server.py            # Aiohttp WebApp serveri va Checkin API
│   └── static/
│       ├── index.html       # WebApp Skaner sahifasi
│       ├── css/style.css    # Premium qorong'u dizayn va animatsiyalar
│       └── js/app.js        # GPS va QR kamera skaneri logikasi
│
└── data/                    # Ma'lumotlar papkasi (Baza, QR kodlar, Excel hisobotlar)
```

---

## 🛠 O'rnatish va Ishga Tushirish

### 1-qadam: Bot Token olish
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring va botingizga nom bering.
3. BotFather bergan `TOKEN` ni nusxalab oling.

### 2-qadam: Sozlamalarni kiritish
Loyiha papkasidagi `.env` faylini oching va bot tokeningizni yozing:
```env
BOT_TOKEN=123456789:AAF...sizning_tokeningiz
ADMIN_PASSWORD=admin123
SHOP_RADIUS_METERS=50
```

### 3-qadam: Ishga tushirish
Windows tizimida shunchaki **`run.bat`** faylini 2 marta bosing yoki terminalda:
```powershell
py main.py
```

---

## 📱 WebApp Skanerini Sozlash (Internet orqali ochish)
Telegram WebApp telefonda ishlashi uchun HTTPS havolaga ega bo'lishi kerak.
Lokal kompyuterda sinash uchun **Ngrok** yoki **Cloudflare Tunnel** orqali 8080 portni ochishingiz mumkin:
```powershell
ngrok http 8080
```
Keyin hosil bo'lgan `https://...ngrok-free.app` manzilini `.env` faylidagi `WEBAPP_BASE_URL` qatoriga yozasiz:
```env
WEBAPP_BASE_URL=https://sizning-subdomain.ngrok-free.app
```
*(Eslatma: Xodimlar oddiy Telegram geolokatsiyasi orqali ham to'g'ridan-to'g'ri qayd etishlari mumkin - "Lokatsiya orqali qayd etish" tugmasi mavjud).*
