#!/usr/bin/env python
"""
WebSocket Cutover Status - Check before starting server

Shows which features are in WebSocket mode vs REST shadow mode.
"""

import os
import sys

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thor_project.settings')

import django
django.setup()

from GlobalMarkets.services.websocket_features import WebSocketFeatureFlags

def print_status():
    """Print cutover status"""
    flags = WebSocketFeatureFlags()
    status = flags.get_status()
    
    print("\n" + "="*60)
    print("🔌 WebSocket Cutover Status")
    print("="*60)
    
    all_live = flags.all_live()
    any_live = flags.any_live()
    
    if all_live:
        print("\n✅ FULL CUTOVER - All features using WebSocket")
    elif any_live:
        print("\n⚡ PARTIAL CUTOVER - Some features using WebSocket")
    else:
        print("\n⚪ SHADOW MODE - All features using REST (WebSocket logging)")
    
    print("\nPer-Feature Status:")
    print("-" * 60)
    
    for feature, enabled in status.items():
        icon = "✅ WS" if enabled else "⚪ REST"
        env_var = f"WS_FEATURE_{feature.upper()}"
        print(f"  {icon:8} {feature:20} (set {env_var}=true to enable)")
    
    print("\n" + "-" * 60)
    print("\n📋 Cutover Plan:")
    print("  1. Enable feature: export WS_FEATURE_<name>=true")
    print("  2. Run market session and verify console logs")
    print("  3. Compare WS payload with REST endpoint")
    print("  4. Once verified, delete REST timer and endpoint")
    print("  5. Repeat for next feature")
    print("\n💾 REST endpoints remain active during shadow mode")
    print("⚡ All WebSocket messages logged to console regardless of flag")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    print_status()
