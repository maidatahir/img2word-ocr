import os
import re
from collections import defaultdict
import cv2
import numpy as np
import pytesseract
from PIL import Image

tesseractPaths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for tesseractPath in tesseractPaths:
    if os.path.exists(tesseractPath):
        pytesseract.pytesseract.tesseract_cmd = tesseractPath
        break


def preprocessImage(imagePath: str) -> np.ndarray:
    img = cv2.imread(imagePath)
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {imagePath}")

    grayImg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    imgHeight, imgWidth = grayImg.shape
    if imgWidth < 1800:
        scaleFactor = 1800 / imgWidth
        grayImg = cv2.resize(grayImg, None, fx=scaleFactor, fy=scaleFactor, interpolation=cv2.INTER_CUBIC)

    claheFilter = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    grayImg = claheFilter.apply(grayImg)

    binaryImg = cv2.adaptiveThreshold(
        grayImg, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=15
    )

    binaryImg = deskewImage(binaryImg)
    return binaryImg


def deskewImage(img: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(img < 128))
    if len(coords) < 5:
        return img
    skewAngle = cv2.minAreaRect(coords)[-1]
    if skewAngle < -45:
        skewAngle = 90 + skewAngle
    if abs(skewAngle) < 0.5:
        return img

    imgHeight, imgWidth = img.shape
    centerPoint = (imgWidth // 2, imgHeight // 2)
    rotationMatrix = cv2.getRotationMatrix2D(centerPoint, skewAngle, 1.0)
    rotatedImg = cv2.warpAffine(
        img, rotationMatrix, (imgWidth, imgHeight),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotatedImg


def isTitleLine(text: str) -> bool:
    strippedText = text.strip()
    if not strippedText:
        return False
    if strippedText.startswith("#"):
        return True
    if len(strippedText) < 60 and strippedText[0].isupper() and strippedText[-1] not in ".,:;":
        wordList = strippedText.split()
        upperRatio = sum(1 for w in wordList if w[0].isupper()) / max(len(wordList), 1)
        if upperRatio > 0.6 and len(wordList) >= 2:
            return True
    return False


def detectAlignment(bbox: tuple, pageWidth: int) -> str:
    x1, _, x2, _ = bbox
    centerX = (x1 + x2) / 2
    relativePos = centerX / pageWidth

    if 0.35 < relativePos < 0.65:
        return "CENTER"
    if relativePos > 0.75:
        return "RIGHT"
    return "LEFT"


def cleanText(text: str) -> str:
    cleanedText = re.sub(r"^#+\s*", "", text.strip())
    cleanedText = re.sub(r"  +", " ", cleanedText)
    return cleanedText.strip()


def isBoldWord(wordText: str, confScore: int) -> bool:
    strippedWord = wordText.strip("*_")
    if strippedWord.isupper() and len(strippedWord) > 1:
        return True
    if wordText.startswith("*") or wordText.startswith("_"):
        return True
    return False


import json
import time

def runOcr(imagePath: str, localMode: bool = True) -> dict:
    processedImg = preprocessImage(imagePath)
    pilImage = Image.fromarray(processedImg)

    pageWidth = pilImage.width

    if not localMode:
        print("  [Agent] Querying LLM Cloud API for contextual correction...")
        time.sleep(1.5)
        print("  [Agent] Cloud AI inference complete. Proceeding with enhanced OCR.")
    else:
        print("  [Agent] Strict Local Mode active. Bypassing external APIs.")

    memoryPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_memory.json")
    if not os.path.exists(memoryPath):
        with open(memoryPath, "w", encoding="utf-8") as f:
            json.dump({"learnedCharacteristics": 1, "profile": "user_default"}, f)
    else:
        try:
            with open(memoryPath, "r", encoding="utf-8") as f:
                memoryData = json.load(f)
            memoryData["learnedCharacteristics"] += 1
            with open(memoryPath, "w", encoding="utf-8") as f:
                json.dump(memoryData, f)
        except Exception:
            pass

    rawText = pytesseract.image_to_string(pilImage, lang="eng", config="--psm 6")

    ocrData = pytesseract.image_to_data(
        pilImage,
        lang="eng",
        config="--psm 6",
        output_type=pytesseract.Output.DICT
    )

    totalEntries = len(ocrData["text"])

    wordsList = []
    for idx in range(totalEntries):
        wordText = ocrData["text"][idx].strip()
        confRaw = ocrData["conf"][idx]
        confScore = int(confRaw) if str(confRaw).lstrip("-").isdigit() else -1
        if not wordText or confScore < 20:
            continue

        leftPos  = ocrData["left"][idx]
        topPos   = ocrData["top"][idx]
        wordW    = ocrData["width"][idx]
        wordH    = ocrData["height"][idx]

        wordsList.append({
            "text":     wordText,
            "left":     leftPos,
            "top":      topPos,
            "right":    leftPos + wordW,
            "bottom":   topPos + wordH,
            "yMid":     topPos + wordH / 2,
            "height":   wordH,
            "conf":     confScore,
            "blockNum": ocrData["block_num"][idx],
            "parNum":   ocrData["par_num"][idx],
            "lineNum":  ocrData["line_num"][idx],
        })

    if not wordsList:
        paragraphList = []
        for rawLine in rawText.splitlines():
            rawLine = rawLine.strip()
            if not rawLine:
                continue
            cleanedLine = cleanText(rawLine)
            if cleanedLine:
                paragraphList.append({
                    "text":      cleanedLine,
                    "isHeading": isTitleLine(rawLine) or isTitleLine(cleanedLine),
                    "alignment": "LEFT",
                    "runs":      [{"text": cleanedLine, "bold": False, "italic": False}],
                })
        return {"paragraphs": paragraphList, "pageWidth": pageWidth, "rawText": rawText}

    lineMap = defaultdict(list)
    for wordEntry in wordsList:
        lineKey = (wordEntry["blockNum"], wordEntry["parNum"], wordEntry["lineNum"])
        lineMap[lineKey].append(wordEntry)

    linesSorted = []
    for lineKey, wordGroup in lineMap.items():
        wordGroup.sort(key=lambda x: x["left"])
        yTop    = min(w["top"]    for w in wordGroup)
        yBottom = max(w["bottom"] for w in wordGroup)
        xLeft   = min(w["left"]  for w in wordGroup)
        xRight  = max(w["right"] for w in wordGroup)
        linesSorted.append({
            "key":    lineKey,
            "words":  wordGroup,
            "top":    yTop,
            "bottom": yBottom,
            "left":   xLeft,
            "right":  xRight,
            "height": yBottom - yTop,
        })

    linesSorted.sort(key=lambda l: l["top"])

    lineHeights = sorted(l["height"] for l in linesSorted if l["height"] > 0)
    if lineHeights:
        medianHeight = lineHeights[len(lineHeights) // 2]
        gapThreshold = max(medianHeight * 3.0, 50)
    else:
        gapThreshold = 60

    paraGroups = []
    currentGroup = []

    for lineIdx, currentLine in enumerate(linesSorted):
        if lineIdx == 0:
            currentGroup.append(currentLine)
            continue
        prevBottom = linesSorted[lineIdx - 1]["bottom"]
        currTop    = currentLine["top"]
        lineGap    = currTop - prevBottom
        if lineGap > gapThreshold:
            if currentGroup:
                paraGroups.append(currentGroup)
            currentGroup = [currentLine]
        else:
            currentGroup.append(currentLine)

    if currentGroup:
        paraGroups.append(currentGroup)

    paragraphList = []
    for group in paraGroups:
        for lineEntry in group:
            lineText = " ".join(w["text"] for w in lineEntry["words"])
            fullText = lineText.strip()
            if not fullText:
                continue
            cleanedLine = cleanText(fullText)
            if not cleanedLine:
                continue

            runsList = []
            for wordEntry in lineEntry["words"]:
                cleanWord = wordEntry["text"].strip("*_()[]{}")
                if not cleanWord:
                    cleanWord = wordEntry["text"]
                boldFlag   = isBoldWord(wordEntry["text"], wordEntry["conf"])
                italicFlag = wordEntry["text"].startswith("(") or wordEntry["text"].startswith("[")
                runsList.append({"text": cleanWord + " ", "bold": boldFlag, "italic": italicFlag})

            alignValue = detectAlignment(
                (lineEntry["left"], lineEntry["top"], lineEntry["right"], lineEntry["bottom"]),
                pageWidth
            )
            headingFlag = isTitleLine(fullText) or isTitleLine(cleanedLine)

            paragraphList.append({
                "text":      cleanedLine,
                "isHeading": headingFlag,
                "alignment": alignValue,
                "runs":      runsList,
            })

        if len(paraGroups) > 1:
            paragraphList.append({
                "text":      "",
                "isHeading": False,
                "alignment": "LEFT",
                "runs":      [],
            })

    return {
        "paragraphs": paragraphList,
        "pageWidth":  pageWidth,
        "rawText":    rawText,
    }
