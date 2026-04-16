import sys
import subprocess
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

textColorRed    = "\033[91m"
textColorGreen  = "\033[92m"
textColorYellow = "\033[93m"
textColorCyan   = "\033[96m"
textReset       = "\033[0m"
textBold        = "\033[1m"

def performCheck(checkLabel, checkFn):
    try:
        checkResult = checkFn()
        print(f"  {textColorGreen}✓{textReset}  {checkLabel}" + (f"  → {checkResult}" if checkResult else ""))
        return True
    except Exception as excMsg:
        print(f"  {textColorRed}✗{textReset}  {checkLabel}  →  {textColorRed}{excMsg}{textReset}")
        return False

print(f"\n{textBold}{textColorCyan}Image→Word Converter - Dependency Check{textReset}\n")

print(f"{textBold}Python{textReset}")
isPythonOk = performCheck(
    f"Python >= 3.9",
    lambda: (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 9)
        else (_ for _ in ()).throw(RuntimeError(f"Python {sys.version_info} is too old"))
    ),
)

print(f"\n{textBold}Python Packages{textReset}")
requiredPackages = {
    "pytesseract":    lambda: __import__("pytesseract").__version__,
    "Pillow":         lambda: __import__("PIL").__version__,
    "opencv-python":  lambda: __import__("cv2").__version__,
    "python-docx":    lambda: __import__("docx").__version__,
    "beautifulsoup4": lambda: __import__("bs4").__version__,
    "lxml":           lambda: __import__("lxml").__version__,
    "numpy":          lambda: __import__("numpy").__version__,
}
arePackagesOk = all(performCheck(pkgName, pkgFn) for pkgName, pkgFn in requiredPackages.items())

print(f"\n{textBold}Tesseract OCR Engine{textReset}")
tesseractPaths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
isTesseractFound = False
for tesseractPath in tesseractPaths:
    if os.path.exists(tesseractPath):
        isTesseractFound = True
        performCheck("Tesseract binary", lambda: tesseractPath)
        break

if not isTesseractFound:
    try:
        processResult = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        if processResult.returncode == 0:
            tesseractVersion = processResult.stdout.splitlines()[0]
            performCheck("Tesseract in PATH", lambda: tesseractVersion)
            isTesseractFound = True
    except FileNotFoundError:
        pass

if not isTesseractFound:
    print(f"  {textColorRed}✗{textReset}  Tesseract OCR not found!")
    print(f"\n{textColorYellow}  Install Tesseract via winget:{textReset}")
    print(f"    winget install UB-Mannheim.TesseractOCR")
    print(f"\n{textColorYellow}  Or download from:{textReset}")
    print(f"    https://github.com/UB-Mannheim/tesseract/wiki")
    print(f"\n{textColorYellow}  After installation, restart this script.{textReset}")
else:
    import pytesseract
    for tesseractPath in tesseractPaths:
        if os.path.exists(tesseractPath):
            pytesseract.pytesseract.tesseract_cmd = tesseractPath
            break
    performCheck("Tesseract importable via pytesseract", lambda: pytesseract.get_tesseract_version())

print(f"\n{'─'*48}")
if isPythonOk and arePackagesOk and isTesseractFound:
    print(f"{textColorGreen}{textBold}✅  All checks passed! You can now run:{textReset}")
    print(f"    python main.py\n")
else:
    print(f"{textColorYellow}{textBold}⚠  Some checks failed. Fix the issues above, then re-run.{textReset}\n")
    if not arePackagesOk:
        print(f"{textColorYellow}  To install missing packages:{textReset}")
        print(f"    pip install -r requirements.txt\n")
