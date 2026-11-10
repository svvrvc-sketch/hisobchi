import logging
from config import GROQ_API_KEY
from database.db import get_summary, get_active_debts, get_budgets

logger = logging.getLogger(__name__)

def format_number(val: float) -> str:
    return f"{int(val):,}".replace(",", " ")

# Query type to prompt mapping
QUERY_PROMPTS = {
    "summary": "Shu oylik moliyaviy holatining qisqa xulosasini tayyorla. 3-4 ta asosiy nuqtani bullet formatda ber.",
    "biggest": "Eng katta xarajat toifalarini ko'rsat va tahlil qil. Qaysi toifaga eng ko'p pul sarflangani haqida ber.",
    "saving": "Tejash imkoniyatlari haqida maslahat ber. Qaysi toifalarda xarajatni qisqartirish mumkin?",
    "forecast": "Oy oxirigacha qancha pul qolishi mumkinligini prognoz qil. Kunlik tavsiya etilgan xarajat me'yorini hisoblaydi.",
}

async def generate_financial_advice(user_id: int, query_type: str = "summary", query_text: str = "") -> str:
    """
    Foydalanuvchining oylik moliya ko'rsatkichlarini tahlil qilib,
    Groq AI orqali shaxsiy moliyaviy maslahat va tahliliy hisobot yaratadi.
    Chat interfeysi uchun turli savollarga javob beradi.
    """
    summary = await get_summary(user_id, period="month")
    debts = await get_active_debts(user_id)
    budgets = await get_budgets(user_id)

    income = summary["income"]
    expense = summary["expense"]
    balance = summary["balance"]
    categories = summary["categories"]

    if income == 0 and expense == 0:
        return (
            "Shu oy xulosasi\n"
            "- Hozircha tahlil qilish uchun ma'lumotlar yetarli emas: "
            "Bir nechta daromad va xarajatlaringizni kiriting.\n"
            "- Maslahat: Kundalik xarajatlaringizni yozib borishni boshlang, "
            "men sizga shaxsiy tavsiyalar tayyorlab beraman."
        )

    categories_text = ", ".join([f"{c['category']}: {format_number(c['sum_amount'])} so'm" for c in categories]) if categories else "Mavjud emas"
    debts_text = f"Siz olishingiz kerak: {format_number(debts['total_given'])} so'm, Siz berishingiz kerak: {format_number(debts['total_taken'])} so'm"

    # Determine specific prompt based on query type
    if query_type == "custom" and query_text:
        specific_instruction = f"Foydalanuvchi quyidagi savolni berdi: \"{query_text}\"\nShu savolga javob ber."
    else:
        specific_instruction = QUERY_PROMPTS.get(query_type, QUERY_PROMPTS["summary"])

    if not GROQ_API_KEY:
        # Fallback without AI
        if query_type == "biggest":
            if categories:
                sorted_cats = sorted(categories, key=lambda x: x['sum_amount'], reverse=True)
                lines = ["Eng katta xarajatlar"]
                for cat in sorted_cats[:5]:
                    pct = round((cat['sum_amount'] / expense) * 100) if expense > 0 else 0
                    lines.append(f"- {cat['category']}: {format_number(cat['sum_amount'])} so'm ({pct}% ulush)")
                return "\n".join(lines)
            return "Eng katta xarajatlar\n- Hozircha xarajatlar mavjud emas."

        elif query_type == "saving":
            return (
                "Tejash maslahati\n"
                f"- Oylik xarajatingiz: {format_number(expense)} so'm. "
                f"Daromadingizning 10-15% qismini jamg'armaga ajrating.\n"
                "- Maslahat: Eng katta xarajat toifangizni aniqlang va shu toifada "
                "10% tejashga harakat qiling.\n"
                "- Qarz holatingiz: " + debts_text
            )

        elif query_type == "forecast":
            import datetime
            today = datetime.date.today()
            days_left = (datetime.date(today.year, today.month + 1 if today.month < 12 else 1, 1) - today).days
            daily_budget = (income - expense) / days_left if days_left > 0 else 0
            return (
                "Oylik prognoz\n"
                f"- Oy oxirigacha {days_left} kun qoldi.\n"
                f"- Hozirgi balans: {format_number(balance)} so'm.\n"
                f"- Kunlik tavsiya etilgan xarajat: {format_number(max(0, daily_budget))} so'm."
            )

        # Default summary
        return (
            "Shu oy xulosasi\n"
            f"- Daromad: {format_number(income)} so'm | Xarajat: {format_number(expense)} so'm\n"
            f"- Balans: {format_number(balance)} so'm\n"
            f"- Maslahat: Xarajatlaringizni nazorat qilib boring va har oy daromadingizning "
            f"10-15% qismini jamg'armaga ajrating."
        )

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=GROQ_API_KEY)

        prompt = f"""Sen shaxsiy moliya buxgalteri va AI moliyaviy maslahatchisisan.
Foydalanuvchining shu oylik ko'rsatkichlari:
- Oylik daromad: {income} so'm
- Oylik xarajat: {expense} so'm
- Hozirgi sof balans: {balance} so'm
- Xarajatlar toifalari: {categories_text}
- Qarz holati: {debts_text}

{specific_instruction}

Javobni quyidagi formatda ber:
1. Birinchi qator — qisqa sarlavha (masalan: "Shu oy xulosasi")
2. Keyin har bir muhim nuqtani "- Sarlavha: Tushuntirish" formatida bullet qilib yoz
3. 3-5 ta asosiy nuqtani ber, ortiqcha uzun yozma
4. Faqat o'zbek tilida yoz
5. Hech qanday emoji ishlatma
6. HTML teglar ishlatma, faqat oddiy matn"""

        resp = await client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        advice_text = resp.choices[0].message.content.strip()
        # Clean HTML tags
        import re
        advice_text = re.sub(r'<[^>]+>', '', advice_text)
        return advice_text

    except Exception as e:
        logger.error(f"AI Maslahatchi xatosi: {e}")
        return (
            "Shu oy xulosasi\n"
            f"- Daromad: {format_number(income)} so'm | Xarajat: {format_number(expense)} so'm\n"
            f"- Balans: {format_number(balance)} so'm\n"
            f"- Maslahat: Hozirgi asosiy xarajatingiz toifalari bo'yicha tejashni rejalashtiring "
            f"va oylik limitlarga amal qiling."
        )
