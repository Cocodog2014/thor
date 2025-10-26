"""
Diagnostic script to check Excel headers and raw data
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import xlwings as xw
    
    file_path = r"A:\Thor\CleanData.xlsm"
    sheet_name = "Futures"
    data_range = "A1:N12"
    
    print("=" * 70)
    print(f"Checking Excel file: {file_path}")
    print(f"Sheet: {sheet_name}")
    print(f"Range: {data_range}")
    print("=" * 70)
    
    # Connect to Excel
    try:
        wb = xw.Book(file_path)
        sheet = wb.sheets[sheet_name]
        
        # Read the range
        raw_data = sheet.range(data_range).value
        
        if raw_data and len(raw_data) > 0:
            # First row should be headers
            headers = raw_data[0]
            print("\n📋 HEADERS FOUND:")
            for i, header in enumerate(headers):
                print(f"  Column {chr(65+i)} ({i}): '{header}'")
            
            # Check for YM row (usually row 2)
            if len(raw_data) > 1:
                print("\n📊 YM DATA (Row 2):")
                ym_row = raw_data[1]
                for i, (header, value) in enumerate(zip(headers, ym_row)):
                    print(f"  {header}: {value}")
                    
                # Specifically check 24Low column
                if '24Low' in headers:
                    low_idx = headers.index('24Low')
                    print(f"\n✓ Found '24Low' at column {chr(65+low_idx)} (index {low_idx})")
                    print(f"  Value: {ym_row[low_idx]}")
                else:
                    print("\n✗ '24Low' header NOT found!")
                    print("  Available headers:", [h for h in headers if h])
                    
                if '24High' in headers:
                    high_idx = headers.index('24High')
                    print(f"\n✓ Found '24High' at column {chr(65+high_idx)} (index {high_idx})")
                    print(f"  Value: {ym_row[high_idx]}")
                else:
                    print("\n✗ '24High' header NOT found!")
                    
        else:
            print("✗ No data found in range!")
            
    except Exception as e:
        print(f"✗ Error reading Excel: {e}")
        import traceback
        traceback.print_exc()
        
except ImportError:
    print("✗ xlwings not installed!")
