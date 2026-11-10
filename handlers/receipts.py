import os
import logging
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message
from config import VOICE_TEMP_DIR
from services.receipt_parser import parse_receipt_image
from database.db import add_transaction, check_budget_alerts
from handlers.finance import format_number

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.photo)
async def handle_receipt_photo(message: Message, bot: Bot):
    user_id = message.from_user.id
    logger.info(f"📸 [PHOTO]: Foydalanuvchi {user_id} dan chek rasmi keldi!")

    status_msg = await message.answer("🧾 <i>Chek o'rganilmoqda va tahlil qilinmoqda (Vision AI)...</i>", parse_mode="HTML")

    # Eng yuqori sifatli rasmni olish
    photo = message.photo[-1]
    temp_file = VOICE_TEMP_DIR / f"receipt_{user_id}_{message.message_id}.jpg"

    try:
        await bot.download(photo.file_id, destination=temp_file)
        
        # Vision AI orqali tahlil
        result = await parse_receipt_image(temp_file)

        if result and result.get("success"):
            store_name = result["store_name"]
            total_amount = result["total_amount"]
            pay_method = result["payment_method"]
            category = result["category"]
            items_summary = result["items_summary"]
            description = result["description"]

            # Bazaga xarajat sifatida kiritish
            await add_transaction(
                user_id=user_id,
                trans_type="expense",
                amount=total_amount,
                category=category,
                description=description,
                payment_method=pay_method
            )

            # Byudjet limitini tekshirish
            alerts = await check_budget_alerts(user_id, category, total_amount)

            reply_text = (
                f"🧾 <b>Chek muvaffaqiyatli o'qildi va saqlandi!</b>\n\n"
                f"🏪 <b>Joy / Do'kon:</b> {store_name}\n"
                f"💵 <b>Jami summa:</b> -{format_number(total_amount)} so'm\n"
                f"💳 <b>Hisob turi:</b> {pay_method}\n"
                f"📁 <b>Toifa:</b> {category}\n"
            )
            if items_summary:
                reply_text += f"🛍 <b>Asosiy mahsulotlar:</b> <i>{items_summary}</i>\n"

            if alerts:
                reply_text += "\n" + "\n\n".join(alerts)

            await status_msg.edit_text(reply_text, parse_mode="HTML")

        else:
            err = result.get("error") if result else "Chek ma'lumotlarini aniqlab bo'lmadi"
            await status_msg.edit_text(
                f"🤔 <b>Rasm tahlili natijasi:</b>\n\n"
                f"<i>{err}</i>\n\n"
                f"💡 <b>Maslahat:</b> Chek aniq, to'g'ri yorug'likda va umumiy summasi yaqqol ko'rinadigan qilib olinganiga ishonch hosil qiling.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Chekni qayta ishlashda xatolik: {e}")
        await status_msg.edit_text(f"⚠️ Chekni tahlil qilishda xatolik yuz berdi: {e}")
    finally:
        if temp_file.exists():
            try:
                os.remove(temp_file)
            except Exception:
                pass
