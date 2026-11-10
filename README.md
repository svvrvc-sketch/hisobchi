# 🎙 Aqlli Ovozli Yordamchi & Shaxsiy Moliya Telegram Boti

Telegram uchun zamonaviy **Python (Aiogram 3)** va sun'iy intellekt (AI Whisper) asosida yaratilgan **Aqlli Ovozli Yordamchi va Moliya boti**.

Bot ovozli xabarlarni (voice) va oddiy matnli xabarlarni tushunadi, xarajatlar va daromadlarni avtomatik hisoblab boradi, hamda eslatmalarni o'z vaqtida foydalanuvchiga yetkazadi.

---

## 🌟 Asosiy Imkoniyatlar

1. **🎙 Ovozli boshqaruv (Speech-to-Text):**
   - Ovozli xabar yuborasiz: *«Tushlikka 45 ming ketdi»* -> bot ovozni matnga o'giradi, toifani (*🍔 Oziq-ovqat*) va summani aniqlab bazaga saqlaydi.
   - Eslatma ovozi: *«15 daqiqadan keyin choy damlashni eslat»* -> bot vaqtni hisoblab kerakli daqiqada xabar beradi.

2. **📊 Shaxsiy Moliya va Balans nazorati:**
   - Xarajat va daromadlarni toifalar bo'yicha guruhlash.
   - Kunlik, haftalik, oylik va umumiy hisobotlar.
   - Foizlar va qoldiq balans ko'rsatkichi.
   - Qo'lda tugmalar yoki FSM orqali ham kiritish imkoniyati.

3. **⏰ Aqlli Eslatmalar (Reminders):**
   - Istalgan vaqtga (masalan: *«ertaga soat 15:00 da majlis»*, *«30 daqiqadan keyin»*) eslatmalar qo'yish.
   - Faol eslatmalarni ko'rish va bekor qilish (o'chirish).
   - Server qayta ishga tushsa ham kutilayotgan eslatmalar bazadan tiklanadi.

---

## 🚀 O'rnatish va Ishga Tushirish

### 1. Bot Tokenini olish:
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring va botingizga nom hamda username bering.
3. BotFather sizga bergan tokenni nusxalang (masalan: `7123456789:AAH...`).

### 2. Sozlamalarni kiritish (.env):
Loyiha papkasidagi `.env` faylini oching va tokenni yozing:
```env
BOT_TOKEN=7123456789:AAH...sizning_tokeningiz
GROQ_API_KEY=
```
*(Eslatma: Ovozli xabarlarni matnga o'girish uchun [console.groq.com](https://console.groq.com) saytidan bepul API kalit olib `GROQ_API_KEY=` ga qo'yishingiz mumkin. Agar qo'yilmasa ham, bot barcha matnli buyruqlar va menyu tugmalari bilan to'liq ishlayveradi).*

### 3. Botni ishga tushirish:
Virtual muhit (venv) faollashtirilgan holda quyidagi buyruqni bering:
```bash
python bot.py
```
Yoki to'g'ridan-to'g'ri:
```bash
.\venv\Scripts\python.exe bot.py
```

---

## 📁 Loyiha Arxitekturasi

```
tgbot/
├── bot.py                  # Asosiy ishga tushirish fayli
├── config.py               # Sozlamalar va muhit o'zgaruvchilari
├── database/
│   ├── __init__.py
│   └── db.py               # SQLite (aiosqlite) asinxron ma'lumotlar bazasi
├── handlers/
│   ├── __init__.py
│   ├── start.py            # /start, /help va qo'llanma
│   ├── finance.py          # Moliya hisoboti va qo'lda kiritish
│   ├── reminders.py        # Eslatmalar boshqaruvi
│   ├── voice.py            # Ovozli xabarlarni qayta ishlash (STT + AI)
│   └── smart_text.py       # Erkin matnli aqlli buyruqlar
├── services/
│   ├── __init__.py
│   ├── nlp_parser.py       # O'zbekcha gaplardan summa va vaqtni ajratish
│   ├── stt.py              # Groq Whisper ovoz tanish moduli
│   └── scheduler.py        # APScheduler eslatma rejalashtiruvchisi
├── utils/
│   ├── __init__.py
│   └── keyboards.py        # Chiroyli inline va reply tugmalar
├── requirements.txt        # Kerakli Python kutubxonalari
└── .env                    # Maxfiy tokenlar
```
