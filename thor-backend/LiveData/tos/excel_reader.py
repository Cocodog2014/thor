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
        """Close Excel connection (but don't close the workbook itself)"""
        self._workbook = None
        self._sheet = None
    
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
                    quote = self._parse_row(headers, row, row_idx + 4)  # +4 because data starts at row 4
                    if quote:
                        quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse row {row_idx + 4}: {e}")
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
        Other columns: Close, Open, NetChange, World High, World Low, Volume, Bid, Last, Ask, BidSize, AskSize
        
        Args:
            headers: List of column headers
            row: List of cell values
            row_idx: Row index (for error reporting)
            
        Returns:
            Quote dictionary or None if invalid
        """
        # First column is the symbol
        symbol = row[0] if row and row[0] else f"FUTURE_{row_idx}"
        
        # Create dict from headers and values (skip first column which is symbol)
        data = {}
        for i, header in enumerate(headers):
            if header and i < len(row):  # Skip None headers
                data[header] = row[i]
        
        # Extract fields (handle None/empty values)
        quote = {
            'symbol': str(symbol).strip() if symbol else f"FUTURE_{row_idx}",
            'last': self._to_decimal(data.get('Last')),
            'bid': self._to_decimal(data.get('Bid')),
            'ask': self._to_decimal(data.get('Ask')),
            'volume': self._to_int(data.get('Volume')),
            'close': self._to_decimal(data.get('Close')),
            'open': self._to_decimal(data.get('Open')),
            'high': self._to_decimal(data.get('World High')),
            'low': self._to_decimal(data.get('World Low')),
            'change': self._to_decimal(data.get('NetChange')),
            'bid_size': self._to_int(data.get('BidSize')),
            'ask_size': self._to_int(data.get('AskSize')),
            'timestamp': None,  # Excel RTD updates in real-time
        }
        
        # Only return if we have at least a valid symbol and last price
        if quote['symbol'] and quote['last'] is not None:
            return quote
        return None
    
    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Convert value to Decimal, return None if invalid"""
        if value is None or value == '':
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
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
