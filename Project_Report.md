# Project Report: Image-to-Word Converter (MVP)

**Course:** Principles and Practices of Information Technology (PPIT)  
**Project Title:** Basic Image-to-Word Converter  
**Technology Stack:** Python · Tesseract OCR · OpenCV · python-docx · Tkinter  

---

## 1. Introduction

### 1.1 Problem Statement

Converting scanned documents or hand-written notes into editable Word format typically results in plain, unformatted text. Users lose essential formatting elements—such as bold and italic styles, paragraph alignment, and structural hierarchy—requiring extensive manual reconstruction effort.

### 1.2 Objectives

The goal of this project is to develop a desktop application that:
- Accepts JPG/PNG input images (including handwritten notes).
- Preprocesses images for optimal OCR accuracy.
- Extracts structured text using the Tesseract OCR engine.
- Detects basic formatting attributes (headings, bold, italic, alignment).
- Generates a formatted `.docx` file that preserves the original document structure.

### 1.3 Scope

- **Input:** Single-page, English-language documents (typed or handwritten).
- **Output:** Microsoft Word `.docx` file.
- **Formatting detected:** Headings, bold, italic, left/centre/right alignment, paragraph structure.
- **Interface:** Desktop GUI built with Tkinter.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    main.py (Tkinter GUI)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Image Browse │  │ Options Panel│  │ Status/Output │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │
            ┌─────────▼──────────┐
            │  src/ocr_engine.py │
            │  ─────────────────  │
            │  1. Preprocessing  │
            │  2. Tesseract hOCR │
            │  3. Format Detect  │
            └─────────┬──────────┘
                      │  Structured Dict
            ┌─────────▼──────────────┐
            │ src/document_builder.py│
            │  ─────────────────────  │
            │  1. Apply Heading Style │
            │  2. Apply Bold/Italic   │
            │  3. Apply Alignment     │
            │  4. Save .docx          │
            └────────────────────────┘
```

---

## 3. Module Descriptions

### 3.1 `main.py` – GUI Application

The main entry point for the application. Built with Python's built-in **Tkinter** library using a modern dark-theme design.

**Features:**
- Image file browser (JPG, PNG, JPEG, BMP, TIFF supported).
- Live image preview panel with auto-scaling.
- Option toggles: image enhancement, formatting detection, alignment detection.
- Custom output folder selection.
- Threaded OCR execution (UI remains responsive during processing).
- Animated progress bar during conversion.
- Post-conversion dialog with option to open the file immediately.

### 3.2 `src/ocr_engine.py` – OCR and Preprocessing Engine

Handles all image analysis and text extraction.

#### Image Preprocessing Pipeline:

| Step | Technique | Purpose |
|------|-----------|---------|
| Grayscale conversion | `cv2.cvtColor` | Reduce complexity, prepare for thresholding |
| Upscaling | `cv2.resize` (INTER_CUBIC) | Improve OCR accuracy on low-res images |
| CLAHE | `cv2.createCLAHE` | Normalise uneven lighting (common in scanned notes) |
| Adaptive thresholding | `cv2.adaptiveThreshold` | Binarise image robustly (handles shadows) |
| Deskewing | `cv2.minAreaRect` | Correct rotational skew |

#### OCR and Formatting Detection:

The engine uses Tesseract's **hOCR** output format (an HTML-based layout description) rather than plain text. This provides:
- **Bounding boxes** for every word, line, and paragraph.
- **Word confidence scores** (x_wconf).
- **Paragraph structure** (`ocr_par` elements).

**Formatting Heuristics:**

| Attribute | Detection Method |
|-----------|-----------------|
| **Heading** | Starts with `#`, or short title-case line with >60% capitalised words |
| **Bold** | All-uppercase words, or words prefixed with `*`/`_` (OCR artefacts) |
| **Italic** | Words in parentheses `()` or brackets `[]` |
| **Alignment** | Bounding box x-centre vs page width: <35% → LEFT, 35–65% → CENTER, >75% → RIGHT |

### 3.3 `src/document_builder.py` – Word Document Builder

Converts the structured OCR output dictionary into a `.docx` file using **python-docx**.

**Document Construction:**
1. Sets professional page margins (1″ top/bottom, 1.25″ left/right).
2. Applies Word's built-in `Heading 1` / `Heading 2` styles for detected headings.
3. Constructs inline **run** objects for each word, applying `bold=True` or `italic=True`.
4. Maps alignment strings to `WD_ALIGN_PARAGRAPH` constants.
5. Configures consistent `Calibri 11pt` body font with 4pt paragraph spacing.

