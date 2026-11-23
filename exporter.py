import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# التدرج اللوني لنسبة التطابق ولتغيير الحروف:
# 1. 100%: تطابق حرفي تام بدون أي تغيير في الحروف (أخضر هادئ)
FILL_PERFECT = PatternFill(start_color="D1E7DD", end_color="D1E7DD", fill_type="solid")
FONT_PERFECT = Font(name="Calibri", size=11, bold=True, color="0F5132")

# 2. 85% إلى 99.9%: تطابق عالي ولكن حدث تغيير حرفي بسيط (أ إلى ا، ي إلى ى، مسافة) (أزرق هادئ)
FILL_MODIFIED_HIGH = PatternFill(start_color="CFE2FF", end_color="CFE2FF", fill_type="solid")
FONT_MODIFIED_HIGH = Font(name="Calibri", size=11, bold=True, color="084298")

# 3. 70% إلى 84.9%: حدث تغيير أكبر في الحروف أو فصل مركب / اختلاف مقطع إضافي (أصفر تحذيري للمراجعة)
FILL_WARNING = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
FONT_WARNING = Font(name="Calibri", size=11, bold=True, color="664D03")

# 4. 0% أو غير مطابق: تلوين كامل الصف بالأحمر لبيان أنه غير موجود
FILL_DANGER = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
FONT_DANGER = Font(name="Calibri", size=11, bold=True, color="842029")

# نمط الاسم غير المتغير
FILL_UNCHANGED = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
FONT_UNCHANGED = Font(name="Calibri", size=11, color="64748B")

# تنسيق الرأس
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
REGULAR_FONT = Font(name="Calibri", size=11)

THIN_BORDER = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

def export_results_to_excel(results: list[dict], output_path: str, mode: str = "master"):
    """
    تصدير قائمة النتائج إلى ملف Excel بتنسيق RTL مع 3 أعمدة أساسية:
    - الاسم
    - الاسم المعدل (يترك فارغاً إذا لم يحقق شرط أول 3 أسماء)
    - نسبة التطابق (%) الفعلية:
      - إذا تطابق حرفياً 100% -> أخضر
      - إذا تغيرت حروف مثل (أ إلى ا، ي إلى ى، فصل مسافة) -> تتغير النسبة وتلون بالأزرق أو الأصفر
      - إذا لم يتطابق (0%) -> تلوين أحمر لكامل الصف.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "نتائج التعديل والمطابقة"
    
    # ضبط ورقة العمل لتكون من اليمين إلى اليسار RTL
    ws.sheet_view.rightToLeft = True

    # تحديد عنوان العمود الثاني والثالث بحسب النمط
    matched_col_title = "الاسم المطابق" if mode == "master" else "الاسم المعدل"
    score_col_title = "نسبة التطابق الحرفي (%)" if mode == "master" else "نسبة التطابق بعد التوحيد (%)"
    headers = ["الاسم", matched_col_title, score_col_title]
    ws.append(headers)

    # تنسيق رأس الجدول
    for col_num in range(1, 4):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[1].height = 28

    # إضافة وتلوين البيانات
    for row_idx, item in enumerate(results, start=2):
        orig = item.get('original', '')
        matched = item.get('matched', '')
        score = item.get('score', 0.0)

        c1 = ws.cell(row=row_idx, column=1, value=orig)
        c2 = ws.cell(row=row_idx, column=2, value=matched if matched else "")
        c3 = ws.cell(row=row_idx, column=3, value=f"{score}%" if score > 0 else "0%")

        # محاذاة وخطوط
        c1.alignment = Alignment(horizontal="right", vertical="center")
        c2.alignment = Alignment(horizontal="right", vertical="center")
        c3.alignment = Alignment(horizontal="center", vertical="center")

        c1.font = REGULAR_FONT
        c2.font = REGULAR_FONT

        c1.border = THIN_BORDER
        c2.border = THIN_BORDER
        c3.border = THIN_BORDER

        if mode == "master":
            # نمط المطابقة مع الشيت الرئيسي
            if score == 0.0 or not matched:
                # غير موجود نهائياً: تلوين كامل الصف بالأحمر
                c1.fill = FILL_DANGER
                c2.fill = FILL_DANGER
                c3.fill = FILL_DANGER
                c3.font = FONT_DANGER
            elif score >= 100.0:
                # متطابق حرفياً 100% بدون أي تعديل حروف
                c3.fill = FILL_PERFECT
                c3.font = FONT_PERFECT
            elif score >= 85.0:
                # حدث تعديل في بعض الحروف (أ إلى ا، ي إلى ى) -> تلوين أزرق هادئ
                c2.fill = FILL_MODIFIED_HIGH
                c3.fill = FILL_MODIFIED_HIGH
                c3.font = FONT_MODIFIED_HIGH
            else:
                # حدث تعديل أكبر أو اختلاف في أحد المقاطع الإضافية -> أصفر تحذيري
                c1.fill = FILL_WARNING
                c2.fill = FILL_WARNING
                c3.fill = FILL_WARNING
                c3.font = FONT_WARNING
        else:
            # نمط التوحيد المباشر
            if orig != matched:
                # حدث تعديل في حروف الاسم
                if score >= 85.0:
                    c2.fill = FILL_MODIFIED_HIGH
                    c3.fill = FILL_MODIFIED_HIGH
                    c3.font = FONT_MODIFIED_HIGH
                else:
                    c2.fill = FILL_WARNING
                    c3.fill = FILL_WARNING
                    c3.font = FONT_WARNING
            else:
                # الاسم مطابق أصلاً لقواعد التوحيد
                c3.fill = FILL_UNCHANGED
                c3.font = FONT_UNCHANGED

        ws.row_dimensions[row_idx].height = 24

    # ضبط العرض التلقائي للأعمدة
    ws.column_dimensions['A'].width = 34
    ws.column_dimensions['B'].width = 34
    ws.column_dimensions['C'].width = 24

    # تجميد الصف الأول
    ws.freeze_panes = "A2"

    wb.save(output_path)
