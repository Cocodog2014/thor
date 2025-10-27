"""
Debug script to see what's actually in the Excel file
"""
from LiveData.tos.excel_reader import TOSExcelReader

reader = TOSExcelReader(
    file_path=r'A:\Thor\RTD_TOS.xlsm',
    sheet_name='LiveData',
    data_range='A1:N13'
)

if reader.connect():
    # Read raw data
    raw_data = reader._sheet.range('A1:N13').value
    
    print("=" * 60)
    print("RAW EXCEL DATA (A1:N13)")
    print("=" * 60)
    
    for i, row in enumerate(raw_data, 1):
        if i == 1:
            print(f"\nRow {i} (HEADERS):")
        else:
            print(f"\nRow {i} (DATA):")
        
        if row:
            print(f"  Column A (Symbol): {row[0]}")
            print(f"  Column B: {row[1]}")
            print(f"  Column C: {row[2]}")
            print(f"  Full row ({len(row)} columns): {row}")
    
    reader.disconnect()
else:
    print("Failed to connect to Excel")