---

## 4. Installation & Running

### Prerequisites

1. **Python 3.9+** – [python.org](https://www.python.org)
2. **Tesseract OCR** – Install via:
   ```
   winget install UB-Mannheim.TesseractOCR
   ```
3. **Python Packages** – Install via:
   ```
   pip install -r requirements.txt
   ```

### Run Setup Check
```
python setup_check.py
```

### Launch Application
```
python main.py
```

---

## 5. Usage Guide

1. Launch `main.py`.
2. Click **Browse Image** or click the preview area to select a JPG/PNG file.
3. Adjust options in the Options panel if needed.
4. Click **⚡ Convert to Word**.
5. Wait for processing (progress bar will animate).
6. When complete, choose to open the file or find it in the same folder as the input.

---

## 6. Testing

### Test Cases

| Test | Input | Expected Output |
|------|-------|----------------|
| Handwritten chemistry notes | `sample1.jpeg` | Extracted text structured into paragraphs with heading detection |
| Multi-column layout | `sample2.jpeg` | Left/right columns correctly assigned alignment |
| Titled document | `sample3.jpeg` | Title detected as Heading 1 |
| Low-quality scan | Blurry image | CLAHE + upscaling improves accuracy before OCR |

### Sample Results

The sample images provided are handwritten chemistry notes (Colloidal Solutions, Surface Chemistry). The application:
- Detects section headings prefixed with `#` (e.g., `#Adsorption:`, `#Colloidal solution`).
- Extracts point-form content as body paragraphs.
- Preserves left/right column structure via alignment detection.

---

## 7. Limitations

| Limitation | Impact | Future Mitigation |
|------------|--------|------------------|
| Handwritten text OCR accuracy | ~60–70% character accuracy | Train custom Tesseract models for handwriting |
| No table detection | Tables extracted as plain text | Integrate layout analysis (e.g., Table Transformer) |
| No equation/symbol support | Math symbols OCR'd as approximations | LaTeX OCR integration (e.g., pix2tex) |
| Single-language (English) | Non-English text not supported | Add Tesseract language packs |

---

## 8. Future Enhancements

- **Phase 2:** Multi-language support, equation detection (LaTeX output).
- **Phase 3:** Table extraction and reconstruction.
- **Phase 4:** Cloud-based batch processing, REST API.
- **Phase 5:** Fine-tuned handwriting recognition model.

---

## 9. Agentic Transformation Section (Phase 2)

### 9.1 Technical Limitations of Phase 1
The Phase 1 application operates as a static, reactive tool. It relies on hard-coded heuristics (e.g., detecting headings via '#' or bolding via capitalisation) and executes a linear, rigid pipeline. It possesses **no autonomy** to deviate from its programmed path and **no intelligence** to understand the semantic context of the text it extracts. It simply translates pixels to characters without contextual awareness.

### 9.2 Agentic System Concept
An Agentic System moves beyond linear execution by incorporating four core pillars:
- **Perception:** Observing the environment (in this case, interpreting visual layouts and semantic text flow).
- **Decision-making:** Dynamically choosing the best processing path based on perceived context rather than static rules.
- **Action:** Executing the chosen strategy (e.g., applying dynamic formatting, querying external knowledge bases for technical terms).
- **Learning:** Improving future performance based on user feedback and past corrections.

### 9.3 Gap Analysis
Our current system is **not agentic** because it lacks a cognitive feedback loop. It cannot self-correct if the OCR outputs gibberish, it cannot contextually differentiate between a chemical formula and a standard paragraph, and it requires explicit human invocation for every step. It acts purely as a mechanical translator, not a cognitive assistant.

### 9.4 Agentic Vision
The goal for Phase 2 is to transform this reactive **tool** into a proactive **agent**. Instead of blindly converting images, the agent will understand the *domain* (e.g., recognizing that the input is a chemistry notebook). It will proactively suggest formatting corrections, automatically resolve OCR ambiguities by inferring context, and adapt to the user's specific handwriting style over time.

### 9.5 Agent Architecture
The redesigned architecture will shift to a cognitive flow:
- **Input:** Image ingestion.
- **Perception & Processing:** OCR combined with visual layout analysis.
- **Decision:** Contextual evaluation (e.g., "Is this a table, an equation, or a paragraph?").
- **Action:** Utilizing **External Tools** (e.g., invoking a dedicated LaTeX solver API for equations or an LLM for text correction).
- **Feedback & Memory:** Storing user corrections in a **Memory** module to update user-specific OCR profiles.

### 9.6 Agent Type Selection
The system will be designed as a **Learning, Goal-Based Agent**. 
*Justification:* A simple reflex agent is insufficient for the ambiguities of handwritten text. A goal-based agent can actively pursue the goal of "semantic accuracy" by querying external LLMs when confidence is low. Incorporating a learning component ensures the agent adapts to individual users' handwriting quirks, progressively reducing error rates.

### 9.7 Operational Workflow
1. **Observe:** Scan the image and extract raw text and layout metadata.
2. **Interpret:** Analyze the semantic context using an intelligence layer (identifying subjects, headings, and equations).
3. **Decide:** Determine if external tools (like a math-solver API) are needed for specific segments.
4. **Act:** Reconstruct the document logically and semantically in Word.
5. **Learn:** Update its internal handwriting profile based on post-generation corrections made by the user.

### 9.8 Intelligence Layer
The transformation requires integrating **Large Language Models (LLMs)** (such as GPT-4o or Claude) to replace static rules. The LLM will handle semantic correction—fixing OCR typos by understanding the surrounding sentence context—and dynamically map unformatted text into proper structural hierarchies without relying on rudimentary `#` or `*` triggers.

### 9.9 Memory & Context
- **Short-term Memory:** Maintains context within a single document session, ensuring formatting consistency across multiple pages of the same chapter.
- **Long-term Memory:** Stores user-specific profiles, retaining knowledge of a user's unique handwriting characteristics (e.g., how they draw a specific chemical bond) and preferred output formatting templates.

### 9.10 Autonomy Level
The system will operate with **Semi-Autonomy**. 
*Justification:* Full autonomy is risky when dealing with academic or legal documents where absolute factual accuracy is required. The agent will autonomously handle layout and OCR corrections, but will flag low-confidence interpretations (like complex chemical equations) for final human approval before finalizing the document.

### 9.11 Human-in-the-Loop (HITL)
The human acts as a supervisor. The agent presents a "confidence heatmap" of the converted document. The human controls the system by reviewing flagged, low-confidence sections, providing corrections that the agent then ingests into its long-term learning memory.

### 9.12 Ethical Agent Design
- **Privacy:** User documents (often containing sensitive intellectual property or personal notes) must be processed locally where possible, or anonymised before hitting external LLM APIs.
- **Bias:** The agent must be trained on diverse handwriting samples to ensure it does not perform poorly for users with non-standard writing styles or physical disabilities affecting motor control.
- **Transparency:** The agent must clearly indicate which parts of the text were "hallucinated" or auto-corrected by the LLM versus what was strictly read by the OCR.
- **User Control:** Users must have the ability to purge their long-term memory profiles at any time.

### 9.13 Risk Assessment
- **Incorrect Decisions:** An over-eager LLM might "autocorrect" a rare chemical formula into a common English word, destroying the academic value of the note.
- **Over-automation:** Users might blindly trust the agent, leading to the propagation of factual errors in study materials.
- **Misuse:** The tool could be used to digitize and claim copyright over proprietary documents or exams without consent.

### 9.14 Safety Mechanisms
- **Logging:** Maintain an immutable log of raw OCR output vs. Agent-corrected output so users can always revert to the original text.
- **Override:** A global "Strict OCR Mode" that disables the LLM intelligence layer entirely, reverting the agent to a basic tool when absolute literal transcription is needed.
- **Explainability:** When the agent changes a word, it will provide a margin comment in the Word document explaining its reasoning (e.g., *"Corrected 'H20' to 'H2O' based on chemistry context"*).

---

## 10. References

1. Smith, R. (2007). *An Overview of the Tesseract OCR Engine.* Proc. ICDAR.
2. Bradski, G. (2000). *The OpenCV Library.* Dr. Dobb's Journal of Software Tools.
3. python-docx documentation: https://python-docx.readthedocs.io
4. Tesseract hOCR format: https://github.com/tesseract-ocr/tesseract/wiki/Command-Line-Usage
5. Pillow documentation: https://pillow.readthedocs.io

---

*Generated for PPIT Project – Image-to-Word Converter MVP Phase 2 Transformation*
