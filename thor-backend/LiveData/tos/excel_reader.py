"""
TOS Excel RTD Reader - Generic reader for TOS RTD Excel spreadsheets

This is a GENERIC utility that can read any Excel range.
Specific configurations (file paths, ranges) should be provided by the consumer.
"""
import logging
import os
from typing import List, Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

try:
    import xlwings as xw
    XLWINGS_AVAILABLE = True
except ImportError:
    XLWINGS_AVAILABLE = False
    logger.warning("xlwings not available - TOS Excel reader disabled")


class TOSExcelReader:
    """
    Reads live TOS RTD data from Excel spreadsheet
    """
    
    def __init__(self, file_path: str, sheet_name: str = "Futures", data_range: str = "A1:M20"):
        """
        Initialize TOS Excel reader
        
        Args:
            file_path: Full path to Excel file (e.g., A:\\Thor\\CleanData.xlsm)
            sheet_name: Sheet name (default: "Futures")
            data_range: Data range to read (default: "A1:M20")
        """
        if not XLWINGS_AVAILABLE:
            raise ImportError("xlwings is required for TOS Excel reader")
        
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.data_range = data_range
        self._workbook = None
        self._sheet = None
    
    def connect(self) -> bool:
        """
        Connect to Excel workbook (open or attach to running instance)
        
        Returns:
            bool: True if connected successfully
        """
        try:
            if not os.path.exists(self.file_path):
                logger.error(f"Excel file not found: {self.file_path}")
                return False
            
            # Try to connect to running instance first
            try:
                self._workbook = xw.Book(self.file_path)
                logger.info(f"Connected to running Excel instance: {self.file_path}")
            except Exception:
                # Open new instance if not already running
                self._workbook = xw.Book(self.file_path)
                logger.info(f"Opened Excel file: {self.file_path}")
            
            self._sheet = self._workbook.sheets[self.sheet_name]
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Excel: {e}")
            return False
    
    def disconnect(self):
        """
        Close Excel connection and release COM objects.
        Important: This prevents Excel from freezing when polled frequently.
        """
        # Release references in reverse order
        if self._sheet:
            self._sheet = None
        if self._workbook:
            self._workbook = None
        
        # Force Python garbage collection to release COM objects immediately
        import gc
        gc.collect()
    
    def read_data(self, include_headers: bool = False) -> List[Dict[str, Any]]:
        """
        Read current data from Excel range
        
        Args:
            include_headers: If True, expects first row to be headers.
                           If False, data starts immediately (uses column indices)
        
        Returns:
            List of quote dictionaries with TOS RTD data
        """
        if not self._sheet:
            if not self.connect():
                logger.error("Cannot read data - not connected to Excel")
                return []
        
        try:
            # Read data range as 2D array
            raw_data = self._sheet.range(self.data_range).value
            
            if not raw_data:
                logger.warning(f"No data found in Excel range {self.data_range}")
                return []
            
            # Handle single row (convert to list of lists)
            if not isinstance(raw_data[0], (list, tuple)):
                raw_data = [raw_data]
            
            # Parse data rows
            quotes = []
            start_row = 0
            
            if include_headers:
                # First row is headers, data starts from row 1
                if len(raw_data) < 2:
                    logger.warning("No data rows found (only headers)")
                    return []
                headers = raw_data[0]
                start_row = 1
            else:
                # No headers in range, all rows are data
                # For T4:BJ13 range, we need to read headers from row 3 separately
                headers = None
                start_row = 0
            
            for row_idx, row in enumerate(raw_data[start_row:], start=start_row):
                if not row or not any(row):  # Skip empty rows
                    continue
                
                try:
                    # Row index for error reporting (1-indexed Excel row)
                    excel_row_num = row_idx + 1 if include_headers else row_idx
                    quote = self._parse_row(headers, row, excel_row_num)
                    if quote:
                        quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse row {excel_row_num}: {e}")
                    continue
            
            logger.info(f"Read {len(quotes)} quotes from Excel range {self.data_range}")
            return quotes
            
        except Exception as e:
            logger.error(f"Error reading Excel data from {self.data_range}: {e}")
            return []
    
    def _parse_row(self, headers: List[str], row: List[Any], row_idx: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single row of Excel data into a quote dictionary
        
    Based on your actual Excel structure:
    Column A: Symbol (YM, NQ, etc.)
    Other columns (new): Close, Open, NetChange, 24High, 24Low, 52WkHigh, 52WkLow, Volume, Bid, Last, Ask, BidSize, AskSize
    Backward compatible with legacy headers 'World High' / 'World Low'.
        
        Args:
            headers: List of column headers
            row: List of cell values
            row_idx: Row index (for error reporting)
            
        Returns:
            Quote dictionary or None if invalid
        """
        # Build a dict of header->value for this row (when headers provided)
        # Strip whitespace from header names to handle formatting inconsistencies
        data = {}
        if headers:
            for i, header in enumerate(headers):
                if header and i < len(row):  # Skip None headers
                    clean_header = str(header).strip() if header else None
                    if clean_header:
                        data[clean_header] = row[i]
        
        # Determine symbol and type robustly
        symbol = None
        instrument_type = None
        
        # Helper to fetch by case-insensitive header name aliases
        def get_by_alias(d: Dict[str, Any], aliases: List[str]) -> Optional[Any]:
            if not d:
                return None
            lower_map = {str(k).strip().lower(): v for k, v in d.items() if k}
            for a in aliases:
                v = lower_map.get(a.lower())
                if v not in (None, ""):
                    return v
            return None
        
        # If headers exist, prefer header-driven extraction
        if data:
            # Common header names for type and symbol columns
            instrument_type = get_by_alias(data, [
                'type', 'asset type', 'category', 'class'
            ])
            symbol = get_by_alias(data, [
                'symbol', 'ticker', 'ticker symbol', 'contract', 'underlying', 'root'
            ])
            
            # If no symbol found but first column is a type and second column looks like symbol, use column B
            if symbol in (None, "") and headers and len(row) >= 2:
                first_header = str(headers[0]).strip().lower() if headers[0] else ''
                second_header = str(headers[1]).strip().lower() if headers[1] else ''
                # Treat first column as type when header says so
                if first_header in ('type', 'asset type', 'category'):
                    # Column B should be the symbol
                    symbol = row[1]
                # If second header explicitly says symbol
                if (symbol in (None, "")) and second_header in ('symbol', 'ticker', 'ticker symbol'):
                    symbol = row[1]
        
        # Fallbacks when no headers were provided or symbol still not found
        if symbol in (None, ""):
            # If there are at least two columns and the first value looks like a type,
            # prefer column B as symbol; else default to column A
            type_like_values = {'futures', 'future', 'index', 'indexes', 'stock', 'stocks', 'equity', 'forex', 'crypto', 'bond'}
            if len(row) >= 2:
                first_val = str(row[0]).strip().lower() if row[0] is not None else ''
                if first_val in type_like_values:
                    symbol = row[1]
            if symbol in (None, ""):
                symbol = row[0] if row and row[0] else f"FUTURE_{row_idx}"
        
        # Normalize symbol
        symbol = str(symbol).strip() if symbol is not None else f"FUTURE_{row_idx}"
        
        # Extract fields (handle None/empty values)
        # Support both new and legacy header names
        high_24h_val = data.get('24High') if headers else None
        low_24h_val = data.get('24Low') if headers else None
        if high_24h_val is None:
            high_24h_val = data.get('World High')
        if low_24h_val is None:
            low_24h_val = data.get('World Low')
        
        # Extract fields (handle None/empty values)
        # Support both new and legacy header names
        high_24h_val = data.get('24High') if headers else None
        low_24h_val = data.get('24Low') if headers else None
        if high_24h_val is None:
            high_24h_val = data.get('World High')
        if low_24h_val is None:
            low_24h_val = data.get('World Low')

        # 52-week fields: support multiple header spellings seen across exports
        high_52w_val = (
            data.get('52WkHigh')
            or data.get('52wkHigh')
            or data.get('52 Week High')
            or data.get('52WeekHigh')
            or data.get('52HIGH')  # TOS Data Export name
        )
        low_52w_val = (
            data.get('52WkLow')
            or data.get('52wkLow')
            or data.get('52 Week Low')
            or data.get('52WeekLow')
            or data.get('52LOW')   # TOS Data Export name
        )
        quote = {
            'symbol': symbol if symbol else f"FUTURE_{row_idx}",
            'type': instrument_type if instrument_type else None,
            'last': self._to_decimal(data.get('Last')),
            'bid': self._to_decimal(data.get('Bid')),
            'ask': self._to_decimal(data.get('Ask')),
            'volume': self._to_int(data.get('Volume')),
            'close': self._to_decimal(data.get('Close')),
            'open': self._to_decimal(data.get('Open')),
            # 24h session high/low
            'high': self._to_decimal(high_24h_val),
            'low': self._to_decimal(low_24h_val),
            # 52-week high/low (optional columns)
            'high_52w': self._to_decimal(high_52w_val),
            'low_52w': self._to_decimal(low_52w_val),
            'change': self._to_decimal(data.get('NetChange')),
            'bid_size': self._to_int(data.get('BidSize')),
            'ask_size': self._to_int(data.get('AskSize')),
            'timestamp': None,  # Excel RTD updates in real-time
        }
        
        # Only return if we have at least a valid symbol
        # (last price can be None for instruments with parsing issues like Treasury bonds)
        if quote['symbol'] and quote['symbol'] != f"FUTURE_{row_idx}":
            if quote['last'] is None:
                logger.warning(f"Row {row_idx} ({quote['symbol']}): No valid 'Last' price. Raw value: {data.get('Last')}")
            return quote
        return None
    
    def _parse_bond_price(self, value: str) -> Optional[Decimal]:
        """
        Parse Treasury bond price in 32nds notation to decimal.
        
        Common formats:
        - "111-16" = 111 + 16/32 = 111.50
        - "111-16+" = 111 + 16.5/32 = 111.515625
        - "111'16" = 111 + 16/32 = 111.50
        - "111:16" = 111 + 16/32 = 111.50
        - "-0'06" = -0 - 6/32 = -0.1875
        
        Returns decimal price or None if unparseable
        """
        if not value or not isinstance(value, str):
            return None
        
        value = str(value).strip()
        
        # Handle negative values
        is_negative = value.startswith('-')
        if is_negative:
            value = value[1:]  # Remove the minus sign
        
        # Try common separators: apostrophe, dash, colon
        # Note: Check apostrophe before dash to avoid splitting negative numbers
        for sep in ["'", ':', '-']:
            if sep in value:
                try:
                    parts = value.split(sep)
                    if len(parts) != 2:
                        continue
                    
                    whole = Decimal(parts[0].strip())
                    frac_str = parts[1].strip()
                    
                    # Handle plus sign for half 32nds
                    has_plus = frac_str.endswith('+')
                    if has_plus:
                        frac_str = frac_str[:-1]
                    
                    numerator = Decimal(frac_str)
                    if has_plus:
                        numerator += Decimal('0.5')
                    
                    # Convert 32nds to decimal
                    decimal_part = numerator / Decimal('32')
                    result = whole + decimal_part
                    
                    # Apply negative sign if needed
                    if is_negative:
                        result = -result
                    
                    return result
                    
                except (ValueError, TypeError, IndexError):
                    continue
        
        return None
    
    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Convert value to Decimal, handling bond 32nds notation"""
        if value is None or value == '':
            return None
        
        # First try normal decimal conversion
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, Exception):
            # Catch all Decimal conversion errors including InvalidOperation
            pass
        
        # If that fails and it's a string, try bond price parsing
        if isinstance(value, str):
            bond_price = self._parse_bond_price(value)
            if bond_price is not None:
                return bond_price
        
        return None
    
    def _to_int(self, value: Any) -> Optional[int]:
        """Convert value to int, return None if invalid"""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


def get_tos_excel_reader(file_path: str, sheet_name: str = "Futures", data_range: str = "A1:M20") -> Optional[TOSExcelReader]:
    """
    Factory function to create TOS Excel reader
    
    Args:
        file_path: Path to Excel file
        sheet_name: Sheet name (default: "Futures")
        data_range: Data range to read (default: "A1:M20")
    
    Returns:
        TOSExcelReader instance or None if not available
    """
    if not XLWINGS_AVAILABLE:
        logger.warning("xlwings not available - cannot create TOS Excel reader")
        return None
    
    try:
        reader = TOSExcelReader(file_path, sheet_name, data_range)
        if reader.connect():
            return reader
        else:
            logger.error(f"Failed to connect to Excel file: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Failed to create TOS Excel reader: {e}")
        return None
