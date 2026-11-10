import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.db import (
    add_transaction, get_summary, get_all_transactions,
    get_active_debts, mark_debt_paid, get_budgets
)
from utils.keyboards import (
    period_inline_keyboard, categories_keyboard,
    cancel_inline_keyboard, main_menu_keyboard,
    excel_period_keyboard, payment_method_keyboard,
    income_categories_keyboard, skip_description_keyboard,
    debts_inline_keyboard, budgets_inline_keyboard,
    back_to_report_keyboard
)
from services.nlp_parser import parse_amount
from services.excel_exporter import generate_excel_report
from services.ai_advisor import generate_financial_advice

logger = logging.getLogger(__name__)
router = Router()

class TransactionFSM(StatesGroup):
    waiting_for_amount = State()
    waiting_for_payment_method = State()
    waiting_for_category = State()
    waiting_for_custom_category = State()
    waiting_for_description = State()

def format_number(val: float) -> str:
    """Raqamlarni chiroyli ajratib ko'rsatish (masalan: 120,000)"""
    return f"{int(val):,}".replace(",", " ")

def generate_report_text(summary: dict) -> str:
    period_names = {
        "today": "📅 Bugungi kunlik",
        "week": "🗓 Shu haftalik",
        "month": "📆 Shu oylik",
        "all": "📈 Umumiy barcha davr"
    }
    title = period_names.get(summary["period"], "Moliya")
    
    income = summary["income"]
    expense = summary["expense"]
    balance = summary["balance"]
    
    income_cash = summary.get("income_cash", 0)
    income_card = summary.get("income_card", 0)
    expense_cash = summary.get("expense_cash", 0)
    expense_card = summary.get("expense_card", 0)
    cash_bal = summary.get("cash_balance", 0)
    card_bal = summary.get("card_balance", 0)
    
    bal_sign = "🟢" if balance >= 0 else "🔴"

    text = (
        f"📊 <b>{title} hisobot:</b>\n"
        f"────────────────────\n"
        f"💰 <b>Jami daromad:</b> +{format_number(income)} so'm\n"
        f"  ├ 💵 Naqd: +{format_number(income_cash)} so'm\n"
        f"  └ 💳 Karta: +{format_number(income_card)} so'm\n\n"
        f"💸 <b>Jami xarajat:</b> -{format_number(expense)} so'm\n"
        f"  ├ 💵 Naqd: -{format_number(expense_cash)} so'm\n"
        f"  └ 💳 Karta: -{format_number(expense_card)} so'm\n\n"
        f"{bal_sign} <b>Sof balans:</b> {format_number(balance)} so'm\n"
        f"  ├ 💵 Naqd hamyon: {format_number(cash_bal)} so'm\n"
        f"  └ 💳 Karta hisob: {format_number(card_bal)} so'm\n\n"
    )

    if summary["categories"]:
        text += "📁 <b>Xarajatlar tarkibi:</b>\n"
        total_exp = expense if expense > 0 else 1
        for cat in summary["categories"]:
            pct = int((cat["sum_amount"] / total_exp) * 100)
            text += f"• {cat['category']}: <b>{format_number(cat['sum_amount'])} so'm</b> ({pct}%)\n"
        text += "\n"
    else:
        text += "ℹ️ <i>Ushbu davrda xarajatlar mavjud emas.</i>\n\n"

    if summary["recent"]:
        text += "🕒 <b>Oxirgi amallar:</b>\n"
        for r in summary["recent"]:
            sign = "+" if r["type"] == "income" else "-"
            dt_str = r["created_at"][11:16] if len(r["created_at"]) >= 16 else ""
            pay = r.get("payment_method", "")
            pay_str = f" [{pay}]" if pay else ""
            desc = f" ({r['description']})" if r.get("description") else ""
            text += f"• {r['category']}{pay_str}: <b>{sign}{format_number(r['amount'])}</b> so'm {desc} <i>[{dt_str}]</i>\n"
            
    return text

@router.message(F.text == "📊 Hisobot & Statistika")
async def show_report(message: Message):
    summary = await get_summary(message.from_user.id, period="month")
    await message.answer(
        generate_report_text(summary),
        parse_mode="HTML",
        reply_markup=period_inline_keyboard()
    )

@router.callback_query(F.data.startswith("report_period_"))
async def change_report_period(callback: CallbackQuery):
    period = callback.data.replace("report_period_", "")
    summary = await get_summary(callback.from_user.id, period=period)
    await callback.message.edit_text(
        generate_report_text(summary),
        parse_mode="HTML",
        reply_markup=period_inline_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "ai_advisor")
