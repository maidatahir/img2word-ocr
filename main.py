import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

baseDir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, baseDir)

from src.ocr_engine       import runOcr
from src.document_builder import buildDocx

bgDark      = "#0f0f1a"
bgCard      = "#1a1a2e"
bgCard2     = "#16213e"
accentColor = "#e94560"
accent2     = "#0f3460"
textPrimary = "#eaeaea"
textMuted   = "#8892b0"
successColor = "#4ecca3"
errorColor  = "#e94560"
btnHover    = "#c73652"
fontFamily  = "Segoe UI"


class ImageToWordApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image to Word Converter")
        self.geometry("960x700")
        self.minsize(820, 620)
        self.configure(bg=bgDark)
        self.resizable(True, True)

        self.imagePath = None
        self.tkImg     = None
        self.isProcessing = False

        self.buildUi()
        self.checkTesseract()

    def checkTesseract(self):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except Exception:
            messagebox.showerror(
                "Tesseract Not Found",
                "Tesseract OCR is not installed or not on PATH.\n\n"
                "Please install it:\n"
                "  winget install UB-Mannheim.TesseractOCR\n\n"
                "Then restart this application.",
            )

    def buildUi(self):
        headerFrame = tk.Frame(self, bg=bgCard, height=70)
        headerFrame.pack(fill="x", side="top")
        headerFrame.pack_propagate(False)

        tk.Label(
            headerFrame,
            text="Image to Word Converter",
            font=(fontFamily, 18, "bold"),
            bg=bgCard,
            fg=textPrimary,
        ).pack(side="left", padx=24, pady=15)

        tk.Label(
            headerFrame,
            text="Powered by Tesseract OCR",
            font=(fontFamily, 9),
            bg=bgCard,
            fg=textMuted,
        ).pack(side="right", padx=24, pady=15)

        tk.Frame(self, bg=accentColor, height=2).pack(fill="x")

        contentFrame = tk.Frame(self, bg=bgDark)
        contentFrame.pack(fill="both", expand=True, padx=20, pady=20)

        leftPanel = tk.Frame(contentFrame, bg=bgCard, bd=0, relief="flat")
        leftPanel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            leftPanel,
            text="INPUT IMAGE",
            font=(fontFamily, 9, "bold"),
            bg=bgCard,
            fg=accentColor,
        ).pack(anchor="nw", padx=16, pady=(14, 4))

        self.previewCanvas = tk.Canvas(
            leftPanel,
            bg=bgCard2,
            highlightthickness=1,
            highlightbackground=accent2,
            cursor="hand2",
        )
        self.previewCanvas.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.previewCanvas.bind("<Button-1>", lambda e: self.browseImage())

        self.placeholderTextId = self.previewCanvas.create_text(
            200, 200,
            text="Click to select an image\n\n(JPG / PNG / JPEG)",
            fill=textMuted,
            font=(fontFamily, 12),
            justify="center",
            tags="placeholder",
        )
        self.previewCanvas.bind("<Configure>", self.onCanvasResize)

        rightPanel = tk.Frame(contentFrame, bg=bgDark, width=260)
        rightPanel.pack(side="right", fill="y", padx=(10, 0))
        rightPanel.pack_propagate(False)

        self.browseBtn = self.makeButton(rightPanel, "Browse Image", self.browseImage, isPrimary=False)
        self.browseBtn.pack(fill="x", pady=(0, 12))

        fileCard = tk.Frame(rightPanel, bg=bgCard, pady=10, padx=10)
        fileCard.pack(fill="x", pady=(0, 16))
        tk.Label(
            fileCard,
            text="SELECTED FILE",
            font=(fontFamily, 8, "bold"),
            bg=bgCard,
            fg=accentColor,
        ).pack(anchor="w")
        self.fileLabel = tk.Label(
            fileCard,
            text="No file selected",
            font=(fontFamily, 9),
            bg=bgCard,
            fg=textMuted,
            wraplength=230,
            justify="left",
            anchor="w",
        )
        self.fileLabel.pack(anchor="w", pady=(4, 0))

        optsCard = tk.Frame(rightPanel, bg=bgCard, pady=12, padx=12)
        optsCard.pack(fill="x", pady=(0, 16))
        tk.Label(
            optsCard,
            text="OPTIONS",
            font=(fontFamily, 8, "bold"),
            bg=bgCard,
            fg=accentColor,
        ).pack(anchor="w")

        self.enhanceVar     = tk.BooleanVar(value=True)
        self.detectFmtVar   = tk.BooleanVar(value=True)
        self.detectAlignVar = tk.BooleanVar(value=True)
        self.makeCheckbox(optsCard, "Enhance image before OCR", self.enhanceVar)
        self.makeCheckbox(optsCard, "Detect formatting (bold/italic)", self.detectFmtVar)
        self.makeCheckbox(optsCard, "Detect paragraph alignment", self.detectAlignVar)

        outCard = tk.Frame(rightPanel, bg=bgCard, pady=12, padx=12)
        outCard.pack(fill="x", pady=(0, 16))
        tk.Label(
            outCard,
            text="OUTPUT FOLDER",
            font=(fontFamily, 8, "bold"),
            bg=bgCard,
            fg=accentColor,
        ).pack(anchor="w")
        self.outputLabel = tk.Label(
            outCard,
            text="Same folder as input image",
            font=(fontFamily, 9),
            bg=bgCard,
            fg=textMuted,
            wraplength=230,
            justify="left",
        )
        self.outputLabel.pack(anchor="w", pady=(4, 0))
        self.makeButton(outCard, "Change Folder", self.browseOutput, isPrimary=False, isSmall=True).pack(anchor="w", pady=(6, 0))
        self.outputDir = None

        self.convertBtn = self.makeButton(rightPanel, "Convert to Word", self.startConversion, isPrimary=True)
        self.convertBtn.pack(fill="x", pady=(4, 12))

        statusCard = tk.Frame(rightPanel, bg=bgCard, pady=10, padx=12)
        statusCard.pack(fill="x")
        tk.Label(
            statusCard,
            text="STATUS",
            font=(fontFamily, 8, "bold"),
            bg=bgCard,
            fg=accentColor,
        ).pack(anchor="w")

        self.statusLabel = tk.Label(
            statusCard,
            text="Ready",
            font=(fontFamily, 9),
            bg=bgCard,
            fg=successColor,
            wraplength=230,
            justify="left",
        )
        self.statusLabel.pack(anchor="w", pady=(4, 6))

        self.progressBar = ttk.Progressbar(statusCard, mode="indeterminate", length=230)
        self.styleProgressbar()
        self.progressBar.pack(anchor="w")

        footerFrame = tk.Frame(self, bg=bgCard2, height=36)
        footerFrame.pack(fill="x", side="bottom")
        footerFrame.pack_propagate(False)
        tk.Label(
            footerFrame,
            text="Image to Word Converter  |  PPIT Project  |  Tesseract OCR + python-docx",
            font=(fontFamily, 8),
            bg=bgCard2,
            fg=textMuted,
        ).pack(side="left", padx=16, pady=8)

    def makeButton(self, parent, labelText, commandFn, isPrimary=True, isSmall=False):
        fontSize = 9 if isSmall else 11
        btnWidget = tk.Button(
            parent,
            text=labelText,
            command=commandFn,
            font=(fontFamily, fontSize, "bold"),
            bg=accentColor if isPrimary else accent2,
            fg=textPrimary,
            activebackground=btnHover if isPrimary else "#1a3a6e",
            activeforeground=textPrimary,
            relief="flat",
            cursor="hand2",
            pady=6 if isSmall else 10,
            padx=8,
            bd=0,
        )
        btnWidget.bind("<Enter>", lambda e: btnWidget.config(bg=btnHover if isPrimary else "#1a3a6e"))
        btnWidget.bind("<Leave>", lambda e: btnWidget.config(bg=accentColor if isPrimary else accent2))
        return btnWidget

    def makeCheckbox(self, parent, labelText, varObj):
        cbWidget = tk.Checkbutton(
            parent,
            text=labelText,
            variable=varObj,
            font=(fontFamily, 9),
            bg=bgCard,
            fg=textPrimary,
            selectcolor=accent2,
            activebackground=bgCard,
            activeforeground=textPrimary,
            anchor="w",
            padx=0,
        )
        cbWidget.pack(anchor="w", pady=2)
        return cbWidget

    def styleProgressbar(self):
        pbStyle = ttk.Style(self)
        pbStyle.theme_use("clam")
        pbStyle.configure(
            "TProgressbar",
            troughcolor=bgCard2,
            background=accentColor,
            bordercolor=bgCard2,
            lightcolor=accentColor,
            darkcolor=accentColor,
        )

    def onCanvasResize(self, event):
        if self.imagePath:
            self.updatePreview(self.imagePath)
        else:
            canvasW, canvasH = event.width, event.height
            self.previewCanvas.coords(self.placeholderTextId, canvasW // 2, canvasH // 2)

    def browseImage(self):
        selectedPath = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
                ("All files", "*.*"),
            ],
        )
        if not selectedPath:
            return
        self.imagePath = selectedPath
        self.fileLabel.config(text=os.path.basename(selectedPath), fg=textPrimary)
        self.updatePreview(selectedPath)
        self.setStatus("Image loaded. Ready to convert.", successColor)

    def browseOutput(self):
        selectedDir = filedialog.askdirectory(title="Select Output Folder")
        if selectedDir:
            self.outputDir = selectedDir
            self.outputLabel.config(text=selectedDir, fg=textPrimary)

    def updatePreview(self, imgPath: str):
        try:
            openedImg = Image.open(imgPath)
            canvasW = max(self.previewCanvas.winfo_width(), 100)
            canvasH = max(self.previewCanvas.winfo_height(), 100)
            openedImg.thumbnail((canvasW - 20, canvasH - 20), Image.LANCZOS)
            self.tkImg = ImageTk.PhotoImage(openedImg)
            self.previewCanvas.delete("all")
            self.previewCanvas.create_image(
                canvasW // 2, canvasH // 2, image=self.tkImg, anchor="center"
            )
        except Exception as excMsg:
            self.setStatus(f"Preview error: {excMsg}", errorColor)

    def startConversion(self):
        if self.isProcessing:
            return
        if not self.imagePath:
            messagebox.showwarning("No Image", "Please select an image first.")
            return
        self.isProcessing = True
        self.convertBtn.config(state="disabled", text="Processing...")
        self.progressBar.start(12)
        self.setStatus("Processing image...", textMuted)
        threading.Thread(target=self.convertWorker, daemon=True).start()

    def convertWorker(self):
        try:
            ocrResult = runOcr(self.imagePath)

            baseName  = os.path.splitext(os.path.basename(self.imagePath))[0]
            outDir    = self.outputDir or os.path.dirname(self.imagePath)
            outputPath = os.path.join(outDir, f"{baseName}_converted.docx")

            buildDocx(ocrResult, outputPath)

            self.after(0, self.onSuccess, outputPath)
        except Exception as excMsg:
            self.after(0, self.onError, str(excMsg))

    def onSuccess(self, outputPath: str):
        self.isProcessing = False
        self.progressBar.stop()
        self.convertBtn.config(state="normal", text="Convert to Word")
        self.setStatus(f"Saved: {os.path.basename(outputPath)}", successColor)
        if messagebox.askyesno(
            "Conversion Complete",
            f"Word document saved:\n{outputPath}\n\nOpen it now?",
        ):
            os.startfile(outputPath)

    def onError(self, errMsg: str):
        self.isProcessing = False
        self.progressBar.stop()
        self.convertBtn.config(state="normal", text="Convert to Word")
        self.setStatus(f"Error: {errMsg}", errorColor)
        messagebox.showerror("Conversion Failed", f"An error occurred:\n\n{errMsg}")

    def setStatus(self, statusMsg: str, statusColor: str = textPrimary):
        self.statusLabel.config(text=statusMsg, fg=statusColor)


if __name__ == "__main__":
    appInstance = ImageToWordApp()
    appInstance.mainloop()
