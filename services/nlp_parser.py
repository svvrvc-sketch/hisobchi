import re
import json
import logging
from typing import Optional, Dict, Any
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    "🍔 Oziq-ovqat": [
        "tushlik", "nonushta", "kechki ovqat", "ovqat", "osh", "lavash", "somsa", "shashlik",
        "kofe", "coffee", "choy", "non", "go'sht", "gosht", "bozorlik", "supermarket",
        "kafe", "cafe", "restoran", "shirinlik", "suv", "cola", "fanta", "muzqaymoq"
    ],
    "🚕 Transport & Yo'l": [
        "taksi", "taxi", "yandex", "benzin", "yo'l", "yol", "yo'lkira", "yolkira",
        "metro", "metropoliten", "avtobus", "marshrutka", "propan", "metan", "moy almashtirish", "zapchast"
    ],
    "🛍 Xaridlar": [
        "kiyim", "shim", "ko'ylak", "koylak", "oyoq kiyim", "poyabzal", "bozor", "korzinka",
        "makro", "havas", "texnika", "telefon", "naushnik", "xarid", "sovg'a", "sovga"
    ],
    "💡 Kommunal & Aloqa": [
        "svet", "elektr", "gaz", "suv", "kommunal", "wifi", "internet", "paynet",
        "uzmobile", "beeline", "ucell", "mobiuz", "ijara", "arenda", "kvartira"
    ],
    "💊 Sog'liq & Sport": [
        "dori", "apteka", "shifokor", "doktor", "klinika", "analiz", "stomatolog", "tish",
        "sport", "zal", "trenirovka", "basseyn"
    ],
    "💰 Daromad": [
        "oylik", "maosh", "avans", "kassa", "daromad", "tushum", "gonorar", "stipendiya",
        "qarz qaytdi", "bonus", "foyda"
    ]
}

def parse_amount(text: str) -> Optional[float]:
    """Matndan summani ajratib olish (masalan: 45 ming, 50k, 100 000, 1.5 mln)"""
    lower = text.lower().replace(",", ".")
    
    mln_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mln|million)", lower)
    if mln_match:
        return float(mln_match.group(1)) * 1_000_000
        
    ming_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ming|k|тыс)", lower)
    if ming_match:
        return float(ming_match.group(1)) * 1_000

    clean_digits = re.search(r"\b(\d{1,3}(?:\s*\d{3})+|\d+)\s*(?:so'?m|som|сум)?\b", lower)
    if clean_digits:
        val_str = clean_digits.group(1).replace(" ", "")
        val = float(val_str)
        if val >= 500 or "so'm" in lower or "som" in lower:
            return val

    return None

def detect_category(text: str) -> str:
    lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", lower) or kw in lower:
                return category
    return "📦 Boshqa"

def is_income_intent(text: str) -> bool:
    lower = text.lower()
    income_signals = ["oylik", "maosh", "avans", "tushdi", "oldim", "daromad", "kassaga", "tushum", "ishlab topdim", "bonus"]
    for sig in income_signals:
        if sig in lower:
            return True
    return False

def detect_payment_method(text: str) -> str:
    lower = text.lower()
    card_signals = ["karta", "kartaga", "kartamga", "kartadan", "click", "payme", "uzcard", "humo", "plastik"]
    for sig in card_signals:
        if sig in lower:
            return "💳 Karta"
    return "💵 Naqd"

