import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk
import pywinstyles

baseDir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, baseDir)

from src.ocr_engine       import runOcr
from src.document_builder import buildDocx

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

glassTint      = "#1c1c28"
cardTint       = "#282a36" 
accentLavender = "#b4b4f3"
accentHover    = "#9292d0"
textPrimary    = "#e6e6fa"
textMuted      = "#a8a8c0"
successColor   = "#6af0a3"
errorColor     = "#ff7a85"
fontFamily     = "Segoe UI"


class ImageToWordApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Image to Word Converter")
        self.geometry("1000x750")
        self.minsize(860, 660)

        try:
            pywinstyles.apply_style(self, "acrylic")
        except Exception:
            pass

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
        headerFrame = ctk.CTkFrame(self, height=75, fg_color="transparent", corner_radius=0)
        headerFrame.pack(fill="x", side="top")
        headerFrame.pack_propagate(False)

        ctk.CTkLabel(
            headerFrame,
            text="Image to Word Converter",
            font=ctk.CTkFont(family=fontFamily, size=22, weight="bold"),
            text_color=textPrimary,
        ).pack(side="left", padx=30, pady=20)

        ctk.CTkLabel(
            headerFrame,
            text="Powered by Tesseract OCR",
            font=ctk.CTkFont(family=fontFamily, size=13),
            text_color=textMuted,
        ).pack(side="right", padx=30, pady=20)

        ctk.CTkFrame(self, height=2, fg_color=accentLavender).pack(fill="x")

        contentFrame = ctk.CTkFrame(self, fg_color="transparent")
        contentFrame.pack(fill="both", expand=True, padx=25, pady=25)

        leftPanel = ctk.CTkFrame(contentFrame, fg_color=cardTint, corner_radius=15)
        leftPanel.pack(side="left", fill="both", expand=True, padx=(0, 20))
        
        try:
            pywinstyles.set_opacity(leftPanel, value=0.85)
        except Exception:
            pass

        ctk.CTkLabel(
            leftPanel,
            text="INPUT IMAGE",
            font=ctk.CTkFont(family=fontFamily, size=12, weight="bold"),
            text_color=accentLavender,
        ).pack(anchor="nw", padx=20, pady=(15, 5))

        self.previewCanvas = tk.Canvas(
            leftPanel,
            bg="#1e1e2e",
            highlightthickness=0,
            cursor="hand2",
        )
        self.previewCanvas.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.previewCanvas.bind("<Button-1>", lambda e: self.browseImage())

        self.placeholderTextId = self.previewCanvas.create_text(
            200, 200,
            text="Click to select an image\n\n(JPG / PNG / JPEG)",
            fill=textMuted,
            font=(fontFamily, 14),
            justify="center",
            tags="placeholder",
        )
        self.previewCanvas.bind("<Configure>", self.onCanvasResize)

        rightPanel = ctk.CTkFrame(contentFrame, width=300, fg_color="transparent")
        rightPanel.pack(side="right", fill="y")
        rightPanel.pack_propagate(False)

        self.browseBtn = ctk.CTkButton(
            rightPanel, 
            text="Browse Image", 
            command=self.browseImage,
            fg_color="transparent",
            hover_color="#3a3c54",
            border_width=1.5,
            border_color=accentLavender,
            text_color=accentLavender,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(family=fontFamily, size=14, weight="bold")
        )
        self.browseBtn.pack(fill="x", pady=(0, 18))

        fileCard = self.makeCard(rightPanel, "SELECTED FILE")
        self.fileLabel = ctk.CTkLabel(
            fileCard,
            text="No file selected",
            font=ctk.CTkFont(family=fontFamily, size=13),
            text_color=textMuted,
            wraplength=250,
            justify="left"
        )
        self.fileLabel.pack(anchor="w", pady=(5, 15), padx=15)

        optsCard = self.makeCard(rightPanel, "OPTIONS")
        self.enhanceVar     = ctk.BooleanVar(value=True)
        self.detectFmtVar   = ctk.BooleanVar(value=True)
        self.detectAlignVar = ctk.BooleanVar(value=True)
        
        self.makeCheckbox(optsCard, "Enhance image before OCR", self.enhanceVar)
        self.makeCheckbox(optsCard, "Detect formatting (bold/italic)", self.detectFmtVar)
        self.makeCheckbox(optsCard, "Detect paragraph alignment", self.detectAlignVar)
        ctk.CTkFrame(optsCard, height=10, fg_color="transparent").pack() 

        outCard = self.makeCard(rightPanel, "OUTPUT FOLDER")
        self.outputLabel = ctk.CTkLabel(
            outCard,
            text="Same folder as input image",
            font=ctk.CTkFont(family=fontFamily, size=13),
            text_color=textMuted,
            wraplength=250,
            justify="left"
        )
        self.outputLabel.pack(anchor="w", pady=(5, 5), padx=15)
        
        ctk.CTkButton(
            outCard, 
            text="Change Folder", 
            command=self.browseOutput,
            fg_color="transparent",
            hover_color="#3a3c54",
            border_width=1,
            border_color=accentLavender,
            text_color=accentLavender,
            height=30,
            corner_radius=8,
            font=ctk.CTkFont(family=fontFamily, size=12, weight="bold")
        ).pack(anchor="w", padx=15, pady=(0, 15))
        self.outputDir = None

        self.convertBtn = ctk.CTkButton(
            rightPanel, 
            text="Convert to Word", 
            command=self.startConversion,
            fg_color=accentLavender,
            hover_color=accentHover,
            text_color="#1a1a2e",
            height=45,
            corner_radius=10,
            font=ctk.CTkFont(family=fontFamily, size=15, weight="bold")
        )
        self.convertBtn.pack(fill="x", pady=(5, 18))

        statusCard = self.makeCard(rightPanel, "STATUS")
        self.statusLabel = ctk.CTkLabel(
            statusCard,
            text="Ready",
            font=ctk.CTkFont(family=fontFamily, size=13),
            text_color=successColor,
            wraplength=250,
            justify="left"
        )
        self.statusLabel.pack(anchor="w", pady=(5, 5), padx=15)

        self.progressBar = ctk.CTkProgressBar(statusCard, progress_color=accentLavender)
        self.progressBar.pack(fill="x", padx=15, pady=(0, 15))
        self.progressBar.set(0)

        footerFrame = ctk.CTkFrame(self, height=40, fg_color="transparent")
        footerFrame.pack(fill="x", side="bottom")
        footerFrame.pack_propagate(False)
        ctk.CTkLabel(
            footerFrame,
            text="Image to Word Converter  |  Agentic System MVP  |  Tesseract OCR + python-docx",
            font=ctk.CTkFont(family=fontFamily, size=12),
            text_color=textMuted,
        ).pack(side="left", padx=20, pady=10)

    def makeCard(self, parent, titleText):
        cardWidget = ctk.CTkFrame(parent, fg_color=cardTint, corner_radius=12)
        cardWidget.pack(fill="x", pady=(0, 18))
        try:
            pywinstyles.set_opacity(cardWidget, value=0.85)
        except Exception:
            pass
        
        ctk.CTkLabel(
            cardWidget,
            text=titleText,
            font=ctk.CTkFont(family=fontFamily, size=12, weight="bold"),
            text_color=accentLavender,
        ).pack(anchor="w", padx=15, pady=(12, 0))
        return cardWidget

    def makeCheckbox(self, parent, labelText, varObj):
        cbWidget = ctk.CTkCheckBox(
            parent,
            text=labelText,
            variable=varObj,
            font=ctk.CTkFont(family=fontFamily, size=13),
            text_color=textPrimary,
            fg_color=accentLavender,
            hover_color=accentHover,
            border_color=accentLavender,
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=6
        )
        cbWidget.pack(anchor="w", padx=15, pady=6)
        return cbWidget

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
        self.fileLabel.configure(text=os.path.basename(selectedPath), text_color=textPrimary)
        self.updatePreview(selectedPath)
        self.setStatus("Image loaded. Ready to convert.", successColor)

    def browseOutput(self):
        selectedDir = filedialog.askdirectory(title="Select Output Folder")
        if selectedDir:
            self.outputDir = selectedDir
            self.outputLabel.configure(text=selectedDir, text_color=textPrimary)

    def updatePreview(self, imgPath: str):
        try:
            openedImg = Image.open(imgPath)
            canvasW = max(self.previewCanvas.winfo_width(), 100)
            canvasH = max(self.previewCanvas.winfo_height(), 100)
            openedImg.thumbnail((canvasW - 30, canvasH - 30), Image.LANCZOS)
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
        self.convertBtn.configure(state="disabled", text="Processing...")
        self.progressBar.start()
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
        self.progressBar.set(1)
        self.convertBtn.configure(state="normal", text="Convert to Word")
        self.setStatus(f"Saved: {os.path.basename(outputPath)}", successColor)
        if messagebox.askyesno(
            "Conversion Complete",
            f"Word document saved:\n{outputPath}\n\nOpen it now?",
        ):
            os.startfile(outputPath)

    def onError(self, errMsg: str):
        self.isProcessing = False
        self.progressBar.stop()
        self.progressBar.set(0)
        self.convertBtn.configure(state="normal", text="Convert to Word")
        self.setStatus(f"Error: {errMsg}", errorColor)
        messagebox.showerror("Conversion Failed", f"An error occurred:\n\n{errMsg}")

    def setStatus(self, statusMsg: str, statusColor: str = textPrimary):
        self.statusLabel.configure(text=statusMsg, text_color=statusColor)


if __name__ == "__main__":
    appInstance = ImageToWordApp()
    appInstance.mainloop()
