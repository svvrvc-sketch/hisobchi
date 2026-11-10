import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from services.nlp_parser import parse_smart_input
from database.db import add_transaction, add_debt, close_debt_by_name, set_budget, check_budget_alerts
from handlers.finance import format_number

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text & ~F.text.startswith("/"))
async def handle_smart_text(message: Message, bot: Bot):
    text = message.text.strip()
    
    # Asosiy menyu tugmalarini chetlab o'tish
    menu_buttons = [
        "➕ Xarajat qo'shish", "💰 Daromad qo'shish",
        "📊 Hisobot & Statistika", "📥 Excel yuklab olish",
        "🎙 Ovozli buyruqlar haqida", "❓ Yordam"
    ]
    if text in menu_buttons:
        return

    logger.info(f"💬 [MATNLI XABAR]: '{text}'")
    user_id = message.from_user.id
    parsed = await parse_smart_input(text)
    action_type = parsed["type"]

    if action_type == "finance":
        items = parsed.get("items", [])
        all_alerts = []

        if len(items) == 1:
            it = items[0]
            trans_type = it["trans_type"]
            amount = it["amount"]
            category = it["category"]
            desc = it["description"]
            pay_method = it.get("payment_method", "💵 Naqd")

            await add_transaction(
                user_id=user_id,
                trans_type=trans_type,
                amount=amount,
                category=category,
                description=desc,
                payment_method=pay_method
            )

            if trans_type == "expense":
                alerts = await check_budget_alerts(user_id, category, amount)
                all_alerts.extend(alerts)

            sign = "+" if trans_type == "income" else "-"
            title = "Daromad kiritildi" if trans_type == "income" else "Xarajat kiritildi"

            reply_text = (
                f"✅ <b>{title}!</b>\n\n"
                f"💵 <b>Summa:</b> {sign}{format_number(amount)} so'm\n"
                f"💳 <b>Hisob turi:</b> {pay_method}\n"
                f"📁 <b>Toifa:</b> {category}\n"
                f"📝 <b>Izoh:</b> {desc}"
            )
            if all_alerts:
                reply_text += "\n\n" + "\n\n".join(all_alerts)

            await message.answer(reply_text, parse_mode="HTML")

        elif len(items) > 1:
            total_sum = 0
            lines = []
            for idx, it in enumerate(items, 1):
                trans_type = it["trans_type"]
                amount = it["amount"]
                category = it["category"]
                desc = it["description"]
                pay_method = it.get("payment_method", "💵 Naqd")
                total_sum += amount if trans_type == "income" else -amount

                await add_transaction(
                    user_id=user_id,
                    trans_type=trans_type,
                    amount=amount,
                    category=category,
                    description=desc,
                    payment_method=pay_method
                )
                if trans_type == "expense":
                    alerts = await check_budget_alerts(user_id, category, amount)
                    all_alerts.extend(alerts)

                sign = "+" if trans_type == "income" else "-"
                lines.append(f"{idx}. {category}: <b>{sign}{format_number(amount)} so'm</b> [{pay_method}] <i>({desc})</i>")

            sign_tot = "+" if total_sum >= 0 else "-"
            reply_text = (
                f"✅ <b>{len(items)} ta amal muvaffaqiyatli saqlandi!</b>\n\n"
                + "\n".join(lines) + "\n\n"
                f"📊 <b>Jami o'zgarish:</b> {sign_tot}{format_number(abs(total_sum))} so'm"
            )
            if all_alerts:
                reply_text += "\n\n" + "\n\n".join(all_alerts)

            await message.answer(reply_text, parse_mode="HTML")

    elif action_type == "debt":
        action = parsed.get("action", "add")
        person = parsed.get("person_name", "Noma'lum")
        amt = parsed.get("amount", 0)

        if action == "pay":
            closed = await close_debt_by_name(user_id, person)
            if closed:
                await message.answer(
                    f"🤝 <b>Qarz yopildi!</b>\n\n"
                    f"👤 Shaxs: <b>{closed['person_name']}</b>\n"
                    f"💵 Summa: <b>{format_number(closed['amount'])} so'm</b>\n\n"
                    f"✅ <i>Qarz daftarchasida to'langan deb belgilandi.</i>",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"ℹ️ <b>{person}</b> bo'yicha faol qarz yozuvi topilmadi.",
                    parse_mode="HTML"
                )
        else:
            debt_type = parsed.get("debt_type", "given")
            desc = parsed.get("description", "Qarz")
            await add_debt(user_id, person, debt_type, amt, desc)
            type_label = "🟢 Qarz berildi (Sizga qaytarishi kerak)" if debt_type == "given" else "🔴 Qarz olindi (Siz qaytarishingiz kerak)"

            await message.answer(
                f"🤝 <b>Qarz daftarchasiga yozildi!</b>\n\n"
                f"👤 Shaxs: <b>{person}</b>\n"
                f"💵 Summa: <b>{format_number(amt)} so'm</b>\n"
                f"📌 Holat: <b>{type_label}</b>\n"
                f"📝 Izoh: {desc}",
                parse_mode="HTML"
            )

    elif action_type == "budget":
        cat = parsed.get("category", "Umumiy")
        lim = parsed.get("monthly_limit", 0)
        await set_budget(user_id, cat, lim)

        await message.answer(
            f"🎯 <b>Oylik byudjet o'rnatildi!</b>\n\n"
            f"📁 Toifa: <b>{cat}</b>\n"
            f"💰 Oylik limit: <b>{format_number(lim)} so'm</b>\n\n"
            f"ℹ️ <i>Xarajatlaringiz 80% va 100% ga yetganda sizni ogohlantirib boraman.</i>",
            parse_mode="HTML"
        )

    else:
        # Tushunilmagan tasodifiy matn
        await message.answer(
            "🤔 Ushbu xabardan aniq moliyaviy ma'lumot topa olmadim.\n\n"
            "💡 <b>Namunalar:</b>\n"
            "• <i>«25 ming taksi, 40 ming tushlik»</i> (Ko'p xarajat)\n"
            "• <i>«Akromga 300 ming qarz berdim»</i> (Qarz daftari)\n"
            "• <i>«Ovqatga 2 mln limit»</i> (Byudjet rejasi)\n"
            "• <i>«1.5 mln oylik tushdi»</i> (Daromad)\n\n"
            "Yoki quyidagi menyu tugmalaridan foydalaning! 👇"
        )
