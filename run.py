#!/usr/bin/env python3
"""
FamilyGuard – AI-Powered Parental Payment Monitoring System
TAGLINE: “Smart spending for children. Intelligent protection for parents.”

Launcher Script
"""

import sys
import os
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")

    print("\n" + "=" * 70)
    print(" 🛡️  FamilyGuard – AI-Powered Parental Payment Monitoring System")
    print("    “Smart spending for children. Intelligent protection for parents.”")
    print("=" * 70)
    print(f"[*] Access Unified Web Application : http://{host}:{port}")
    print(f"[*] Interactive REST API Docs       : http://{host}:{port}/docs")
    print("\n[*] Synthetic Demo Credentials:")
    print("    - Parent Profile : parent@familyguard.demo / Password123!")
    print("    - Child Profile  : arjun@familyguard.demo  / Password123!")
    print("    - One-Click Mode : Click 'Parent' or 'Child' in the top header!")
    print("=" * 70 + "\n")

    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
