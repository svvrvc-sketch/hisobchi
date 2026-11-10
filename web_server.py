import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional, List
import aiosqlite
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import DB_PATH
from database.db import (
    init_db,
    add_transaction,
    get_summary,
    delete_transaction,
    get_all_transactions,
    add_debt,
    get_active_debts,
    mark_debt_paid,
    set_budget,
    get_budgets,
    check_budget_alerts
)
from services.receipt_parser import parse_receipt_image
from services.nlp_parser import parse_smart_input
from services.ai_advisor import generate_financial_advice
from services.excel_exporter import generate_excel_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hisobchi AI - Web Dashboard API", version="2.0.0")

@app.on_event("startup")
async def _startup_init_db():
    """Baza jadvallari mavjud bo'lmasa yaratadi va botni fonda ishga tushiradi."""
    await init_db()
    if os.getenv("RUN_BOT", "1") == "1":
        import asyncio
        from bot import main as run_bot
        asyncio.create_task(run_bot())
        logger.info("Telegram Bot fonda ishga tushirildi.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_str(s: Optional[str]) -> str:
    if not s:
        return ""
    import re
    return re.sub(r'[\U00010000-\U0010ffff\u2600-\u27ff]', '', s).strip()

# Pydantic Schemas
class TransactionCreate(BaseModel):
    user_id: int
    trans_type: str  # 'expense' or 'income'
    amount: float
    category: str
    description: Optional[str] = ""
    payment_method: Optional[str] = "Naqd"

class DebtCreate(BaseModel):
    user_id: int
    person_name: str
    debt_type: str  # 'given' or 'taken'
    amount: float
    description: Optional[str] = ""

class BudgetCreate(BaseModel):
    user_id: int
    category: str
    monthly_limit: float

class AIAdviceRequest(BaseModel):
    user_id: int
    query_type: str = "summary"
    query_text: str = ""

class SmartInputRequest(BaseModel):
    user_id: int
    text: str
    auto_save: Optional[bool] = False

# API Routes
@app.get("/api/users")
async def get_users():
    """Barcha ro'yxatdan o'tgan foydalanuvchilar ro'yxati"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT user_id, full_name, username FROM users ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []

@app.get("/api/summary")
async def api_summary(user_id: int = Query(...), period: str = Query("month")):
    """Moliya balansi, naqd/karta taqsimoti va toifalar statistikasi"""
    try:
        summary = await get_summary(user_id, period)
        return summary
    except Exception as e:
        logger.error(f"Error in api_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions")
async def api_transactions(user_id: int = Query(...), period: str = Query("all"), limit: int = Query(50)):
    """Tranzaksiyalar ro'yxati"""
    try:
        items = await get_all_transactions(user_id, period)
        # Sort desc
        items = sorted(items, key=lambda x: x["created_at"], reverse=True)
        return items[:limit]
    except Exception as e:
        logger.error(f"Error in api_transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transactions")
async def api_add_transaction(data: TransactionCreate):
    """Yangi xarajat yoki daromad qo'shish"""
    try:
        cat = clean_str(data.category) or ("Oziq-ovqat" if data.trans_type == "expense" else "Maosh")
        pay_m = clean_str(data.payment_method) or "Naqd"
        tx_id = await add_transaction(
            user_id=data.user_id,
            trans_type=data.trans_type,
            amount=data.amount,
            category=cat,
            description=clean_str(data.description),
            payment_method=pay_m
        )
        alerts = []
        if data.trans_type == "expense":
            alerts = await check_budget_alerts(data.user_id, cat, data.amount)
        return {"success": True, "id": tx_id, "alerts": alerts}
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions/{tx_id}")
async def api_delete_transaction(tx_id: int, user_id: int = Query(...)):
    """Tranzaksiyani o'chirish"""
    try:
        ok = await delete_transaction(tx_id, user_id)
        return {"success": ok}
    except Exception as e:
        logger.error(f"Error deleting transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debts")
async def api_debts(user_id: int = Query(...)):
    """Qarzlar ro'yxati (haqqim bor / qarzdorman)"""
    try:
        debts = await get_active_debts(user_id)
        return debts
    except Exception as e:
        logger.error(f"Error fetching debts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/debts")
async def api_add_debt(data: DebtCreate):
    """Yangi qarz yozish"""
    try:
        debt_id = await add_debt(
            user_id=data.user_id,
            person_name=data.person_name,
            debt_type=data.debt_type,
            amount=data.amount,
            description=data.description or ""
        )
        return {"success": True, "id": debt_id}
    except Exception as e:
        logger.error(f"Error adding debt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/debts/{debt_id}/pay")
async def api_pay_debt(debt_id: int, user_id: int = Query(...)):
    """Qarzni to'langan deb belgilash"""
    try:
        ok = await mark_debt_paid(debt_id, user_id)
        return {"success": ok}
    except Exception as e:
        logger.error(f"Error marking debt paid: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/budgets")
async def api_budgets(user_id: int = Query(...)):
    """Oylik limitlar va ularning joriy oyda sarflangan holati"""
    try:
        budgets = await get_budgets(user_id)
        # Shu oylik xarajatlarni toifalar bo'yicha hisoblaymiz
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT category, COALESCE(SUM(amount), 0) as spent
                FROM transactions
                WHERE user_id = ? AND type = 'expense'
                  AND strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')
                GROUP BY category
            """, (user_id,))
            cat_rows = await cursor.fetchall()
            cat_map = {r["category"]: r["spent"] for r in cat_rows}
            total_spent = sum(cat_map.values())

        result = []
        for b in budgets:
            cat = b["category"]
            limit = b["monthly_limit"]
            spent = total_spent if cat.lower() in ["umumiy", "jami"] else cat_map.get(cat, 0)
            pct = round((spent / limit) * 100, 1) if limit > 0 else 0
            result.append({
                "category": cat,
                "monthly_limit": limit,
                "spent": spent,
                "remaining": max(0, limit - spent),
                "percent": pct
            })
        return result
    except Exception as e:
        logger.error(f"Error in api_budgets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/budgets")
async def api_set_budget(data: BudgetCreate):
    """Byudjet limitini belgilash yoki yangilash"""
    try:
        await set_budget(data.user_id, data.category, data.monthly_limit)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error setting budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/advice")
async def api_ai_advice(data: AIAdviceRequest):
    """Groq AI orqali shaxsiy moliya tahlili va maslahat olish"""
    try:
        advice = await generate_financial_advice(
            data.user_id, 
            query_type=data.query_type, 
            query_text=data.query_text
        )
        return {"advice": advice}
    except Exception as e:
        logger.error(f"Error generating AI advice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/receipts/scan")
async def api_scan_receipt(
    user_id: int = Form(...),
    auto_save: bool = Form(True),
    file: UploadFile = File(...)
):
    """Vision AI yordamida chek rasmini o'qish va avtomatik xarajat qo'shish"""
    suffix = Path(file.filename or "receipt.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(file.file, tmp)

    try:
        parsed = await parse_receipt_image(tmp_path)
        if not parsed or not parsed.get("success"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Chekdagi ma'lumotlarni o'qib bo'lmadi."}
            )

        saved_tx = None
        alerts = []
        if auto_save:
            c_name = clean_str(parsed.get("category")) or "Oziq-ovqat"
            p_method = clean_str(parsed.get("payment_method")) or "Karta"
            c_desc = clean_str(parsed.get("description")) or f"Chek: {clean_str(parsed.get('store_name')) or 'Dokon'}"
            tx_id = await add_transaction(
                user_id=user_id,
                trans_type="expense",
                amount=parsed["total_amount"],
                category=c_name,
                description=c_desc,
                payment_method=p_method
            )
            alerts = await check_budget_alerts(user_id, c_name, parsed["total_amount"])
            saved_tx = {"id": tx_id}

        return {
            "success": True,
            "data": parsed,
            "saved": saved_tx,
            "alerts": alerts
        }
    finally:
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except Exception:
                pass

@app.post("/api/ai/parse-text")
async def api_parse_text(data: SmartInputRequest):
    """Aqlli matn tahlili (NLP / Groq AI)"""
    try:
        res = await parse_smart_input(data.text)
        saved_items = []
        alerts = []

        if data.auto_save and res.get("type") == "finance":
            for it in res.get("items", []):
                tx_id = await add_transaction(
                    user_id=data.user_id,
                    trans_type=it["trans_type"],
                    amount=it["amount"],
                    category=it["category"],
                    description=it.get("description", ""),
                    payment_method=it.get("payment_method", "💵 Naqd")
                )
                if it["trans_type"] == "expense":
                    al = await check_budget_alerts(data.user_id, it["category"], it["amount"])
                    alerts.extend(al)
                saved_items.append({"id": tx_id, **it})

        elif data.auto_save and res.get("type") == "debt":
            d_id = await add_debt(
                user_id=data.user_id,
                person_name=res["person_name"],
                debt_type=res["debt_type"],
                amount=res["amount"],
                description=res.get("description", "")
            )
            saved_items.append({"id": d_id, **res})

        elif data.auto_save and res.get("type") == "budget":
            await set_budget(data.user_id, res["category"], res["monthly_limit"])
            saved_items.append(res)

        return {
            "success": True,
            "parsed": res,
            "saved_items": saved_items,
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Error in smart text parse: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/excel/download")
async def api_download_excel(user_id: int = Query(...), period: str = Query("month")):
    """Excel (.xlsx) hisobotini yuklab olish"""
    try:
        transactions = await get_all_transactions(user_id, period)
        user_name = "Foydalanuvchi"
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row and row["full_name"]:
                user_name = row["full_name"]

        period_names = {
            "today": "Bugungi kun",
            "week": "So'nggi 7 kun",
            "month": "Shu oy",
            "all": "Barcha davr"
        }
        period_str = period_names.get(period, "Barcha davr")
        xlsx_path = generate_excel_report(transactions, user_name, period_str)

        filename = f"moliya_hisoboti_{period}.xlsx"
        return FileResponse(
            xlsx_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Error generating excel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ping")
async def ping():
    return {"status": "ok", "app": "Hisobchi AI", "bot": "active"}

# Mount static web app
WEBAPP_DIR = Path(__file__).parent / "webapp"
WEBAPP_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="webapp")
