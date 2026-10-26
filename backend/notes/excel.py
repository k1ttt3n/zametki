import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

MAX_ROWS = 10000


def _safe(value):
    """Защита от инъекций формул: значения, начинающиеся с = + - @, пишутся с апострофом."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def build_notes_xlsx(notes, prefix="notes"):
    """Собирает .xlsx в памяти и возвращает (имя_файла, байты). На диске файл не сохраняется."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Данные"

    headers = ["№", "Название", "Текст", "Категория", "Закреплена", "Создана", "Обновлена"]
    ws.append(headers)
    bold = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold
    ws.freeze_panes = "A2"

    truncated = False
    row_idx = 2
    for i, note in enumerate(notes):
        if i >= MAX_ROWS:
            truncated = True
            break
        ws.append([
            row_idx - 1,
            _safe(note.title),
            _safe(note.text),
            _safe(note.category),
            "Да" if note.is_pinned else "Нет",
            note.created_at.date(),
            note.updated_at.date(),
        ])
        row_idx += 1

    last_row = row_idx - 1
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(last_row, 1)}"

    # даты — форматом ДД.ММ.ГГГГ
    for col in (6, 7):
        for r in range(2, last_row + 1):
            ws.cell(row=r, column=col).number_format = "DD.MM.YYYY"

    # ширина колонок под содержимое
    for col in range(1, len(headers) + 1):
        width = max(
            (len(str(ws.cell(row=r, column=col).value or "")) for r in range(1, last_row + 1)),
            default=10,
        )
        ws.column_dimensions[get_column_letter(col)].width = min(max(width + 2, 8), 60)

    buf = io.BytesIO()
    wb.save(buf)

    today = date.today().strftime("%Y-%m-%d")
    filename = f"{prefix}_{today}.xlsx"
    meta = {"truncated": truncated, "rows": max(last_row - 1, 0)}
    return filename, buf.getvalue(), meta
