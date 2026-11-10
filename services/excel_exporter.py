import tempfile
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generate_excel_report(transactions: list[dict], user_name: str, period_name: str = "Barcha davr") -> str:
    """
    Tranzaksiyalar ro'yxatidan professional dizayndagi Excel (.xlsx) hisobot yaratadi.
    Vaqtinchalik fayl yo'lini qaytaradi.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Moliya Hisoboti"

    ws.views.sheetView[0].showGridLines = True

    PRIMARY_COLOR = "1B365D"  # To'q ko'k
    ACCENT_GREEN = "0E7A46"   # Yashil
    ACCENT_RED = "A82222"     # Qizil
    HEADER_FILL = "2A4365"     # Header foni
    ZEBRA_FILL = "F8FAFC"      # Qatorlar foni

    font_title = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    font_meta = Font(name="Calibri", size=11, bold=True, color="334155")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_regular = Font(name="Calibri", size=11)
    font_income = Font(name="Calibri", size=11, bold=True, color=ACCENT_GREEN)
    font_expense = Font(name="Calibri", size=11, bold=True, color=ACCENT_RED)
    font_total = Font(name="Calibri", size=12, bold=True, color="000000")

    fill_title = PatternFill(start_color=PRIMARY_COLOR, end_color=PRIMARY_COLOR, fill_type="solid")
    fill_header = PatternFill(start_color=HEADER_FILL, end_color=HEADER_FILL, fill_type="solid")
    fill_zebra = PatternFill(start_color=ZEBRA_FILL, end_color=ZEBRA_FILL, fill_type="solid")
    fill_total = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    thin_border_side = Side(border_style="thin", color="CBD5E1")
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    double_bottom_side = Side(border_style="double", color="1E293B")
    top_thin_side = Side(border_style="thin", color="1E293B")
    border_total = Border(top=top_thin_side, bottom=double_bottom_side)

    # 1. Title Banner (A1:G2)
    ws.merge_cells("A1:G2")
    title_cell = ws["A1"]
    title_cell.value = "📊 HISOBCHI AI — SHAXSIY MOLIYA HISOBOTI"
    title_cell.font = font_title
    title_cell.fill = fill_title
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    # 2. Metadata (Row 3 & 4)
    ws["A3"] = "Foydalanuvchi:"
    ws["B3"] = user_name
    ws["A4"] = "Hisobot davri:"
    ws["B4"] = period_name

    ws["E3"] = "Chiqarilgan sana:"
    ws["F3"] = datetime.now().strftime("%d.%m.%Y, %H:%M")
    ws["E4"] = "Jami amallar soni:"
    ws["F4"] = len(transactions)

    for r in range(3, 5):
        ws[f"A{r}"].font = font_meta
        ws[f"E{r}"].font = font_meta
        ws[f"B{r}"].font = font_regular
        ws[f"F{r}"].font = font_regular

    # 3. Table Headers (Row 6)
    headers = ["№", "Sana va Vaqt", "Amal turi", "Hisob turi", "Toifa / Kategoriya", "Summa (so'm)", "Izoh / Tavsif"]
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=6, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_cell
    ws.row_dimensions[6].height = 26

    # 4. Data Rows
    total_income = 0.0
    total_expense = 0.0
    start_row = 7

    for idx, tx in enumerate(transactions, start=1):
        row_num = start_row + idx - 1
        t_type = tx.get("type", "expense")
        amount = float(tx.get("amount", 0))
        created_at = tx.get("created_at", "")
        category = tx.get("category", "")
        pay_method = tx.get("payment_method", "💵 Naqd") or "💵 Naqd"
        desc = tx.get("description", "") or "—"

        is_income = (t_type == "income")
        if is_income:
            total_income += amount
            type_label = "Daromad"
            amt_str = f"+{int(amount):,}".replace(",", " ")
            amt_font = font_income
        else:
            total_expense += amount
            type_label = "Xarajat"
            amt_str = f"-{int(amount):,}".replace(",", " ")
            amt_font = font_expense

        row_data = [idx, created_at, type_label, pay_method, category, amt_str, desc]

        for col_idx, val in enumerate(row_data, start=1):
            cell = ws.cell(row=row_num, column=col_idx, value=val)
            cell.font = amt_font if col_idx == 6 else font_regular
            cell.border = border_cell

            # Alignment
            if col_idx in [1, 2, 3, 4]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 6:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            # Zebra striping
            if idx % 2 == 0:
                cell.fill = fill_zebra

        ws.row_dimensions[row_num].height = 20

    # 5. Totals Section
    summary_row_start = start_row + len(transactions) + 1

    totals_data = [
        ("JAMI DAROMAD:", f"+{int(total_income):,}".replace(",", " ") + " so'm", font_income),
        ("JAMI XARAJAT:", f"-{int(total_expense):,}".replace(",", " ") + " so'm", font_expense),
        ("SOF BALANS / QOLDIQ:", f"{int(total_income - total_expense):,}".replace(",", " ") + " so'm", font_total),
    ]

    for offset, (lbl, val, fnt) in enumerate(totals_data):
        curr_r = summary_row_start + offset
        ws.merge_cells(start_row=curr_r, start_column=4, end_row=curr_r, end_column=5)
        lbl_cell = ws.cell(row=curr_r, column=4, value=lbl)
        lbl_cell.font = font_meta
        lbl_cell.alignment = Alignment(horizontal="right", vertical="center")

        val_cell = ws.cell(row=curr_r, column=6, value=val)
        val_cell.font = fnt
        val_cell.alignment = Alignment(horizontal="right", vertical="center")
        val_cell.fill = fill_total

        for col in range(4, 7):
            ws.cell(row=curr_r, column=col).border = border_total

        ws.row_dimensions[curr_r].height = 24

    # 6. Adjust Column Widths
    col_widths = {1: 6, 2: 20, 3: 14, 4: 16, 5: 25, 6: 22, 7: 35}
    for col_idx, width in col_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    # Save to temp file
    fd, temp_path = tempfile.mkstemp(suffix=".xlsx", prefix="moliya_hisoboti_")
    import os
    os.close(fd)
    wb.save(temp_path)
    return temp_path
