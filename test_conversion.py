# -*- coding: utf-8 -*-
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

baseDir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, baseDir)

from src.ocr_engine       import runOcr
from src.document_builder import buildDocx

sampleFiles = ["sample1.jpeg", "sample2.jpeg", "sample3.jpeg"]

for fileName in sampleFiles:
    imgPath = os.path.join(baseDir, fileName)
    if not os.path.exists(imgPath):
        print(f"  SKIP  {fileName} (not found)")
        continue

    print(f"\nProcessing: {fileName}")
    print("  Running OCR...")
    try:
        ocrResult   = runOcr(imgPath)
        totalParas  = len(ocrResult["paragraphs"])
        totalHeadings = sum(1 for p in ocrResult["paragraphs"] if p["isHeading"])
        print(f"  Extracted {totalParas} paragraphs, {totalHeadings} headings")

        outFileName = fileName.replace(".jpeg", "_converted.docx")
        outFilePath = os.path.join(baseDir, outFileName)
        buildDocx(ocrResult, outFilePath)
        print(f"  Saved: {outFileName}")

        print("  Preview (first 3 paragraphs):")
        for paraIdx, paraEntry in enumerate(ocrResult["paragraphs"][:3]):
            headingTag = "[H]" if paraEntry["isHeading"] else "   "
            print(f"     {headingTag} ({paraEntry['alignment']}) {paraEntry['text'][:80]}")

    except Exception as excMsg:
        print(f"  ERROR: {excMsg}")
        import traceback
        traceback.print_exc()

print("\nDone.")
