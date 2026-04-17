import os
import sys
import threading
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk
import pywinstyles

baseDir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, baseDir)

from src.ocr_engine       import runOcr
from src.document_builder import buildDocx

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# iOS 26 Futuristic Light/Glass Theme Constants
glassTint      = "#f2f2f7"   # iOS System Grouped Background (Light)
cardTint       = "#ffffff"   # Pure white for cards, highly translucent
accentColor    = "#af52de"   # iOS System Purple
accentHover    = "#c86efd"
textPrimary    = "#000000"   # Black text for HD clarity
textMuted      = "#5c5c60"   # Darker iOS System Gray for better visibility
successColor   = "#34c759"   # iOS System Green
errorColor     = "#ff3b30"   # iOS System Red
fontFamily     = "Helvetica" # Closest universal fallback to SF Pro
cardRadius     = 20          # Heavy squircle rounding typical of modern iOS

settingsPath   = os.path.join(baseDir, "settings.json")
memoryPath     = os.path.join(baseDir, "user_memory.json")

class AgentChatbot(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Agent Assistant")
        self.geometry("400x550")
        self.configure(fg_color=glassTint)
        self.attributes("-topmost", True)

        try:
            pywinstyles.apply_style(self, "acrylic")
        except Exception:
            pass

        self.chatHistory = ctk.CTkTextbox(
            self,
            fg_color=cardTint,
            text_color=textPrimary,
            font=ctk.CTkFont(family=fontFamily, size=13),
            wrap="word",
            state="disabled",
            corner_radius=15
        )
        self.chatHistory.pack(fill="both", expand=True, padx=20, pady=(20, 15))

        inputFrame = ctk.CTkFrame(self, fg_color="transparent")
        inputFrame.pack(fill="x", padx=20, pady=(0, 20))

        self.queryInput = ctk.CTkEntry(
            inputFrame,
            placeholder_text="Ask me anything...",
            fg_color=cardTint,
            text_color=textPrimary,
            border_width=0,
            corner_radius=18,
            font=ctk.CTkFont(family=fontFamily, size=13),
            height=40
        )
        self.queryInput.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.queryInput.bind("<Return>", lambda e: self.processQuery())

        self.sendBtn = ctk.CTkButton(
            inputFrame,
            text="↑",
            width=40,
            height=40,
            corner_radius=20,
            fg_color=accentColor,
            hover_color=accentHover,
            text_color="#ffffff",
            font=ctk.CTkFont(family=fontFamily, size=18, weight="bold"),
            command=self.processQuery
        )
        self.sendBtn.pack(side="right")

        self.appendMessage("Agent", "Hello! I am your AI Assistant. You can ask me about local mode, clearing memory, or how this converter works.")

    def appendMessage(self, sender: str, msg: str):
        self.chatHistory.configure(state="normal")
        self.chatHistory.insert("end", f"{sender}:\n{msg}\n\n")
        self.chatHistory.configure(state="disabled")
        self.chatHistory.see("end")

    def processQuery(self):
        userText = self.queryInput.get().strip()
        if not userText:
            return
        
        self.queryInput.delete(0, "end")
        self.appendMessage("You", userText)
        
        userTextLower = userText.lower()
        if "local" in userTextLower or "privacy" in userTextLower:
            replyText = "When 'Strict Local Mode' is enabled, I use local Tesseract OCR. No data is sent to cloud LLM APIs, ensuring total privacy."
        elif "clear" in userTextLower or "memory" in userTextLower:
            replyText = "You can clear my stored contextual memory by clicking the 'Clear Agent Memory' button in the main window. This deletes user_memory.json."
        elif "how" in userTextLower or "work" in userTextLower:
            replyText = "I preprocess your image, run OCR to detect text and spatial gaps, apply heuristics for formatting, and output a structured Word document."
        elif "hello" in userTextLower or "hi" in userTextLower:
            replyText = "Hello! Ready to convert some images?"
        else:
            replyText = "I'm a rule-based agent for now. I can help answer queries regarding privacy, local mode, and clearing memory."
            
        self.after(500, lambda: self.appendMessage("Agent", replyText))


class ImageToWordApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Image to Word Converter")
        self.geometry("1050x850")
        self.minsize(900, 750)
        self.configure(fg_color=glassTint)

        try:
            pywinstyles.apply_style(self, "acrylic")
        except Exception:
            pass

        self.imagePath = None
        self.tkImg     = None
        self.isProcessing = False
        self.chatbotWindow = None

        self.checkTermsAndConditions()
        self.buildUi()
        self.checkTesseract()

    def checkTermsAndConditions(self):
        termsAccepted = False
        if os.path.exists(settingsPath):
            try:
                with open(settingsPath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    termsAccepted = data.get("acceptedTerms", False)
            except Exception:
                pass

        if not termsAccepted:
            self.showTermsModal()

    def showTermsModal(self):
        modalWindow = ctk.CTkToplevel(self)
        modalWindow.title("Terms & Privacy")
        modalWindow.geometry("550x500")
        modalWindow.configure(fg_color=glassTint)
        modalWindow.attributes("-topmost", True)
        modalWindow.grab_set()

        try: pywinstyles.apply_style(modalWindow, "acrylic")
        except: pass

        ctk.CTkLabel(
            modalWindow,
            text="Privacy & Terms of Use",
            font=ctk.CTkFont(family=fontFamily, size=22, weight="bold"),
            text_color=accentColor
        ).pack(pady=(30, 10))

        termsText = (
            "By using this Agentic System, you agree to the following:\n\n"
            "1. PRIVACY: Your data remains yours. The 'Strict Local Mode'\n"
            "   ensures your images are processed entirely offline.\n"
            "2. MEMORY: The agent learns your handwriting style over time.\n"
            "   You can delete this memory at any time via the GUI.\n"
            "3. INTEGRITY: Do not use this tool to infringe on copyrights."
        )
        ctk.CTkLabel(
            modalWindow,
            text=termsText,
            font=ctk.CTkFont(family=fontFamily, size=14),
            text_color=textPrimary,
            justify="left"
        ).pack(padx=40, pady=10)

        cbVar1 = ctk.BooleanVar(value=False)
        cbVar2 = ctk.BooleanVar(value=False)

        def checkAcceptState(*args):
            if cbVar1.get() and cbVar2.get():
                acceptBtn.configure(state="normal", fg_color=accentColor)
            else:
                acceptBtn.configure(state="disabled", fg_color="#d1d1d6")

        cbVar1.trace_add("write", checkAcceptState)
        cbVar2.trace_add("write", checkAcceptState)

        ctk.CTkCheckBox(modalWindow, text="I agree to the offline Privacy processing.", variable=cbVar1, font=ctk.CTkFont(family=fontFamily, size=13, weight="bold"), text_color=textPrimary, fg_color=accentColor, hover_color=accentHover).pack(anchor="w", padx=45, pady=(15, 5))
        ctk.CTkCheckBox(modalWindow, text="I understand the Agent Memory features.", variable=cbVar2, font=ctk.CTkFont(family=fontFamily, size=13, weight="bold"), text_color=textPrimary, fg_color=accentColor, hover_color=accentHover).pack(anchor="w", padx=45, pady=5)

        def acceptTerms():
            with open(settingsPath, "w", encoding="utf-8") as f:
                json.dump({"acceptedTerms": True}, f)
            modalWindow.destroy()

        def declineTerms():
            sys.exit(0)

        btnFrame = ctk.CTkFrame(modalWindow, fg_color="transparent")
        btnFrame.pack(pady=25)

        ctk.CTkButton(
            btnFrame, text="Decline & Exit", command=declineTerms,
            fg_color="transparent", text_color=errorColor,
            font=ctk.CTkFont(family=fontFamily, size=15, weight="bold")
        ).pack(side="left", padx=15)
        
        acceptBtn = ctk.CTkButton(
            btnFrame, text="I Accept", command=acceptTerms,
            fg_color="#d1d1d6", text_color="#ffffff", hover_color=accentHover, state="disabled",
            corner_radius=18, font=ctk.CTkFont(family=fontFamily, size=15, weight="bold")
        )
        acceptBtn.pack(side="right", padx=15)
        
        self.wait_window(modalWindow)

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
        headerFrame = ctk.CTkFrame(self, height=80, fg_color="transparent", corner_radius=0)
        headerFrame.pack(fill="x", side="top")
        headerFrame.pack_propagate(False)

        ctk.CTkLabel(
            headerFrame,
            text="Image to Word",
            font=ctk.CTkFont(family=fontFamily, size=28, weight="bold"),
            text_color=textPrimary,
        ).pack(side="left", padx=35, pady=25)

        self.chatBtn = ctk.CTkButton(
            headerFrame,
            text="Ask Agent",
            command=self.openChatbot,
            fg_color=cardTint,
            hover_color="#2c2c2e",
            text_color=accentColor,
            corner_radius=20,
            width=110,
            height=36,
            font=ctk.CTkFont(family=fontFamily, size=13, weight="bold")
        )
        self.chatBtn.pack(side="right", padx=35, pady=22)

        contentFrame = ctk.CTkFrame(self, fg_color="transparent")
        contentFrame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        leftPanel = ctk.CTkFrame(contentFrame, fg_color=cardTint, corner_radius=cardRadius)
        leftPanel.pack(side="left", fill="both", expand=True, padx=(0, 25))

        self.previewCanvas = tk.Canvas(
            leftPanel,
            bg="#f2f2f7",
            highlightthickness=0,
            cursor="hand2",
        )
        self.previewCanvas.pack(fill="both", expand=True, padx=20, pady=20)
        self.previewCanvas.bind("<Button-1>", lambda e: self.browseImage())

        self.placeholderTextId = self.previewCanvas.create_text(
            200, 200,
            text="Tap to select an image",
            fill=textMuted,
            font=(fontFamily, 16),
            justify="center",
            tags="placeholder",
        )
        self.previewCanvas.bind("<Configure>", self.onCanvasResize)

        rightPanel = ctk.CTkScrollableFrame(contentFrame, width=340, fg_color="transparent")
        rightPanel.pack(side="right", fill="y")

        self.browseBtn = ctk.CTkButton(
            rightPanel, 
            text="Choose Image...", 
            command=self.browseImage,
            fg_color=cardTint,
            hover_color="#2c2c2e",
            text_color=accentColor,
            height=45,
            corner_radius=cardRadius,
            font=ctk.CTkFont(family=fontFamily, size=15, weight="bold")
        )
        self.browseBtn.pack(fill="x", pady=(0, 20))

        fileCard = self.makeCard(rightPanel, "SELECTED FILE")
        self.fileLabel = ctk.CTkLabel(
            fileCard,
            text="None",
            font=ctk.CTkFont(family=fontFamily, size=14),
            text_color=textMuted,
            wraplength=280,
            justify="left"
        )
        self.fileLabel.pack(anchor="w", pady=(5, 15), padx=20)

        optsCard = self.makeCard(rightPanel, "PROCESSING OPTIONS")
        self.enhanceVar     = ctk.BooleanVar(value=True)
        self.detectFmtVar   = ctk.BooleanVar(value=True)
        self.detectAlignVar = ctk.BooleanVar(value=True)
        self.localModeVar   = ctk.BooleanVar(value=True)
        
        self.makeSwitch(optsCard, "Enhance image before OCR", self.enhanceVar)
        self.makeSwitch(optsCard, "Detect formatting", self.detectFmtVar)
        self.makeSwitch(optsCard, "Detect alignment", self.detectAlignVar)
        self.makeSwitch(optsCard, "Strict Local Mode", self.localModeVar)
        ctk.CTkFrame(optsCard, height=10, fg_color="transparent").pack() 

        privacyCard = self.makeCard(rightPanel, "PRIVACY & MEMORY")
        ctk.CTkButton(
            privacyCard, text="View Terms & Conditions", command=self.showTermsModal,
            fg_color="transparent", text_color=textMuted, hover_color=cardTint,
            height=30, anchor="w", font=ctk.CTkFont(family=fontFamily, size=13)
        ).pack(anchor="w", fill="x", padx=10, pady=(5, 5))
        
        ctk.CTkButton(
            privacyCard, text="Clear Agent Memory", command=self.clearMemory,
            fg_color="transparent", text_color=errorColor, hover_color=cardTint,
            height=30, anchor="w", font=ctk.CTkFont(family=fontFamily, size=13)
        ).pack(anchor="w", fill="x", padx=10, pady=(0, 10))

        outCard = self.makeCard(rightPanel, "OUTPUT FOLDER")
        self.outputLabel = ctk.CTkLabel(
            outCard,
            text="Same as input image",
            font=ctk.CTkFont(family=fontFamily, size=14),
            text_color=textMuted,
            wraplength=280,
            justify="left"
        )
        self.outputLabel.pack(anchor="w", pady=(5, 10), padx=20)
        
        ctk.CTkButton(
            outCard, 
            text="Change Folder...", 
            command=self.browseOutput,
            fg_color="transparent",
            hover_color="#2c2c2e",
            text_color=accentColor,
            height=35,
            corner_radius=18,
            font=ctk.CTkFont(family=fontFamily, size=13, weight="bold")
        ).pack(anchor="w", padx=15, pady=(0, 15))
        self.outputDir = None

        self.convertBtn = ctk.CTkButton(
            rightPanel, 
            text="Convert to Word", 
            command=self.startConversion,
            fg_color=accentColor,
            hover_color=accentHover,
            text_color="#ffffff",
            height=50,
            corner_radius=25, # Pill shaped
            font=ctk.CTkFont(family=fontFamily, size=16, weight="bold")
        )
        self.convertBtn.pack(fill="x", pady=(10, 20))

        statusCard = self.makeCard(rightPanel, "STATUS")
        self.statusLabel = ctk.CTkLabel(
            statusCard,
            text="Ready to process",
            font=ctk.CTkFont(family=fontFamily, size=14),
            text_color=successColor,
            wraplength=280,
            justify="left"
        )
        self.statusLabel.pack(anchor="w", pady=(5, 10), padx=20)

        self.progressBar = ctk.CTkProgressBar(statusCard, progress_color=accentColor, fg_color="#e5e5ea", height=6, corner_radius=3)
        self.progressBar.pack(fill="x", padx=20, pady=(0, 20))
        self.progressBar.set(0)

        footerFrame = ctk.CTkFrame(self, height=45, fg_color="transparent")
        footerFrame.pack(fill="x", side="bottom")
        footerFrame.pack_propagate(False)
        ctk.CTkLabel(
            footerFrame,
            text="Agentic System MVP  •  Tesseract OCR",
            font=ctk.CTkFont(family=fontFamily, size=12),
            text_color=textMuted,
        ).pack(side="left", padx=35, pady=12)

    def makeCard(self, parent, titleText):
        cardWidget = ctk.CTkFrame(parent, fg_color=cardTint, corner_radius=cardRadius)
        cardWidget.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            cardWidget,
            text=titleText,
            font=ctk.CTkFont(family=fontFamily, size=11, weight="bold"),
            text_color=textMuted,
        ).pack(anchor="w", padx=20, pady=(15, 0))
        return cardWidget

    def makeSwitch(self, parent, labelText, varObj):
        switchWidget = ctk.CTkSwitch(
            parent,
            text=labelText,
            variable=varObj,
            font=ctk.CTkFont(family=fontFamily, size=14),
            text_color=textPrimary,
            progress_color=accentColor,
            button_color="#ffffff",
            button_hover_color="#f0f0f0",
            switch_width=45,
            switch_height=24
        )
        switchWidget.pack(anchor="w", padx=20, pady=8)
        return switchWidget

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
        self.setStatus("Image loaded", textPrimary)

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
            openedImg.thumbnail((canvasW - 40, canvasH - 40), Image.LANCZOS)
            self.tkImg = ImageTk.PhotoImage(openedImg)
            self.previewCanvas.delete("all")
            self.previewCanvas.create_image(
                canvasW // 2, canvasH // 2, image=self.tkImg, anchor="center"
            )
        except Exception as excMsg:
            self.setStatus(f"Preview error: {excMsg}", errorColor)

    def openChatbot(self):
        if self.chatbotWindow is None or not self.chatbotWindow.winfo_exists():
            self.chatbotWindow = AgentChatbot(self)
        else:
            self.chatbotWindow.focus()

    def clearMemory(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear your stored OCR profiles and reset settings?"):
            if os.path.exists(memoryPath):
                os.remove(memoryPath)
            if os.path.exists(settingsPath):
                os.remove(settingsPath)
            self.setStatus("Agent memory cleared", successColor)

    def startConversion(self):
        if self.isProcessing:
            return
        if not self.imagePath:
            messagebox.showwarning("No Image", "Please select an image first.")
            return
        self.isProcessing = True
        self.convertBtn.configure(state="disabled", text="Processing...")
        self.progressBar.start()
        
        modeText = "Local Mode" if self.localModeVar.get() else "Cloud AI"
        self.setStatus(f"Processing in {modeText}...", textMuted)
        
        threading.Thread(target=self.convertWorker, daemon=True).start()

    def convertWorker(self):
        try:
            ocrResult = runOcr(self.imagePath, localMode=self.localModeVar.get())

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
        self.setStatus("Conversion failed", errorColor)
        messagebox.showerror("Error", f"An error occurred:\n\n{errMsg}")

    def setStatus(self, statusMsg: str, statusColor: str = textPrimary):
        self.statusLabel.configure(text=statusMsg, text_color=statusColor)


if __name__ == "__main__":
    appInstance = ImageToWordApp()
    appInstance.mainloop()
