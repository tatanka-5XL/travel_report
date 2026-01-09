import openpyxl


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
wb.save('../output/spam.xlsx')