import base64
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

async def parse_receipt_image(image_path: Path) -> Optional[Dict[str, Any]]:
    """
    Groq Vision AI (qwen/qwen3.8-27b) orqali chek rasmini tahlil qilish va
    xarajat parametrlarini avtomatik ajratib olish.
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY mavjud emas")
        return None

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=GROQ_API_KEY)

        with open(image_path, "rb") as f:
            image_bytes = f.read()
            b64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """Sen chek va kvitansiyalarni o'quvchi professional AI buxgaltersan.
Taqdim etilgan rasmda do'kon, supermarket (Korzinka, Makro, Havas), kafe, dorixona yoki zapravka cheki aks etgan.

Chekni sinchkovlik bilan tahlil qilib, quyidagi ma'lumotlarni JSON shaklida ajrat:
1. store_name: Do'kon, savdo markazi yoki kafe nomi (masalan: "Korzinka", "Havas", "Apteka", "EVOS"). Agar nomi yo'q bo'lsa "Kassa cheki".
2. total_amount: Chek bo'yicha YAKUNIY to'langan jami summa (so'mda, son ko'rinishida, masalan: 125000).
3. payment_method: "💳 Karta" (agar terminal, Humo, Uzcard, karta orqali bo'lsa) yoki "💵 Naqd".
4. category: Eng mos toifani tanla:
   - "🍔 Oziq-ovqat" (supermarket, oziq-ovqat, kafe, restoran)
   - "🚕 Transport & Yo'l" (yoqilg'i, zapravka, avto)
   - "🛍 Xaridlar" (kiyim, poyabzal, maishiy texnika)
   - "💡 Kommunal & Aloqa" (kommunal kvitansiya)
   - "💊 Sog'liq & Sport" (dorixona, klinika)
   - "📦 Boshqa"
5. items_summary: Chekdagi asosiy 3-5 ta mahsulot nomlari (masalan: "Go'sht, sut, non, suv").
6. description: Qisqa ixcham izoh (masalan: "Korzinka: oziq-ovqat xaridlari").

Faqat va faqat quyidagi JSON formatda javob ber:
{
  "success": true,
  "store_name": "Korzinka",
  "total_amount": 145000,
  "payment_method": "💳 Karta",
  "category": "🍔 Oziq-ovqat",
  "items_summary": "Sut, non, pishloq",
  "description": "Korzinka: oziq-ovqat xaridi"
}

Agar bu rasmda moliyaviy chek yoki summa aniqlanmasa:
{
  "success": false,
  "error": "Chekdagi ma'lumotlarni o'qib bo'lmadi"
}
"""

        response = await client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        if data.get("success") and data.get("total_amount") and float(data.get("total_amount")) > 0:
            return {
                "success": True,
                "store_name": data.get("store_name", "Kassa cheki"),
                "total_amount": float(data.get("total_amount")),
                "payment_method": data.get("payment_method", "💳 Karta"),
                "category": data.get("category", "🍔 Oziq-ovqat"),
                "items_summary": data.get("items_summary", ""),
                "description": data.get("description", f"{data.get('store_name', 'Chek')} xarajatlari")
            }
        else:
            return {
                "success": False,
                "error": data.get("error", "Chek ma'lumotlarini aniqlab bo'lmadi")
            }

    except Exception as e:
        logger.error(f"Vision AI tahlilida xatolik: {e}")
        return {
            "success": False,
            "error": str(e)
        }
