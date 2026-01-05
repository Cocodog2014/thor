from __future__ import annotations
"""
Test precision-agnostic target computation.

Verifies that targets respect TradingInstrument.display_precision
without any hard-coded decimal places.
"""
from decimal import Decimal
from django.test import TestCase

from Instruments.models.rtd import TradingInstrument, InstrumentCategory
from ThorTrading.studies.futures_total.models.target_high_low import TargetHighLowConfig
from ThorTrading.studies.futures_total.services.indicators import compute_targets_for_symbol


class PrecisionTargetsTestCase(TestCase):
    def setUp(self):
        # Create category
        self.category = InstrumentCategory.objects.create(
            name='futures',
            display_name='Futures'
        )
        
        # Create instruments with different precisions
        self.inst_2dec = TradingInstrument.objects.create(
            symbol='ES',
            name='S&P 500 Futures',
            category=self.category,
            display_precision=2
        )
        
        self.inst_3dec = TradingInstrument.objects.create(
            symbol='SI',
            name='Silver Futures',
            category=self.category,
            display_precision=3
        )
        
        self.inst_0dec = TradingInstrument.objects.create(
            symbol='YM',
            name='Dow Futures',
            category=self.category,
            display_precision=0
        )
        
        # Create configs
        TargetHighLowConfig.objects.create(
            symbol='ES',
            mode=TargetHighLowConfig.MODE_POINTS,
            offset_high=Decimal('25'),
            offset_low=Decimal('25'),
            is_active=True
        )
        
        TargetHighLowConfig.objects.create(
            symbol='SI',
            mode=TargetHighLowConfig.MODE_POINTS,
            offset_high=Decimal('0.500'),
            offset_low=Decimal('0.500'),
            is_active=True
        )
        
        TargetHighLowConfig.objects.create(
            symbol='YM',
            mode=TargetHighLowConfig.MODE_POINTS,
            offset_high=Decimal('200'),
            offset_low=Decimal('200'),
            is_active=True
        )
    
    def test_2_decimal_precision(self):
        """ES should use 2 decimal places"""
        entry = Decimal('4500.00')
        high, low = compute_targets_for_symbol('ES', entry)
        
        self.assertEqual(high, Decimal('4525.00'))
        self.assertEqual(low, Decimal('4475.00'))
        
        # Verify no extra precision
        self.assertEqual(str(high), '4525.00')
        self.assertEqual(str(low), '4475.00')
    
    def test_3_decimal_precision(self):
        """SI should use 3 decimal places"""
        entry = Decimal('24.125')
        high, low = compute_targets_for_symbol('SI', entry)
        
        self.assertEqual(high, Decimal('24.625'))
        self.assertEqual(low, Decimal('23.625'))
        
        # Verify precision
        self.assertEqual(str(high), '24.625')
        self.assertEqual(str(low), '23.625')
    
    def test_0_decimal_precision(self):
        """YM should use 0 decimal places (whole numbers)"""
        entry = Decimal('43500')
        high, low = compute_targets_for_symbol('YM', entry)
        
        self.assertEqual(high, Decimal('43700'))
        self.assertEqual(low, Decimal('43300'))
        
        # Verify no decimals
        self.assertEqual(str(high), '43700')
        self.assertEqual(str(low), '43300')
    
    def test_percent_mode_respects_precision(self):
        """Percent mode should also respect display_precision"""
        cfg = TargetHighLowConfig.objects.create(
            symbol='NQ',
            mode=TargetHighLowConfig.MODE_PERCENT,
            percent_high=Decimal('0.50'),
            percent_low=Decimal('0.50'),
            is_active=True
        )
        
        # Create NQ with 2 decimals
        TradingInstrument.objects.create(
            symbol='NQ',
            name='Nasdaq Futures',
            category=self.category,
            display_precision=2
        )
        
        entry = Decimal('16000.00')
        high, low = compute_targets_for_symbol('NQ', entry)
        
        # +0.5% = 16080.00, -0.5% = 15920.00
        self.assertEqual(high, Decimal('16080.00'))
        self.assertEqual(low, Decimal('15920.00'))
    
    def test_legacy_fallback_respects_precision(self):
        """Legacy ±20 fallback should also respect precision"""
        # Create instrument without config
        TradingInstrument.objects.create(
            symbol='CL',
            name='Crude Oil',
            category=self.category,
            display_precision=2
        )
        
        entry = Decimal('75.50')
        high, low = compute_targets_for_symbol('CL', entry)
        
        # Legacy +/-20
        self.assertEqual(high, Decimal('95.50'))
        self.assertEqual(low, Decimal('55.50'))
    
    def test_missing_instrument_no_quantization(self):
        """If instrument missing, targets computed but not quantized"""
        # No instrument for ZB
        entry = Decimal('115.15625')
        high, low = compute_targets_for_symbol('ZB', entry)
        
        # Fallback +/-20, but no quantization applied
        self.assertIsNotNone(high)
        self.assertIsNotNone(low)
        # Should be exact arithmetic without forced rounding
        self.assertEqual(high, entry + Decimal('20'))
        self.assertEqual(low, entry - Decimal('20'))

