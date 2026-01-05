from __future__ import annotations
"""
Test precision-agnostic target computation.

Verifies that targets respect Instrument.display_precision
without any hard-coded decimal places.
"""
from decimal import Decimal
from django.test import TestCase

from Instruments.models import Instrument
from ThorTrading.studies.futures_total.models.target_high_low import TargetHighLowConfig
from ThorTrading.studies.futures_total.services.indicators import compute_targets_for_symbol


class PrecisionTargetsTestCase(TestCase):
    def setUp(self):
        # Canonical instruments with different precisions
        self.inst_2dec = Instrument.objects.create(
            symbol="ES",
            asset_type=Instrument.AssetType.FUTURE,
            name="S&P 500 Futures",
            country="USA",
            display_precision=2,
            is_active=True,
        )

        self.inst_3dec = Instrument.objects.create(
            symbol="SI",
            asset_type=Instrument.AssetType.FUTURE,
            name="Silver Futures",
            country="USA",
            display_precision=3,
            is_active=True,
        )

        self.inst_0dec = Instrument.objects.create(
            symbol="YM",
            asset_type=Instrument.AssetType.FUTURE,
            name="Dow Futures",
            country="USA",
            display_precision=0,
            is_active=True,
        )
        
        # Create configs
        TargetHighLowConfig.objects.create(
            country="USA",
            symbol='ES',
            mode=TargetHighLowConfig.MODE_POINTS,
            offset_high=Decimal('25'),
            offset_low=Decimal('25'),
            is_active=True
        )
        
        TargetHighLowConfig.objects.create(
            country="USA",
            symbol='SI',
            mode=TargetHighLowConfig.MODE_POINTS,
            offset_high=Decimal('0.500'),
            offset_low=Decimal('0.500'),
            is_active=True
        )
        
        TargetHighLowConfig.objects.create(
            country="USA",
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
        TargetHighLowConfig.objects.create(
            country="USA",
            symbol='NQ',
            mode=TargetHighLowConfig.MODE_PERCENT,
            percent_high=Decimal('0.50'),
            percent_low=Decimal('0.50'),
            is_active=True
        )

        # Create NQ with 2 decimals
        Instrument.objects.create(
            symbol="NQ",
            asset_type=Instrument.AssetType.FUTURE,
            name="Nasdaq Futures",
            country="USA",
            display_precision=2,
            is_active=True,
        )
        
        entry = Decimal('16000.00')
        high, low = compute_targets_for_symbol('NQ', entry)
        
        # +0.5% = 16080.00, -0.5% = 15920.00
        self.assertEqual(high, Decimal('16080.00'))
        self.assertEqual(low, Decimal('15920.00'))
    
    def test_missing_config_returns_none(self):
        """If no config exists, targets are not computed."""
        entry = Decimal("75.50")
        high, low = compute_targets_for_symbol("CL", entry)
        self.assertIsNone(high)
        self.assertIsNone(low)
    
    def test_missing_instrument_no_quantization(self):
        """If instrument missing, targets computed but not quantized"""
        # Config exists but there is no Instrument row for ZB
        TargetHighLowConfig.objects.create(
            country="USA",
            symbol="ZB",
            mode=TargetHighLowConfig.MODE_POINTS,
            offset_high=Decimal("20"),
            offset_low=Decimal("20"),
            is_active=True,
        )

        entry = Decimal('115.15625')
        high, low = compute_targets_for_symbol('ZB', entry)

        self.assertIsNotNone(high)
        self.assertIsNotNone(low)
        # Should be exact arithmetic without forced rounding
        self.assertEqual(high, entry + Decimal('20'))
        self.assertEqual(low, entry - Decimal('20'))

