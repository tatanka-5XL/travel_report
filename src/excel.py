import openpyxl
from openpyxl.styles import Font
from openpyxl.worksheet.pagebreak import Break

''' Reading Excel sheets

wb = openpyxl.load_workbook('../input/example.xlsx')
print(wb.sheetnames)

sheet = wb['Sheet1']

print(sheet.title)

print(sheet['B3'].value)
'''

wb = openpyxl.Workbook()
print(wb.sheetnames)
sheet = wb.active
sheet.title = 'Spam Bacon Eggs Sheet'
print(wb.sheetnames)

# Print settings
sheet.print_area = "A1:F85"

# A4 + portrait (or switch to landscape if needed)
sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE  # try LANDSCAPE for wide tables

# Fit the print area to ONE page (this is the key)
sheet.page_setup.fitToWidth = 1
sheet.page_setup.fitToHeight = 1
sheet.sheet_properties.pageSetUpPr.fitToPage = True

# Reasonable margins (in inches!)
sheet.page_margins.left = 0.25
sheet.page_margins.right = 0.25
sheet.page_margins.top = 0.5
sheet.page_margins.bottom = 0.5

# Optional: center on page
sheet.page_setup.horizontalCentered = True




sheet.print_area = "A1:F85"
sheet.row_breaks.append(Break(id=85))
sheet.col_breaks.append(Break(id=6))

# Set default font for the workbook (matches Excel default)
default_font = Font(name="Helvetica", size=10)
for row in sheet.iter_rows(min_row=1, max_row=86, min_col=1, max_col=7):
    for cell in row:
        cell.font = default_font

for row_idx in range(1, 86):
    sheet.row_dimensions[row_idx].height = 16

sheet.column_dimensions["A"].width = 15.17
sheet.column_dimensions["B"].width = 68.5
sheet.column_dimensions["C"].width = 12
sheet.column_dimensions["D"].width = 12
sheet.column_dimensions["E"].width = 12
sheet.column_dimensions["F"].width = 12

wb.save('../output/spam.xlsx')