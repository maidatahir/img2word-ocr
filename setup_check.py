# -*- coding: utf-8 -*-
"""
setup_check.py
--------------
Run this script FIRST to verify all dependencies are installed correctly.
It will guide you through any missing components.

Usage:
    python setup_check.py
"""

import sys
import subprocess
import os

# Force UTF-8 output to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def check(label, fn):
    try:
        result = fn()
        print(f"  {GREEN}✓{RESET}  {label}" + (f"  → {result}" if result else ""))
        return True
    except Exception as e:
        print(f"  {RED}✗{RESET}  {label}  →  {RED}{e}{RESET}")
        return False

print(f"\n{BOLD}{CYAN}Image→Word Converter – Dependency Check{RESET}\n")

# ── Python version
print(f"{BOLD}Python{RESET}")
py_ok = check(
    f"Python ≥ 3.9",
    lambda: (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 9)
        else (_ for _ in ()).throw(RuntimeError(f"Python {sys.version_info} is too old"))
    ),
)

# ── Python packages
print(f"\n{BOLD}Python Packages{RESET}")
packages = {
    "pytesseract":  lambda: __import__("pytesseract").__version__,
    "Pillow":       lambda: __import__("PIL").__version__,
    "opencv-python":lambda: __import__("cv2").__version__,
    "python-docx":  lambda: __import__("docx").__version__,
    "beautifulsoup4": lambda: __import__("bs4").__version__,
    "lxml":         lambda: __import__("lxml").__version__,
    "numpy":        lambda: __import__("numpy").__version__,
}
pkg_ok = all(check(name, fn) for name, fn in packages.items())

# ── Tesseract binary
print(f"\n{BOLD}Tesseract OCR Engine{RESET}")
tess_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
tess_found = False
for p in tess_paths:
    if os.path.exists(p):
        tess_found = True
        check("Tesseract binary", lambda: p)
        break

if not tess_found:
    # Try PATH
    try:
        result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            ver = result.stdout.splitlines()[0]
            check("Tesseract in PATH", lambda: ver)
            tess_found = True
    except FileNotFoundError:
        pass

if not tess_found:
    print(f"  {RED}✗{RESET}  Tesseract OCR not found!")
    print(f"\n{YELLOW}  ► Install Tesseract via winget:{RESET}")
    print(f"    winget install UB-Mannheim.TesseractOCR")
    print(f"\n{YELLOW}  ► Or download from:{RESET}")
    print(f"    https://github.com/UB-Mannheim/tesseract/wiki")
    print(f"\n{YELLOW}  After installation, restart this script.{RESET}")
else:
    import pytesseract
    for p in tess_paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break
    check("Tesseract importable via pytesseract", lambda: pytesseract.get_tesseract_version())

# ── Summary
print(f"\n{'─'*48}")
if py_ok and pkg_ok and tess_found:
    print(f"{GREEN}{BOLD}✅  All checks passed! You can now run:{RESET}")
    print(f"    python main.py\n")
else:
    print(f"{YELLOW}{BOLD}⚠  Some checks failed. Fix the issues above, then re-run.{RESET}\n")
    if not pkg_ok:
        print(f"{YELLOW}  To install missing packages:{RESET}")
        print(f"    pip install -r requirements.txt\n")
