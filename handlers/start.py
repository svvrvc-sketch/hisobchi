from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from database.db import register_user
from utils.keyboards import main_menu_keyboard

router = Router()

START_TEXT = (
    "👋 <b>Assalomu alaykum!</b>\n\n"
    "Men sizning <b>Hisobchi AI — Aqlli Cho'ntak Buxgalteringizman</b>. 🤖💼✨\n\n"
    "Barcha daromad, xarajat, cheklar va qarzlaringizni men bilan oson nazorat qilib boring!\n\n"
    "🚀 <b>Yangi aqlli imkoniyatlar:</b>\n"
    "• 📸 <b>Chek tanish (Vision AI):</b> Do'kon yoki kafe chekini rasmga olib yuboring — summasi, toifasi va xaridlarini o'zim kiritaman.\n"
    "• 🎙 <b>Ovozli boshqaruv:</b> <i>«40 ming tushlik, 20 ming taksi, kartadan 100 ming dori»</i> — bir nechta xarajatni bir gapda aytishingiz mumkin!\n"
    "• 🤝 <b>Qarz daftari:</b> <i>«Akromga 300 ming qarz berdim»</i> yoki <i>«Akrom qarzini qaytardi»</i> desangiz, qarzlar hisobini yuritaman.\n"
    "• 🎯 <b>Oylik byudjet:</b> <i>«Oziq-ovqatga 2 mln limit»</i> deb limit qo'ying, oshganda ogohlantiraman.\n"
    "• 🧠 <b>AI Maslahatchi:</b> Hisobotlar bo'limida shaxsiy moliyaviy tahlil va maslahat oling.\n\n"
    "👇 <i>Quyidagi menyu orqali boshlashingiz mumkin:</i>"
)

HELP_TEXT = (
    "❓ <b>Yordam va Qo'llanma</b>\n\n"
    "Botdan foydalanish juda oddiy — xuddi insonga gapirgandek muloqot qiling:\n\n"
    "📸 <b>1. Chek va kvitansiyalar:</b>\n"
    "Korzinka, Havas, dorixona yoki kafe chekini rasmga olib yuboring — sun'iy intellekt xarajatni avtomatik hisoblaydi.\n\n"
    "🎙 <b>2. Ovozli va yozma buyruqlar:</b>\n"
    "• <i>«25 ming taksiga berdim»</i> (bitta xarajat)\n"
    "• <i>«50 ming tushlik, 20 ming taksi, 100 ming dori»</i> (ko'p xarajat)\n"
    "• <i>«Kartamga 1.5 mln oylik tushdi»</i> (daromad)\n\n"
    "🤝 <b>3. Qarz daftari:</b>\n"
    "• <i>«Akromga 300 ming qarz berdim»</i>\n"
    "• <i>«Sardordan 500 ming qarz oldim»</i>\n"
    "• <i>«Akrom qarzini qaytardi»</i>\n\n"
    "🎯 <b>4. Byudjet limitlari:</b>\n"
    "• <i>«Oziq-ovqatga 2 mln limit»</i>\n"
    "• <i>«Umumiy xarajatimga 5 mln limit»</i>\n\n"
    "📊 <b>5. Hisobot, AI Maslahatchi va Excel:</b>\n"
    "<b>«📊 Hisobot & Statistika»</b> bo'limida qarzlar, byudjetlar, AI tahlil va Excel hisobot mavjud."
)

from utils.keyboards import main_menu_keyboard, webapp_inline_keyboard

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await register_user(user.id, user.full_name, user.username)
    await message.answer(
        START_TEXT, 
        parse_mode="HTML", 
        reply_markup=webapp_inline_keyboard(user.id)
    )
    await message.answer(
        "👇 <i>Pastdagi menyu orqali ham ilovani istalgan vaqtda ochishingiz mumkin:</i>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )

@router.message(Command("help"))
@router.message(F.text == "❓ Yordam")
@router.message(F.text == "🎙 Ovozli buyruqlar haqida")
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML", reply_markup=main_menu_keyboard())

@router.message(Command("webapp"))
@router.message(F.text == "📱 Ilovani ochish")
async def cmd_webapp(message: Message):
    user_id = message.from_user.id
    text = (
        "✨ <b>Hisobchi AI — Telegram Mini App</b>\n\n"
        "Barcha moliyangiz, xarajatlar tahlili, cheklar va qarzlaringizni qulay interfeysda boshqarish uchun pastdagi tugmani bosing:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=webapp_inline_keyboard(user_id))

