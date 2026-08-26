"""
Bindu Doctor
A simple diagnostic tool to verify local Bindu setup.
"""

import sys
import os


def check_python_version():
    if sys.version_info >= (3, 12):
        print("✅ Python version OK")
    else:
        print("❌ Python 3.12 or higher is required")
        print("   → Install via: https://www.python.org/downloads/")


def check_api_keys():
    if os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"):
        print("✅ API key found")
    else:
        print("⚠️ No API key found")
        print("   → Set OPENAI_API_KEY or OPENROUTER_API_KEY")


def main():
    print("🔍 Bindu Doctor\n")
    check_python_version()
    check_api_keys()
    print("\n🩺 Diagnosis complete.")


if __name__ == "__main__":
    main()