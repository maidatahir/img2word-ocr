# 📝 Image To Text: Agentic OCR Utility

A professional, offline-first Image-to-Word converter designed for privacy-conscious users. This utility uses local OCR processing combined with an agentic assistant to provide high-fidelity text extraction without ever sending your data to the cloud.

## ✨ Key Features
- **Agentic Core:** Built-in AI assistant that learns your processing patterns locally.
- **Privacy First:** 100% offline. No data leaves your machine.
- **Multi-Format Export:** Extract text directly into Word (.docx), PDF, or plain text (.txt).
- **Intelligent Layouts:** Detects headings, bold text, and alignments to preserve document structure.
- **Modern UI:** iOS-inspired minimalist interface with real-time backend process visualization.

## 🚀 Getting Started

### Prerequisites
1. **Python 3.8+**
2. **Tesseract OCR:** Install Tesseract on your system.
   - [Download Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/maidatahir/img2word-ocr.git
   cd img2word-ocr
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App
```bash
python main.py
```

## 🛠️ Tech Stack
- **GUI:** CustomTkinter (Python)
- **OCR Engine:** Pytesseract & OpenCV
- **Document Generation:** Python-Docx & ReportLab
- **Logic:** Agentic reasoning with local memory persistence

## 🛡️ Privacy & Security
This project was built as a final year utility to demonstrate that agentic AI can be both powerful and secure. By keeping the processing local, we ensure that sensitive documents remain entirely under the user's control.

---
*Created as part of an 8th-semester final project.*
