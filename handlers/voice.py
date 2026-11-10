import os
import logging
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from config import VOICE_TEMP_DIR
from services.stt import transcribe_voice
from services.nlp_parser import parse_smart_input
from database.db import add_transaction, add_debt, close_debt_by_name, set_budget, check_budget_alerts
from handlers.finance import format_number

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.voice | F.audio)
async def handle_voice_message(message: Message, bot: Bot, state: FSMContext):
    await state.clear()  # Har qanday eski holatni tozalash
    user_id = message.from_user.id
    logger.info(f"🎙 [VOICE] Foydalanuvchi {user_id} dan ovozli xabar keldi!")
    status_msg = await message.answer("🎙 <i>Ovozingiz tinglanmoqda va tahlil qilinmoqda...</i>", parse_mode="HTML")
    
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    temp_file = VOICE_TEMP_DIR / f"{user_id}_{message.message_id}.ogg"
    
    try:
        # Faylni yuklab olish
        await bot.download(file_id, destination=temp_file)
        
        # Ovozni matnga o'girish (STT)
        text = await transcribe_voice(temp_file)
        logger.info(f"🎙 [VOICE MATN]: '{text}'")
        
        if not text:
            await status_msg.edit_text("⚠️ Ovozingizni aniqlab bo'lmadi. Iltimos qaytadan aniqroq gapirib ko'ring.")
            return

        # Matnni aqlli tahlil qilish (AI yordamida moliya ma'lumotlarini ajratib oladi)
        parsed = await parse_smart_input(text)
        action_type = parsed["type"]
        logger.info(f"🎯 [ACTION]: turi={action_type}")
        
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
                    f"🎙 <b>Eshitdim:</b> <i>«{text}»</i>\n\n"
                    f"✅ <b>{title}!</b>\n\n"
                    f"💵 <b>Summa:</b> {sign}{format_number(amount)} so'm\n"
                    f"💳 <b>Hisob turi:</b> {pay_method}\n"
                    f"📁 <b>Toifa:</b> {category}\n"
                    f"📝 <b>Izoh:</b> {desc}"
                )
                if all_alerts:
                    reply_text += "\n\n" + "\n\n".join(all_alerts)

                await status_msg.edit_text(reply_text, parse_mode="HTML")

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
                    f"🎙 <b>Eshitdim:</b> <i>«{text}»</i>\n\n"
                    f"✅ <b>{len(items)} ta amal muvaffaqiyatli saqlandi!</b>\n\n"
                    + "\n".join(lines) + "\n\n"
                    f"📊 <b>Jami o'zgarish:</b> {sign_tot}{format_number(abs(total_sum))} so'm"
                )
                if all_alerts:
                    reply_text += "\n\n" + "\n\n".join(all_alerts)

                await status_msg.edit_text(reply_text, parse_mode="HTML")

        elif action_type == "debt":
            action = parsed.get("action", "add")
            person = parsed.get("person_name", "Noma'lum")
            amt = parsed.get("amount", 0)

            if action == "pay":
                closed = await close_debt_by_name(user_id, person)
                if closed:
                    await status_msg.edit_text(
                        f"🎙 <b>Eshitdim:</b> <i>«{text}»</i>\n\n"
                        f"🤝 <b>Qarz yopildi!</b>\n\n"
                        f"👤 Shaxs: <b>{closed['person_name']}</b>\n"
                        f"💵 Summa: <b>{format_number(closed['amount'])} so'm</b>\n\n"
                        f"✅ <i>Qarz daftarchasida to'langan deb belgilandi.</i>",
                        parse_mode="HTML"
                    )
                else:
                    await status_msg.edit_text(
                        f"🎙 <b>Eshitdim:</b> <i>«{text}»</i>\n\n"
                        f"ℹ️ <b>{person}</b> bo'yicha faol qarz yozuvi topilmadi.",
                        parse_mode="HTML"
                    )
            else:
                debt_type = parsed.get("debt_type", "given")
                desc = parsed.get("description", "Qarz")
                await add_debt(user_id, person, debt_type, amt, desc)
                type_label = "🟢 Qarz berildi (Sizga qaytarishi kerak)" if debt_type == "given" else "🔴 Qarz olindi (Siz qaytarishingiz kerak)"

                await status_msg.edit_text(
                    f"🎙 <b>Eshitdim:</b> <i>«{text}»</i>\n\n"
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

            await status_msg.edit_text(
                f"🎙 <b>Eshitdim:</b> <i>«{text}»</i>\n\n"
                f"🎯 <b>Oylik byudjet o'rnatildi!</b>\n\n"
                f"📁 Toifa: <b>{cat}</b>\n"
                f"💰 Oylik limit: <b>{format_number(lim)} so'm</b>\n\n"
                f"ℹ️ <i>Xarajatlaringiz 80% va 100% ga yetganda sizni ogohlantirib boraman.</i>",
                parse_mode="HTML"
            )

        else:
            reply_text = (
                f"🎙 <b>Eshitdim:</b> <i>«{text}»</i>\n\n"
                f"🤔 Bu xabardan aniq moliyaviy ma'lumot topa olmadim.\n\n"
                f"💡 <b>Namunalar:</b>\n"
                f"• <i>«35 ming tushlik, 20 ming taksi»</i> (Bir nechta xarajat)\n"
                f"• <i>«Akromga 200 ming qarz berdim»</i> (Qarz daftari)\n"
                f"• <i>«Oziq-ovqatga 2 mln limit»</i> (Oylik byudjet)\n"
                f"• <i>«Kassaga 500 ming tushdi»</i>"
            )
            await status_msg.edit_text(reply_text, parse_mode="HTML")

    except ValueError as ve:
        await status_msg.edit_text(
            f"ℹ️ <b>Ovozli xizmatni sozlash zarur:</b>\n\n{str(ve)}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ovozli xabarni qayta ishlashda xatolik: {e}")
        await status_msg.edit_text(
            f"⚠️ Ovozni qayta ishlashda xatolik yuz berdi: {e}\n"
            f"Iltimos, qayta urinib ko'ring yoki xabarni matn ko'rinishida yozing."
        )
    finally:
        if temp_file.exists():
            try:
                os.remove(temp_file)
            except Exception:
                pass
