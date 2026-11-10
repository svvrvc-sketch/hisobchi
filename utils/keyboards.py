from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from config import WEBAPP_URL

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Hisobchi AI asosiy menyu klaviaturasi (Web App tugmasi bilan)"""
    kb = [
        [
            KeyboardButton(text="📱 Ilovani ochish", web_app=WebAppInfo(url=WEBAPP_URL))
        ],
        [
            KeyboardButton(text="➕ Xarajat qo'shish"),
            KeyboardButton(text="💰 Daromad qo'shish")
        ],
        [
            KeyboardButton(text="📊 Hisobot & Statistika"),
            KeyboardButton(text="❓ Yordam")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def webapp_inline_keyboard(user_id: int = 0) -> InlineKeyboardMarkup:
    """Telegram Mini App ochish inline tugmasi"""
    url = f"{WEBAPP_URL}?user_id={user_id}" if user_id else WEBAPP_URL
    kb = [
        [
            InlineKeyboardButton(text="📱 Ilovani ochish (Web App)", web_app=WebAppInfo(url=url))
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_method_keyboard(trans_type: str = "income") -> InlineKeyboardMarkup:
    """To'lov usulini tanlash (Naqd yoki Karta)"""
    kb = [
        [
            InlineKeyboardButton(text="💵 Naqd pul", callback_data=f"pay_naqd_{trans_type}"),
            InlineKeyboardButton(text="💳 Plastik karta", callback_data=f"pay_karta_{trans_type}")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def income_categories_keyboard() -> InlineKeyboardMarkup:
    """Daromad toifalarini tanlash klaviaturasi"""
    kb = [
        [
            InlineKeyboardButton(text="💼 Oylik / Maosh", callback_data="inc_cat_💼 Oylik"),
            InlineKeyboardButton(text="🚀 Qo'shimcha daromad", callback_data="inc_cat_🚀 Qo'shimcha daromad")
        ],
        [
            InlineKeyboardButton(text="💰 Kassa / Savdo", callback_data="inc_cat_💰 Kassa"),
            InlineKeyboardButton(text="🎁 Sovg'a / Bonus", callback_data="inc_cat_🎁 Sovg'a")
        ],
        [
            InlineKeyboardButton(text="✏️ Boshqa (o'zingiz yozing)", callback_data="inc_cat_custom")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def period_inline_keyboard() -> InlineKeyboardMarkup:
    """Moliya hisoboti davrini tanlash va aqlli xizmatlar"""
    kb = [
        [
            InlineKeyboardButton(text="📅 Bugun", callback_data="report_period_today"),
            InlineKeyboardButton(text="🗓 Shu hafta", callback_data="report_period_week")
        ],
        [
            InlineKeyboardButton(text="📆 Shu oy", callback_data="report_period_month"),
            InlineKeyboardButton(text="📈 Umumiy", callback_data="report_period_all")
        ],
        [
            InlineKeyboardButton(text="🧠 AI Maslahatchi", callback_data="ai_advisor"),
            InlineKeyboardButton(text="🤝 Qarz daftari", callback_data="view_debts")
        ],
        [
            InlineKeyboardButton(text="🎯 Byudjet limitlari", callback_data="view_budgets"),
            InlineKeyboardButton(text="📥 Excelda yuklash", callback_data="export_excel_current")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def debts_inline_keyboard(debts_data: dict) -> InlineKeyboardMarkup:
    """Qarzlar ro'yxati va ularni yopish klaviaturasi"""
    kb = []
    # Faol qarzlarni yopish uchun tugmalar
    all_debts = debts_data.get("given", []) + debts_data.get("taken", [])
    for d in all_debts[:6]:  # eng oxirgi 6 ta
        sign = "🟢" if d["debt_type"] == "given" else "🔴"
        name = d["person_name"]
        amt = f"{int(d['amount']):,}".replace(",", " ")
        btn_text = f"✅ {sign} {name} ({amt}) qaytarildi"
        kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"pay_debt_{d['id']}")])

    kb.append([
        InlineKeyboardButton(text="🔙 Hisobotga qaytish", callback_data="report_period_month")
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def budgets_inline_keyboard() -> InlineKeyboardMarkup:
    """Byudjet bo'limi klaviaturasi"""
    kb = [
        [InlineKeyboardButton(text="➕ Yangi limit o'rnatish", callback_data="set_new_budget")],
        [InlineKeyboardButton(text="🔙 Hisobotga qaytish", callback_data="report_period_month")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_to_report_keyboard() -> InlineKeyboardMarkup:
    """Hisobotga qaytish tugmasi"""
    kb = [
        [InlineKeyboardButton(text="🔙 Hisobotga qaytish", callback_data="report_period_month")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def excel_period_keyboard() -> InlineKeyboardMarkup:
    """Excel yuklab olish uchun davrni tanlash"""
    kb = [
        [
            InlineKeyboardButton(text="📅 Bugungi kun", callback_data="excel_today"),
            InlineKeyboardButton(text="🗓 Shu haftalik", callback_data="excel_week")
        ],
        [
            InlineKeyboardButton(text="📆 Shu oylik", callback_data="excel_month"),
            InlineKeyboardButton(text="📈 Barcha davr (to'liq)", callback_data="excel_all")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def categories_keyboard(trans_type: str = "expense") -> InlineKeyboardMarkup:
    """Xarajat toifalarini tanlash uchun inline tugmalar"""
    kb = [
        [
            InlineKeyboardButton(text="🍔 Oziq-ovqat", callback_data="cat_🍔 Oziq-ovqat"),
            InlineKeyboardButton(text="🚕 Transport & Yo'l", callback_data="cat_🚕 Transport & Yo'l")
        ],
        [
            InlineKeyboardButton(text="🛍 Xaridlar", callback_data="cat_🛍 Xaridlar"),
            InlineKeyboardButton(text="💡 Kommunal & Aloqa", callback_data="cat_💡 Kommunal & Aloqa")
        ],
        [
            InlineKeyboardButton(text="💊 Sog'liq & Sport", callback_data="cat_💊 Sog'liq & Sport"),
            InlineKeyboardButton(text="📦 Boshqa", callback_data="cat_📦 Boshqa")
        ],
        [
            InlineKeyboardButton(text="✏️ Boshqa (o'zingiz yozing)", callback_data="cat_custom")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def cancel_inline_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish tugmasi"""
    kb = [
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def skip_description_keyboard() -> InlineKeyboardMarkup:
    """Izoh kiritishni o'tkazib yuborish klaviaturasi"""
    kb = [
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish (izohsiz)", callback_data="skip_description")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
