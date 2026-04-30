"""
OCR Engine Module
Handles image preprocessing, text extraction via Tesseract, 
and sensitive information redaction.
"""

import os
import re
from collections import defaultdict
import cv2
import numpy as np
import pytesseract
from PIL import Image
import json
import time

# Auto-detect Tesseract executable path on Windows
tesseractPaths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for tPath in tesseractPaths:
    if os.path.exists(tPath):
        pytesseract.pytesseract.tesseract_cmd = tPath
        break


def preprocessImage(imagePath: str) -> np.ndarray:
    """
    Applies computer vision techniques to optimize the image for OCR.
    Includes grayscale conversion, upscaling, CLAHE normalization, and thresholding.
    """
    img = cv2.imread(imagePath)
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {imagePath}")

    # Convert to grayscale to simplify the processing
    grayImg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Upscale if the image is too small to ensure high OCR accuracy
    imgH, imgW = grayImg.shape
    if imgW < 1800:
        scaleF = 1800 / imgW
        grayImg = cv2.resize(grayImg, None, fx=scaleF, fy=scaleF, interpolation=cv2.INTER_CUBIC)

    # Enhance contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    grayImg = clahe.apply(grayImg)

    # Adaptive binarization to handle uneven lighting
    binaryImg = cv2.adaptiveThreshold(
        grayImg, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=15
    )
    return deskewImage(binaryImg)


def deskewImage(img: np.ndarray) -> np.ndarray:
    """
    Corrects any rotational skew in the image to align text horizontally.
    """
    coords = np.column_stack(np.where(img < 128))
    if len(coords) < 5:
        return img
        
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:
        return img

    h, w = img.shape
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def isTitleLine(text: str) -> bool:
    """
    Heuristic-based detection for document headings.
    Checks for markdown markers or formatting patterns.
    """
    sText = text.strip()
    if not sText: return False
    if sText.startswith("#"): return True
    
    # Title Case detection for lines that look like headings
    if len(sText) < 60 and sText[0].isupper() and sText[-1] not in ".,:;":
        words = sText.split()
        ratio = sum(1 for w in words if w[0].isupper()) / max(len(words), 1)
        if ratio > 0.6 and len(words) >= 2: return True
    return False


def detectAlignment(bbox: tuple, pageWidth: int) -> str:
    """
    Determines if a block of text is Left, Center, or Right aligned.
    """
    x1, _, x2, _ = bbox
    cX = (x1 + x2) / 2
    relPos = cX / pageWidth
    if 0.35 < relPos < 0.65: return "CENTER"
    if relPos > 0.75: return "RIGHT"
    return "LEFT"


def cleanText(text: str) -> str:
    """Removes OCR artifacts and formatting symbols from the text."""
    cText = re.sub(r"^#+\s*", "", text.strip())
    cText = re.sub(r"  +", " ", cText)
    return cText.strip()


def isBoldWord(word: str, conf: int) -> bool:
    """Detects if a word should be bolded based on capitalization or markers."""
    sWord = word.strip("*_")
    if sWord.isupper() and len(sWord) > 1: return True
    if word.startswith("*") or word.startswith("_"): return True
    return False


def maskSensitiveInfo(text: str) -> str:
    """
    Redacts emails and Pakistani CNIC numbers from the text for privacy.
    Uses robust regex patterns that account for OCR noise.
    """
    # Pattern accounts for single spaces often added by OCR
    emailPattern = r'[a-zA-Z0-9_.+-]+\s*@\s*[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    cnicPattern  = r'\d{5}-\d{7}-\d{1}'
    
    maskedText = re.sub(emailPattern, "[EMAIL MASKED]", text)
    maskedText = re.sub(cnicPattern, "[CNIC MASKED]", maskedText)
    
    return maskedText