async def ai_parse_smart_input(text: str) -> Optional[Dict[str, Any]]:
    """
    Groq AI orqali:
    1. Bir yoki bir nechta xarajat/daromadlarni ajratish (Multi-intent)
    2. Qarz munosabatlarini aniqlash (qarz berdim, qarz oldim, qarz qaytdi)
    3. Oylik byudjet limitlarini aniqlash (masalan: "ovqatga 2 mln limit")
    """
    if not GROQ_API_KEY:
        return None

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=GROQ_API_KEY)

        prompt = f"""Sen shaxsiy moliya buxgalter AI yordamchisisan. Foydalanuvchi ovozli yoki matnli xabar yubordi:
Xabar: "{text}"

Vazifang - ushbu xabarni chuqur tahlil qilib, 3 turdagi holatdan biriga ajratish:

A HOLAT: MOLIYA TRANZAKSIYALARI (bitta yoki BIR NECHTA xarajat/daromad):
Agar xabarda 1 ta yoki BIR NECHTA xarajat yoki daromad tilga olingan bo'lsa (masalan: «40 ming tushlik, 20 ming taksi, kartadan 100 ming dori»):
Har bir amalni alohida obyekt qilib items massivida qaytar:
- trans_type: "expense" yoki "income"
- amount: so'mda aniq son (masalan: 40 ming -> 40000, 1.5 mln -> 1500000)
- payment_method: agar "karta", "kartadan", "click", "payme", "plastik" qatnashsa "💳 Karta", aks holda "💵 Naqd"
- category: "🍔 Oziq-ovqat", "🚕 Transport & Yo'l", "🛍 Xaridlar", "💡 Kommunal & Aloqa", "💊 Sog'liq & Sport", "💼 Oylik", "🚀 Qo'shimcha daromad", "💰 Kassa", "📦 Boshqa".
- description: aynan nima sabab/xarid ekanligi (masalan: "Tushlik", "Taksi xizmati", "Dorixona dori")

Format:
{{
  "type": "finance",
  "items": [
    {{
      "trans_type": "expense",
      "amount": 40000,
      "payment_method": "💵 Naqd",
      "category": "🍔 Oziq-ovqat",
      "description": "Tushlik"
    }},
    {{
      "trans_type": "expense",
      "amount": 20000,
      "payment_method": "💵 Naqd",
      "category": "🚕 Transport & Yo'l",
      "description": "Taksi yo'lkira"
    }}
  ]
}}

B HOLAT: QARZ DAFTARI (qarz berish, qarz olish yoki qarzni qaytarish):
- Agar kimgadir qarz berilgan bo'lsa (masalan: «Akromga 300 ming qarz berdim»):
  action: "add", debt_type: "given", person_name: "Akrom", amount: 300000, description: "qarz berildi"
- Agar birovdan qarz olingan bo'lsa (masalan: «Sardordan 500 ming qarz oldim»):
  action: "add", debt_type: "taken", person_name: "Sardor", amount: 500000, description: "qarz olindi"
- Agar qarz qaytarilgan/yopilgan bo'lsa (masalan: «Akrom 300 ming qarzini qaytardi» yoki «Akrom qarzini berdi»):
  action: "pay", person_name: "Akrom", amount: 300000

Format:
{{
  "type": "debt",
  "action": "add" yoki "pay",
  "person_name": "Akrom",
  "debt_type": "given" yoki "taken",
  "amount": 300000,
  "description": "qarz berildi"
}}

C HOLAT: OYLIK BYUDJET LIMITI O'RNATISH:
Agar foydalanuvchi ma'lum bir toifaga yoki umumiy oylik limit qo'ymoqchi bo'lsa (masalan: «Oziq-ovqatga 2 mln limit», «Umumiy oylik xarajatimga 6 mln limit»):
Format:
{{
  "type": "budget",
  "category": "🍔 Oziq-ovqat" (yoki "Umumiy"),
  "monthly_limit": 2000000
}}

Agar xabarda bularning hech biri bo'lmasa:
{{
  "type": "unknown"
}}

Faqat to'g'ri JSON formatda javob ber:"""

        resp = await client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        content = resp.choices[0].message.content
        data = json.loads(content)

        msg_type = data.get("type")

        # 1. Finance (single or multi items)
        if msg_type == "finance":
            items = data.get("items", [])
            # Agar bitta obyekt ko'rinishida qaytgan bo'lsa
            if not items and data.get("amount"):
                items = [data]

            valid_items = []
            for it in items:
                amt = it.get("amount")
                if amt and float(amt) > 0:
                    desc = it.get("description", "").strip()
                    if not desc or desc.lower() in ["tavsif", "qisqa tavsif"]:
                        desc = it.get("category", "Xarajat")
                    valid_items.append({
                        "trans_type": it.get("trans_type", "expense"),
                        "amount": float(amt),
                        "category": it.get("category", "📦 Boshqa"),
                        "payment_method": it.get("payment_method", detect_payment_method(text)),
                        "description": desc
                    })

            if valid_items:
                return {
                    "type": "finance",
                    "items": valid_items
                }

        # 2. Debt
        elif msg_type == "debt" and data.get("person_name"):
            return {
                "type": "debt",
                "action": data.get("action", "add"),
                "person_name": data.get("person_name", "Noma'lum").strip(),
                "debt_type": data.get("debt_type", "given"),
                "amount": float(data.get("amount", 0)),
                "description": data.get("description", "Qarz amali")
            }

        # 3. Budget
        elif msg_type == "budget" and data.get("monthly_limit"):
            return {
                "type": "budget",
                "category": data.get("category", "Umumiy"),
                "monthly_limit": float(data.get("monthly_limit"))
            }

    except Exception as e:
        logger.warning(f"AI tahlilda xatolik (fallback ishga tushadi): {e}")

    return None

async def parse_smart_input(text: str) -> Dict[str, Any]:
    ai_result = await ai_parse_smart_input(text)
    if ai_result:
        return ai_result

    amount = parse_amount(text)
    if amount and amount > 0:
        is_income = is_income_intent(text)
        category = "💰 Daromad" if is_income else detect_category(text)
        pay_method = detect_payment_method(text)
        
        # Izohni tozalash
        clean_desc = re.sub(r"(\d+(?:\.\d+)?)\s*(?:ming|k|mln|million|so'?m|som|тыс)?", "", text, flags=re.IGNORECASE)
        clean_desc = re.sub(r"\b(kartadan|kartaga|kartamga|naqd|berdim|oldim|ketdi|to'ladim|toladim|tushdi)\b", "", clean_desc, flags=re.IGNORECASE)
        clean_desc = clean_desc.strip(" ,.-")
        if not clean_desc:
            clean_desc = text.strip()
        else:
            clean_desc = clean_desc[0].upper() + clean_desc[1:]

        return {
            "type": "finance",
            "items": [
                {
                    "trans_type": "income" if is_income else "expense",
                    "amount": amount,
                    "category": category,
                    "payment_method": pay_method,
                    "description": clean_desc
                }
            ]
        }

    return {
        "type": "unknown",
        "data": {"raw": text}
    }