async def show_ai_advisor(callback: CallbackQuery):
    await callback.message.edit_text("⏳ <i>AI Moliyaviy Maslahatchi hisoblaringizni tahlil qilmoqda...</i>", parse_mode="HTML")
    await callback.answer()
    
    advice = await generate_financial_advice(callback.from_user.id)
    await callback.message.edit_text(
        advice,
        parse_mode="HTML",
        reply_markup=back_to_report_keyboard()
    )

@router.callback_query(F.data == "view_debts")
async def show_debts(callback: CallbackQuery):
    user_id = callback.from_user.id
    debts = await get_active_debts(user_id)
    
    given = debts["given"]
    taken = debts["taken"]
    tot_given = debts["total_given"]
    tot_taken = debts["total_taken"]
    
    text = (
        "🤝 <b>Qarz Daftari («Berdilar-Oldilar» hisobi)</b>\n"
        "────────────────────\n\n"
        f"🟢 <b>Sizga qaytarilishi kerak (haqqingiz):</b> +{format_number(tot_given)} so'm\n"
    )
    if given:
        for g in given:
            dt = g["created_at"][:10] if g.get("created_at") else ""
            desc = f" ({g['description']})" if g.get("description") else ""
            text += f"• <b>{g['person_name']}</b>: {format_number(g['amount'])} so'm{desc} <i>[{dt}]</i>\n"
    else:
        text += "<i>Haqdorlik yozuvlari yo'q.</i>\n"
        
    text += f"\n🔴 <b>Siz qaytarishingiz kerak (qarzingiz):</b> -{format_number(tot_taken)} so'm\n"
    if taken:
        for t in taken:
            dt = t["created_at"][:10] if t.get("created_at") else ""
            desc = f" ({t['description']})" if t.get("description") else ""
            text += f"• <b>{t['person_name']}</b>: {format_number(t['amount'])} so'm{desc} <i>[{dt}]</i>\n"
    else:
        text += "<i>Qarz majburiyatlari yo'q.</i>\n"
        
    text += (
        "\n💡 <i>Yangi qarz qo'shish uchun shunchaki yozing yoki ovoz yuboring:</i>\n"
        "• <i>«Akromga 300 ming qarz berdim»</i>\n"
        "• <i>«Sardordan 500 ming qarz oldim»</i>\n"
        "• <i>«Akrom qarzini qaytardi»</i>\n\n"
        "Qarz qaytarilgan bo'lsa, quyidagi tugma orqali uni yopishingiz mumkin 👇"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=debts_inline_keyboard(debts)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_debt_"))
async def process_pay_debt(callback: CallbackQuery):
    debt_id = int(callback.data.replace("pay_debt_", ""))
    user_id = callback.from_user.id
    
    success = await mark_debt_paid(debt_id, user_id)
    if success:
        await callback.answer("✅ Qarz muvaffaqiyatli yopildi!", show_alert=True)
    else:
        await callback.answer("⚠️ Qarz topilmadi yoki allaqachon yopilgan.", show_alert=True)
        
    # Ro'yxatni yangilash
    await show_debts(callback)

@router.callback_query(F.data == "view_budgets")
async def show_budgets(callback: CallbackQuery):
    user_id = callback.from_user.id
    budgets = await get_budgets(user_id)
    
    text = (
        "🎯 <b>Oylik Byudjet va Xarajat Limitlari</b>\n"
        "────────────────────\n\n"
    )
    if budgets:
        for b in budgets:
            text += f"• <b>{b['category']}</b>: {format_number(b['monthly_limit'])} so'm / oyiga\n"
        text += (
            "\nℹ️ <i>Ushbu toifalar bo'yicha xarajat 80% va 100% ga yetganda bot sizni darhol ogohlantiradi.</i>\n"
        )
    else:
        text += (
            "<i>Sizda hozircha oylik byudjet limitlari o'rnatilmagan.</i>\n\n"
            "💡 Limit qo'yish orqali xarajatlaringiz nazoratdan chiqib ketishining oldini olasiz!\n"
        )
        
    text += (
        "\n✍️ <i>Yangi limit qo'yish uchun shunchaki yozing yoki ovoz yuboring:</i>\n"
        "• <i>«Oziq-ovqatga 2 mln limit»</i>\n"
        "• <i>«Umumiy oylik xarajatimga 6 mln limit»</i>"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=budgets_inline_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "set_new_budget")
async def explain_set_budget(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎯 <b>Yangi limit o'rnatish juda oson!</b>\n\n"
        "Istalgan vaqtda botga oddiy matn yoki ovoz bilan ayting:\n\n"
        "• <i>«Oziq-ovqatga 2 mln limit»</i>\n"
        "• <i>«Transportga 800 ming limit»</i>\n"
        "• <i>«Umumiy xarajatimga 5 mln limit»</i>\n\n"
        "Bot buni avtomatik tushunadi va oylik byudjetingizga kiritib qo'yadi! ⚡️",
        parse_mode="HTML",
        reply_markup=back_to_report_keyboard()
    )
    await callback.answer()

# --- Excel eksport qismi ---

@router.message(F.text == "📥 Excel yuklab olish")
async def show_excel_menu(message: Message):
    await message.answer(
        "📥 <b>Qaysi davr uchun hisobotni Excel (.xlsx) formatida yuklab olmoqchisiz?</b>\n\n"
        "Kerakli davrni tanlang:",
        parse_mode="HTML",
        reply_markup=excel_period_keyboard()
    )

@router.callback_query(F.data == "export_excel_current")
async def export_current_to_excel(callback: CallbackQuery):
    await callback.message.answer(
        "📥 <b>Excel uchun davrni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=excel_period_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("excel_"))
async def export_period_to_excel(callback: CallbackQuery):
    period = callback.data.replace("excel_", "")
    period_labels = {
        "today": "Bugungi kunlik",
        "week": "Shu haftalik",
        "month": "Shu oylik",
        "all": "Barcha davr (to'liq)"
    }
    label = period_labels.get(period, "Barcha davr")
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name or "Foydalanuvchi"

    status_msg = await callback.message.answer("⏳ <i>Excel jadval tayyorlanmoqda...</i>", parse_mode="HTML")
    await callback.answer()

    txs = await get_all_transactions(user_id, period=period)
    if not txs:
        await status_msg.edit_text(f"📭 <b>{label}</b> bo'yicha hech qanday xarajat yoki daromad yozuvlari topilmadi.", parse_mode="HTML")
        return

    try:
        excel_path = generate_excel_report(txs, user_name, period_name=label)
        file_name = f"Moliya_Hisoboti_{period}.xlsx"
        
        await callback.message.answer_document(
            document=FSInputFile(excel_path, filename=file_name),
            caption=(
                f"📊 <b>Moliya hisobotingiz tayyor!</b>\n\n"
                f"🗓 Davr: <b>{label}</b>\n"
                f"📝 Jami amallar: <b>{len(txs)} ta</b>\n\n"
                f"<i>Faylni ochib barcha hisob-kitoblarni qulay ko'rishingiz mumkin.</i>"
            ),
            parse_mode="HTML"
        )
        await status_msg.delete()
        if os.path.exists(excel_path):
            os.remove(excel_path)
    except Exception as e:
        logger.error(f"Excel yaratishda xatolik: {e}")
        await status_msg.edit_text(f"❌ Excel faylni yaratishda xatolik yuz berdi: {e}")

# --- Qo'lda Xarajat / Daromad kiritish ---

@router.message(F.text == "➕ Xarajat qo'shish")
async def start_add_expense(message: Message, state: FSMContext):
    await state.set_state(TransactionFSM.waiting_for_amount)
    await state.update_data(trans_type="expense")
    await message.answer(
        "💸 <b>Xarajat summasini kiriting:</b>\n"
        "<i>(Masalan: 35000 yoki 35 ming)</i>\n\n"
        "ℹ️ <i>Keyingi bosqichda to'lov usuli (💵 Naqd yoki 💳 Karta) hamda toifani tanlaysiz.</i>\n\n"
        "🎙 <b>Yoki shunchaki ovozli xabar yuboring!</b>\n"
        "<i>«Kartadan 25 ming tushlikka to'ladim» deb ovoz yuborsangiz ham avtomatik saqlaydi! ⚡️</i>",
        parse_mode="HTML",
        reply_markup=cancel_inline_keyboard()
    )

@router.message(F.text == "💰 Daromad qo'shish")
async def start_add_income(message: Message, state: FSMContext):
    await state.set_state(TransactionFSM.waiting_for_amount)
    await state.update_data(trans_type="income")
    await message.answer(
        "💰 <b>Daromad summasini kiriting:</b>\n"
        "<i>(Masalan: 500000 yoki 500 ming)</i>\n\n"
        "ℹ️ <i>Keyingi bosqichda hisob turi (💵 Naqd yoki 💳 Karta) hamda manbani tanlaysiz.</i>\n\n"
        "🎙 <b>Yoki shunchaki ovozli xabar yuboring!</b>\n"
        "<i>«Kartamga 1 mln oylik tushdi» deb ovoz yuborsangiz ham avtomatik saqlanadi! ⚡️</i>",
        parse_mode="HTML",
        reply_markup=cancel_inline_keyboard()
    )

@router.message(TransactionFSM.waiting_for_amount, F.text)
async def process_amount(message: Message, state: FSMContext):
    if not message.text:
        return
    val = parse_amount(message.text)
    if not val or val <= 0:
        await message.answer(
            "⚠️ Summani to'g'ri kiritmadingiz. Iltimos raqam yoki matn bilan yozing (Masalan: <i>45000</i> yoki <i>45 ming</i>):",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    trans_type = data.get("trans_type", "expense")
    await state.update_data(amount=val)
    await state.set_state(TransactionFSM.waiting_for_payment_method)

    action_label = "daromad" if trans_type == "income" else "xarajat"
    sign = "+" if trans_type == "income" else "-"
    await message.answer(
        f"💵 Summa: <b>{sign}{format_number(val)} so'm</b>\n\n"
        f"1️⃣ <b>Pul qanday hisob orqali amalga oshirildi?</b>",
        parse_mode="HTML",
        reply_markup=payment_method_keyboard(trans_type)
    )

@router.callback_query(TransactionFSM.waiting_for_payment_method, F.data.startswith("pay_"))
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    method_code = parts[1]
    trans_type = parts[2]
    
    pay_method = "💵 Naqd" if method_code == "naqd" else "💳 Karta"
    await state.update_data(payment_method=pay_method)
    await state.set_state(TransactionFSM.waiting_for_category)

    data = await state.get_data()
    amount = data["amount"]

    if trans_type == "income":
        await callback.message.edit_text(
            f"💵 Summa: <b>+{format_number(amount)} so'm</b>\n"
            f"💳 Hisob turi: <b>{pay_method}</b>\n\n"
            f"2️⃣ <b>Daromad manbasi / toifasini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=income_categories_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"💵 Summa: <b>-{format_number(amount)} so'm</b>\n"
            f"💳 Hisob turi: <b>{pay_method}</b>\n\n"
            f"2️⃣ <b>Xarajat toifasini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=categories_keyboard("expense")
        )
    await callback.answer()

@router.callback_query(TransactionFSM.waiting_for_category, F.data.startswith("inc_cat_"))
async def process_income_category(callback: CallbackQuery, state: FSMContext):
    cat_code = callback.data.replace("inc_cat_", "")

    if cat_code == "custom":
        await state.set_state(TransactionFSM.waiting_for_custom_category)
        await callback.message.edit_text(
            "✍️ <b>Yangi daromad toifasi nomini yozing:</b>\n\n"
            "<i>Masalan: «Yaqinim orqali», «Ijara tushumi», «Frilans loyiha»</i>",
            parse_mode="HTML",
            reply_markup=cancel_inline_keyboard()
        )
        await callback.answer()
        return

    data = await state.get_data()
    amount = data["amount"]
    pay_method = data.get("payment_method", "💵 Naqd")
    await state.update_data(category=cat_code)
    await state.set_state(TransactionFSM.waiting_for_description)

    await callback.message.edit_text(
        f"💵 Summa: <b>+{format_number(amount)} so'm</b>\n"
        f"💳 Hisob turi: <b>{pay_method}</b>\n"
        f"📁 Toifa: <b>{cat_code}</b>\n\n"
        f"3️⃣ <b>Daromad uchun izoh / sharh yozing:</b>\n"
        f"<i>(Masalan: «Oktabr oyi oyligi», «Kassadan kunlik tushum», «Loyiha uchun to'lov»)</i>\n\n"
        f"<i>Agar izoh kiritmoqchi bo'lmasangiz, quyidagi tugmani bosing:</i>",
        parse_mode="HTML",
        reply_markup=skip_description_keyboard()
    )
    await callback.answer()

@router.callback_query(TransactionFSM.waiting_for_category, F.data.startswith("cat_"))
async def process_expense_category(callback: CallbackQuery, state: FSMContext):
    cat_code = callback.data.replace("cat_", "")

    if cat_code == "custom":
        await state.set_state(TransactionFSM.waiting_for_custom_category)
        await callback.message.edit_text(
            "✍️ <b>Yangi xarajat toifasi nomini yozing:</b>\n\n"
            "<i>Masalan: «Kredit to'lovi», «Usta haqqi», «Bolalar bog'chasi», «Ijara to'lovi»</i>",
            parse_mode="HTML",
            reply_markup=cancel_inline_keyboard()
        )
        await callback.answer()
        return

    data = await state.get_data()
    amount = data["amount"]
    pay_method = data.get("payment_method", "💵 Naqd")
    await state.update_data(category=cat_code)
    await state.set_state(TransactionFSM.waiting_for_description)

    await callback.message.edit_text(
        f"💵 Summa: <b>-{format_number(amount)} so'm</b>\n"
        f"💳 Hisob turi: <b>{pay_method}</b>\n"
        f"📁 Toifa: <b>{cat_code}</b>\n\n"
        f"3️⃣ <b>Xarajat uchun izoh / sharh yozing:</b>\n"
        f"<i>(Masalan: «Tushlik osh markazida», «Cobalt moy almashtirish», «Bozorlik»)</i>\n\n"
        f"<i>Agar izoh kiritmoqchi bo'lmasangiz, quyidagi tugmani bosing:</i>",
        parse_mode="HTML",
        reply_markup=skip_description_keyboard()
    )
    await callback.answer()

@router.message(TransactionFSM.waiting_for_custom_category, F.text)
async def process_custom_category(message: Message, state: FSMContext):
    custom_cat = message.text.strip()
    if not custom_cat:
        return

    data = await state.get_data()
    trans_type = data.get("trans_type", "expense")
    amount = data["amount"]
    pay_method = data.get("payment_method", "💵 Naqd")
    category = f"✨ {custom_cat}"
    await state.update_data(category=category)
    await state.set_state(TransactionFSM.waiting_for_description)

    action_label = "daromad" if trans_type == "income" else "xarajat"
    sign = "+" if trans_type == "income" else "-"

    await message.answer(
        f"💵 Summa: <b>{sign}{format_number(amount)} so'm</b>\n"
        f"💳 Hisob turi: <b>{pay_method}</b>\n"
        f"📁 Toifa: <b>{category}</b>\n\n"
        f"3️⃣ <b>Ushbu {action_label} uchun qisqa izoh yozing:</b>\n"
        f"<i>(Agar izoh yozishni istamasangiz, pastdagi tugmani bosing)</i>",
        parse_mode="HTML",
        reply_markup=skip_description_keyboard()
    )

@router.message(TransactionFSM.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if not desc:
        return

    data = await state.get_data()
    trans_type = data.get("trans_type", "expense")
    amount = data["amount"]
    category = data.get("category", "📦 Boshqa")
    pay_method = data.get("payment_method", "💵 Naqd")

    action_title = "Daromad" if trans_type == "income" else "Xarajat"
    sign = "+" if trans_type == "income" else "-"

    await add_transaction(
        user_id=message.from_user.id,
        trans_type=trans_type,
        amount=amount,
        category=category,
        description=desc,
        payment_method=pay_method
    )
    await state.clear()

    msg = (
        f"✅ <b>{action_title} muvaffaqiyatli saqlandi!</b>\n\n"
        f"💵 <b>Summa:</b> {sign}{format_number(amount)} so'm\n"
        f"💳 <b>Hisob turi:</b> {pay_method}\n"
        f"📁 <b>Toifa:</b> {category}\n"
        f"📝 <b>Izoh:</b> {desc}"
    )
    await message.answer(msg, parse_mode="HTML")

@router.callback_query(TransactionFSM.waiting_for_description, F.data == "skip_description")
async def process_skip_description(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trans_type = data.get("trans_type", "expense")
    amount = data["amount"]
    category = data.get("category", "📦 Boshqa")
    pay_method = data.get("payment_method", "💵 Naqd")

    action_title = "Daromad" if trans_type == "income" else "Xarajat"
    sign = "+" if trans_type == "income" else "-"

    await add_transaction(
        user_id=callback.from_user.id,
        trans_type=trans_type,
        amount=amount,
        category=category,
        description="-",
        payment_method=pay_method
    )
    await state.clear()

    msg = (
        f"✅ <b>{action_title} muvaffaqiyatli saqlandi!</b>\n\n"
        f"💵 <b>Summa:</b> {sign}{format_number(amount)} so'm\n"
        f"💳 <b>Hisob turi:</b> {pay_method}\n"
        f"📁 <b>Toifa:</b> {category}\n"
        f"📝 <b>Izoh:</b> - (izohsiz)"
    )
    await callback.message.edit_text(msg, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Amal bekor qilindi.")
    await callback.answer()
