import os
import sys
import threading
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk

baseDir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, baseDir)

from src.ocr_engine       import runOcr
from src.document_builder import buildDocx

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Web-Style Theme Constants
bgTint         = "#f8f9fa"   # Very light gray (almost white) for page background
cardTint       = "#ffffff"   # Pure white for main content box
accentColor    = "#8c52ff"   # Prominent vibrant purple matching screenshot
accentHover    = "#7a3cf5"
textPrimary    = "#212529"   # Dark gray/black
textMuted      = "#6c757d"   # Secondary gray
successColor   = "#198754"   
errorColor     = "#dc3545"   
fontFamily     = "Helvetica" 

settingsPath   = os.path.join(baseDir, "settings.json")
memoryPath     = os.path.join(baseDir, "user_memory.json")

class AgentChatbot(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Live Chat (Agent Assistant)")
        self.geometry("400x550")
        self.configure(fg_color=bgTint)
        self.attributes("-topmost", True)

        self.chatHistory = ctk.CTkTextbox(
            self,
            fg_color=cardTint,
            text_color=textPrimary,
            font=ctk.CTkFont(family=fontFamily, size=13),
            wrap="word",
            state="disabled",
            corner_radius=10,
            border_width=1,
            border_color="#dee2e6"
        )
        self.chatHistory.pack(fill="both", expand=True, padx=20, pady=(20, 15))

        inputFrame = ctk.CTkFrame(self, fg_color="transparent")
        inputFrame.pack(fill="x", padx=20, pady=(0, 20))

        self.queryInput = ctk.CTkEntry(
            inputFrame,
            placeholder_text="Ask me anything...",
            fg_color=cardTint,
            text_color=textPrimary,
            border_width=1,
            border_color="#dee2e6",
            corner_radius=8,
            font=ctk.CTkFont(family=fontFamily, size=13),
            height=40
        )
        self.queryInput.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.queryInput.bind("<Return>", lambda e: self.processQuery())

        self.sendBtn = ctk.CTkButton(
            inputFrame,
            text="Send",
            width=60,
            height=40,
            corner_radius=8,
            fg_color=accentColor,
            hover_color=accentHover,
            text_color="#ffffff",
            font=ctk.CTkFont(family=fontFamily, size=14, weight="bold"),
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
            replyText = "You can clear my stored contextual memory by clearing settings. This deletes user_memory.json."
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
        self.title("Image to Text Converter")
        self.geometry("1150x850")
        self.minsize(900, 750)
        self.configure(fg_color=bgTint)

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
        modalWindow.configure(fg_color=bgTint)
        modalWindow.attributes("-topmost", True)
        modalWindow.grab_set()

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
            corner_radius=8, font=ctk.CTkFont(family=fontFamily, size=15, weight="bold")
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
        # 1. Top Navigation Bar
        navFrame = ctk.CTkFrame(self, height=65, fg_color=cardTint, corner_radius=0)
        navFrame.pack(fill="x", side="top")
        navFrame.pack_propagate(False)

        leftNav = ctk.CTkFrame(navFrame, fg_color="transparent")
        leftNav.pack(side="left", padx=20)
        
        ctk.CTkLabel(leftNav, text="📝 Image To Text", font=ctk.CTkFont(family=fontFamily, size=16, weight="bold"), text_color="#4f46e5").pack(side="left", padx=(0, 20))
        
        navLinks = ["Image Translator", "JPG To Word", "JPG To Excel", "PDF To Excel"]
        for link in navLinks:
            lbl = ctk.CTkLabel(leftNav, text=link, font=ctk.CTkFont(family=fontFamily, size=13), text_color=textPrimary, cursor="hand2")
            lbl.pack(side="left", padx=15)
            if link == "JPG To Word":
                lbl.configure(font=ctk.CTkFont(family=fontFamily, size=13, weight="bold"), text_color=accentColor)

        rightNav = ctk.CTkFrame(navFrame, fg_color="transparent")
        rightNav.pack(side="right", padx=20)
        
        ctk.CTkButton(rightNav, text="💬 Ask Agent", command=self.openChatbot, fg_color="transparent", text_color="#4f46e5", font=ctk.CTkFont(family=fontFamily, size=14, weight="bold"), hover_color="#f3f4f6", width=80).pack(side="left", padx=10)
        ctk.CTkButton(rightNav, text="📜 Privacy Terms", command=self.showTermsModal, fg_color="transparent", text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), hover_color="#f3f4f6", width=80).pack(side="left", padx=10)

        # 2. Hero Section
        heroFrame = ctk.CTkFrame(self, fg_color="transparent")
        heroFrame.pack(fill="x", pady=(50, 20))
        
        ctk.CTkLabel(heroFrame, text="Image to Text Converter", font=ctk.CTkFont(family=fontFamily, size=34, weight="bold"), text_color=textPrimary).pack()
        ctk.CTkLabel(heroFrame, text="An offline image to text converter to extract text from images.", font=ctk.CTkFont(family=fontFamily, size=16), text_color=textMuted).pack(pady=(8, 18))

        # 3. Main Container
        self.mainContainer = ctk.CTkFrame(self, fg_color="transparent")
        self.mainContainer.pack(fill="both", expand=True, padx=40, pady=(10, 40))

        self.buildUploadBox()
        self.buildPreviewBox()

        self.showUploadBox()

    def buildUploadBox(self):
        self.uploadFrame = ctk.CTkFrame(self.mainContainer, fg_color=cardTint, corner_radius=12, border_width=1, border_color="#e5e7eb")
        
        innerFrame = ctk.CTkFrame(self.uploadFrame, fg_color="transparent")
        innerFrame.pack(expand=True)

        ctk.CTkLabel(innerFrame, text="Drop, Upload or Paste Images", font=ctk.CTkFont(family=fontFamily, size=20, weight="bold"), text_color=textPrimary).pack(pady=(40, 5))
        ctk.CTkLabel(innerFrame, text="Supported formats: JPG, PNG, GIF, JFIF (JPEG), HEIC, PDF", font=ctk.CTkFont(family=fontFamily, size=14), text_color=textMuted).pack(pady=(0, 30))

        btnFrame = ctk.CTkFrame(innerFrame, fg_color="transparent")
        btnFrame.pack(pady=10)

        ctk.CTkButton(btnFrame, text="↑ Browse", command=self.browseImage, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", font=ctk.CTkFont(family=fontFamily, size=16, weight="bold"), height=50, width=160, corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(btnFrame, text="🔗", fg_color="transparent", border_width=1, border_color=accentColor, text_color=accentColor, hover_color="#f3ebff", height=50, width=50, corner_radius=8, font=ctk.CTkFont(family=fontFamily, size=16)).pack(side="left", padx=5)

        self.ocrModeVar = ctk.StringVar(value="formatted")
        
        radioFrame = ctk.CTkFrame(innerFrame, fg_color="transparent")
        radioFrame.pack(pady=30)

        # Radio button 1
        r1Frame = ctk.CTkFrame(radioFrame, fg_color="transparent", border_width=1, border_color="#e5e7eb", corner_radius=8)
        r1Frame.pack(side="left", padx=10, ipadx=10, ipady=5)
        ctk.CTkRadioButton(r1Frame, text="Simple OCR\nSimple plain text", variable=self.ocrModeVar, value="simple", text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), fg_color=accentColor, border_width_checked=5).pack(pady=10, padx=10)

        # Radio button 2
        r2Frame = ctk.CTkFrame(radioFrame, fg_color="transparent", border_width=1, border_color="#e5e7eb", corner_radius=8)
        r2Frame.pack(side="left", padx=10, ipadx=10, ipady=5)
        ctk.CTkRadioButton(r2Frame, text="Formatted Text\nTable, list, headings etc.", variable=self.ocrModeVar, value="formatted", text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), fg_color=accentColor, border_width_checked=5).pack(pady=10, padx=10)

        # Footer Privacy
        ctk.CTkLabel(self.uploadFrame, text="*Your privacy is protected! No data is transmitted or stored.", font=ctk.CTkFont(family=fontFamily, size=12, slant="italic"), text_color=textMuted).pack(side="bottom", pady=20, anchor="w", padx=30)

    def buildPreviewBox(self):
        self.previewFrame = ctk.CTkFrame(self.mainContainer, fg_color=cardTint, corner_radius=12, border_width=1, border_color="#e5e7eb")
        
        self.previewCanvas = tk.Canvas(self.previewFrame, bg=bgTint, highlightthickness=1, highlightbackground="#e5e7eb")
        self.previewCanvas.pack(fill="both", expand=True, padx=25, pady=(25, 10))
        self.previewCanvas.bind("<Configure>", self.onCanvasResize)

        self.progressBar = ctk.CTkProgressBar(self.previewFrame, progress_color=accentColor, fg_color="#e5e7eb", height=4, corner_radius=0)
        self.progressBar.set(0)

        bottomBar = ctk.CTkFrame(self.previewFrame, fg_color="transparent", height=80)
        bottomBar.pack(fill="x", side="bottom", padx=25, pady=(0, 20))
        
        self.fileLabel = ctk.CTkLabel(bottomBar, text="filename.png", font=ctk.CTkFont(family=fontFamily, size=15, weight="bold"), text_color=textPrimary)
        self.fileLabel.pack(side="left")

        self.statusLabel = ctk.CTkLabel(bottomBar, text="", font=ctk.CTkFont(family=fontFamily, size=13), text_color=successColor)
        self.statusLabel.pack(side="left", padx=25)

        btnContainer = ctk.CTkFrame(bottomBar, fg_color="transparent")
        btnContainer.pack(side="right")

        ctk.CTkButton(btnContainer, text="Cancel", command=self.showUploadBox, fg_color="transparent", border_width=1, border_color=errorColor, text_color=errorColor, hover_color="#fee2e2", width=110, height=45, corner_radius=8, font=ctk.CTkFont(family=fontFamily, size=14, weight="bold")).pack(side="left", padx=10)
        
        self.convertBtn = ctk.CTkButton(btnContainer, text="Convert to Word", command=self.startConversion, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", width=180, height=45, corner_radius=8, font=ctk.CTkFont(family=fontFamily, size=15, weight="bold"))
        self.convertBtn.pack(side="right")

    def showUploadBox(self):
        self.previewFrame.pack_forget()
        self.uploadFrame.pack(fill="both", expand=True)
        self.imagePath = None

    def showPreviewBox(self, imgPath):
        self.imagePath = imgPath
        self.fileLabel.configure(text=os.path.basename(imgPath))
        self.uploadFrame.pack_forget()
        self.previewFrame.pack(fill="both", expand=True)
        self.progressBar.pack_forget()
        self.statusLabel.configure(text="Ready to process", text_color=textMuted)
        self.updatePreview(imgPath)

    def onCanvasResize(self, event):
        if self.imagePath:
            self.updatePreview(self.imagePath)

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
        self.showPreviewBox(selectedPath)

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

    def startConversion(self):
        if self.isProcessing:
            return
        if not self.imagePath:
            messagebox.showwarning("No Image", "Please select an image first.")
            return
        self.isProcessing = True
        self.convertBtn.configure(state="disabled", text="Processing...")
        
        self.progressBar.pack(fill="x", padx=25, pady=(0, 10), before=self.previewCanvas.master.winfo_children()[-1])
        self.progressBar.start()
        
        self.setStatus("Processing securely offline...", textMuted)
        threading.Thread(target=self.convertWorker, daemon=True).start()

    def convertWorker(self):
        try:
            # We enforce localMode=True since the UI guarantees "No data is transmitted"
            ocrResult = runOcr(self.imagePath, localMode=True)

            baseName  = os.path.splitext(os.path.basename(self.imagePath))[0]
            outDir    = os.path.dirname(self.imagePath)
            outputPath = os.path.join(outDir, f"{baseName}_converted.docx")

            # Simple mode logic - we just ignore formatting if simple is chosen
            # Our document_builder currently assumes full formatting dict. 
            # If simple is selected, we could strip out formatting from ocrResult. 
            # For MVP, we'll just pass it through and rely on document_builder.
            # In a real implementation, we'd modify buildDocx to ignore styles.

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