def runOcr(imagePath: str, localMode: bool = True) -> dict:
    """
    The main OCR pipeline execution. 
    Returns a structured dictionary containing extracted text and formatting metadata.
    """
    processedImg = preprocessImage(imagePath)
    pilImg = Image.fromarray(processedImg)
    pWidth = pilImg.width

    # Log the processed file into the agent memory module
    memPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_memory.json")
    if os.path.exists(memPath):
        try:
            with open(memPath, "r", encoding="utf-8") as f: mData = json.load(f)
            mData["learnedCharacteristics"] = mData.get("learnedCharacteristics", 0) + 1
            with open(memPath, "w", encoding="utf-8") as f: json.dump(mData, f)
        except: pass

    # Extract raw text and detailed word-level data
    rawText = pytesseract.image_to_string(pilImg, lang="eng", config="--psm 6")
    ocrData = pytesseract.image_to_data(pilImg, lang="eng", config="--psm 6", output_type=pytesseract.Output.DICT)
    
    total = len(ocrData["text"])
    wordsList = []
    for i in range(total):
        wText = ocrData["text"][i].strip()
        confVal = ocrData["conf"][i]
        score = int(confVal) if str(confVal).lstrip("-").isdigit() else -1
        if not wText or score < 20: continue

        l, t, w, h = ocrData["left"][i], ocrData["top"][i], ocrData["width"][i], ocrData["height"][i]
        wordsList.append({
            "text": wText, "left": l, "top": t, "right": l + w, "bottom": t + h,
            "conf": score, "blockNum": ocrData["block_num"][i],
            "parNum": ocrData["par_num"][i], "lineNum": ocrData["line_num"][i]
        })

    # Fallback to line-based extraction if word-level data is sparse
    if not wordsList:
        pList = []
        for line in rawText.splitlines():
            line = line.strip()
            if not line: continue
            cLine = cleanText(line)
            if cLine:
                pList.append({
                    "text": cLine, "isHeading": isTitleLine(line) or isTitleLine(cLine),
                    "alignment": "LEFT", "runs": [{"text": cLine, "bold": False, "italic": False}]
                })
        return {"paragraphs": pList, "pageWidth": pWidth, "rawText": rawText}

    # Group words into logical lines and paragraphs
    lMap = defaultdict(list)
    for w in wordsList:
        lKey = (w["blockNum"], w["parNum"], w["lineNum"])
        lMap[lKey].append(w)

    lSorted = []
    for k, g in lMap.items():
        g.sort(key=lambda x: x["left"])
        yT, yB = min(w["top"] for w in g), max(w["bottom"] for w in g)
        xL, xR = min(w["left"] for w in g), max(w["right"] for w in g)
        lSorted.append({"key": k, "words": g, "top": yT, "bottom": yB, "left": xL, "right": xR, "height": yB - yT})

    lSorted.sort(key=lambda l: l["top"])
    
    # Calculate spacing threshold for paragraph grouping
    lHeights = sorted(l["height"] for l in lSorted if l["height"] > 0)
    gThreshold = max(lHeights[len(lHeights)//2] * 3.0, 50) if lHeights else 60

    pGroups, cGroup = [], []
    for i, l in enumerate(lSorted):
        if i == 0: cGroup.append(l); continue
        if (l["top"] - lSorted[i-1]["bottom"]) > gThreshold:
            if cGroup: pGroups.append(cGroup)
            cGroup = [l]
        else: cGroup.append(l)
    if cGroup: pGroups.append(cGroup)

    # Build the final structured output
    pList = []
    for group in pGroups:
        for line in group:
            fText = " ".join(w["text"] for w in line["words"]).strip()
            if not fText: continue
            cLine = cleanText(fText)
            if not cLine: continue

            rList = []
            for w in line["words"]:
                cWord = w["text"].strip("*_()[]{}")
                if not cWord: cWord = w["text"]
                rList.append({"text": cWord + " ", "bold": isBoldWord(w["text"], w["conf"]), "italic": w["text"].startswith("(") or w["text"].startswith("[")})

            pList.append({
                "text": cLine, "isHeading": isTitleLine(fText) or isTitleLine(cLine),
                "alignment": detectAlignment((line["left"], line["top"], line["right"], line["bottom"]), pWidth),
                "runs": rList
            })
        if len(pGroups) > 1: pList.append({"text": "", "isHeading": False, "alignment": "LEFT", "runs": []})

    return {"paragraphs": pList, "pageWidth": pWidth, "rawText": rawText}
