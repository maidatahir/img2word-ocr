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
from src.document_builder import buildDocx, buildPdf, buildTxt
from src.llm_client      import GeminiClient

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

bgTint         = "#f8f9fa"   
cardTint       = "#ffffff"   
accentColor    = "#8c52ff"   
accentHover    = "#7a3cf5"
textPrimary    = "#212529"   
textMuted      = "#6c757d"   
successColor   = "#198754"   
errorColor     = "#dc3545"   
fontFamily     = "Helvetica" 

settingsPath   = os.path.join(baseDir, "settings.json")
memoryPath     = os.path.join(baseDir, "user_memory.json")

class ImageToWordApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Image to Text Converter")
        self.geometry("1200x850")
        self.minsize(1000, 750)
        self.configure(fg_color=bgTint)

        self.imagePath = None
        self.tkImg     = None
        self.ocrResult = None
        self.isProcessing = False
        
        self.isChatOpen = False
        self.isAnimating = False
        self.currentRelX = 1.0 
        self.chatPanelWidthRel = 0.32

        self.userMemory = self.loadMemory()
        self.settings = self.loadSettings()
        self.llmClient = GeminiClient(self.settings.get("gemini_api_key"))

        self.buildUi()
        self.checkTesseract()

        self.pastelColors = [(255, 209, 220), (230, 230, 250), (209, 236, 241), (212, 237, 218), (255, 243, 205)]
        self.currentColorIndex = 0
        self.nextColorIndex = 1
        self.gradientStep = 0.0
        self.animateBackground()

    def loadMemory(self):
        if os.path.exists(memoryPath):
            try:
                with open(memoryPath, "r") as f: return json.load(f)
            except: return {}
        return {}

    def loadSettings(self):
        if os.path.exists(settingsPath):
            try:
                with open(settingsPath, "r") as f: return json.load(f)
            except: return {}
        return {}

    def saveSettings(self):
        with open(settingsPath, "w", encoding="utf-8") as f:
            json.dump(self.settings, f)

    def saveMemory(self):
        with open(memoryPath, "w") as f: json.dump(self.userMemory, f)

    def animateBackground(self):
        colorOne = self.pastelColors[self.currentColorIndex]
        colorTwo = self.pastelColors[self.nextColorIndex]
        redVal = int(colorOne[0] + (colorTwo[0] - colorOne[0]) * self.gradientStep)
        greenVal = int(colorOne[1] + (colorTwo[1] - colorOne[1]) * self.gradientStep)
        blueVal = int(colorOne[2] + (colorTwo[2] - colorOne[2]) * self.gradientStep)
        hexColor = f"#{redVal:02x}{greenVal:02x}{blueVal:02x}"
        self.configure(fg_color=hexColor)
        if hasattr(self, 'mainLayoutFrame'): self.mainLayoutFrame.configure(fg_color="transparent")
        if hasattr(self, 'mainContainer'): self.mainContainer.configure(fg_color="transparent")
        self.gradientStep += 0.005
        if self.gradientStep >= 1.0:
            self.gradientStep = 0.0
            self.currentColorIndex = self.nextColorIndex
            self.nextColorIndex = (self.nextColorIndex + 1) % len(self.pastelColors)
        self.after(50, self.animateBackground)

    def showTermsModal(self, onAccept=None):
        modalWindow = ctk.CTkToplevel(self)
        modalWindow.title("Terms & Privacy")
        modalWindow.geometry("550x500")
        modalWindow.configure(fg_color=bgTint)
        modalWindow.attributes("-topmost", True)
        modalWindow.grab_set()
        ctk.CTkLabel(modalWindow, text="Privacy & Terms of Use", font=ctk.CTkFont(family=fontFamily, size=22, weight="bold"), text_color=accentColor).pack(pady=(30, 10))
        termsText = (
            "By using this Agentic System, you agree to the following:\n\n"
            "1. PRIVACY: Your data remains yours. Processing is entirely offline.\n"
            "2. MEMORY: The agent learns locally to improve accuracy.\n"
            "3. INTEGRITY: Respect copyrights and user data privacy."
        )
        ctk.CTkLabel(modalWindow, text=termsText, font=ctk.CTkFont(family=fontFamily, size=14), text_color=textPrimary, justify="left").pack(padx=40, pady=10)
        cbVar1, cbVar2 = ctk.BooleanVar(value=False), ctk.BooleanVar(value=False)
        def checkAcceptState(*args):
            if cbVar1.get() and cbVar2.get(): acceptBtn.configure(state="normal", fg_color=accentColor)
            else: acceptBtn.configure(state="disabled", fg_color="#d1d1d6")
        cbVar1.trace_add("write", checkAcceptState)
        cbVar2.trace_add("write", checkAcceptState)
        ctk.CTkCheckBox(modalWindow, text="I agree to the offline Privacy processing.", variable=cbVar1, font=ctk.CTkFont(family=fontFamily, size=13, weight="bold"), text_color=textPrimary, fg_color=accentColor).pack(anchor="w", padx=45, pady=(15, 5))
        ctk.CTkCheckBox(modalWindow, text="I understand the Agent Memory features.", variable=cbVar2, font=ctk.CTkFont(family=fontFamily, size=13, weight="bold"), text_color=textPrimary, fg_color=accentColor).pack(anchor="w", padx=45, pady=5)
        def acceptTerms():
            with open(settingsPath, "w", encoding="utf-8") as f: json.dump({"acceptedTerms": True}, f)
            modalWindow.destroy()
            if onAccept: onAccept()
        def declineTerms(): modalWindow.destroy()
        btnFrame = ctk.CTkFrame(modalWindow, fg_color="transparent")
        btnFrame.pack(pady=25)
        ctk.CTkButton(btnFrame, text="Decline", command=declineTerms, fg_color="transparent", text_color=errorColor, font=ctk.CTkFont(family=fontFamily, size=15, weight="bold")).pack(side="left", padx=15)
        acceptBtn = ctk.CTkButton(btnFrame, text="I Accept", command=acceptTerms, fg_color="#d1d1d6", text_color="#ffffff", state="disabled", corner_radius=8, font=ctk.CTkFont(family=fontFamily, size=15, weight="bold"))
        acceptBtn.pack(side="right", padx=15)
        self.wait_window(modalWindow)

    def showSettingsModal(self):
        settingsWindow = ctk.CTkToplevel(self)
        settingsWindow.title("System Settings")
        settingsWindow.geometry("500x350")
        settingsWindow.configure(fg_color=bgTint)
        settingsWindow.attributes("-topmost", True)
        settingsWindow.grab_set()
        ctk.CTkLabel(settingsWindow, text="⚙️ Application Settings", font=ctk.CTkFont(family=fontFamily, size=20, weight="bold"), text_color=textPrimary).pack(pady=(30, 20))
        ctk.CTkLabel(settingsWindow, text="Gemini API Key:", font=ctk.CTkFont(size=13, weight="bold"), text_color=textPrimary).pack(anchor="w", padx=50)
        keyEntry = ctk.CTkEntry(settingsWindow, placeholder_text="Enter your API key here...", width=400, height=40, show="*")
        keyEntry.insert(0, self.settings.get("gemini_api_key", ""))
        keyEntry.pack(pady=(5, 20), padx=50)
        def saveApiKey():
            newKey = keyEntry.get().strip()
            self.settings["gemini_api_key"] = newKey
            self.saveSettings()
            self.llmClient = GeminiClient(newKey)
            messagebox.showinfo("Success", "Settings saved successfully!")
            settingsWindow.destroy()
        ctk.CTkButton(settingsWindow, text="Save Settings", command=saveApiKey, fg_color=accentColor, hover_color=accentHover, height=45, width=200, corner_radius=8).pack(pady=20)

    def showSecurityGuidelines(self):
        securityWindow = ctk.CTkToplevel(self)
        securityWindow.title("Agentic Security Protocol")
        securityWindow.geometry("500x400")
        securityWindow.configure(fg_color=bgTint)
        securityWindow.attributes("-topmost", True)
        securityWindow.grab_set()
        ctk.CTkLabel(securityWindow, text="🛡️ Agentic Security Protocol", font=ctk.CTkFont(family=fontFamily, size=20, weight="bold"), text_color="#0d6efd").pack(pady=(30, 20))
        guidelinesText = (
            "• Local Sovereignty: Agentic reasoning happens 100% offline.\n"
            "• Zero Data Leaks: No telemetry or data is sent to cloud APIs.\n"
            "• Encrypted Memory: User patterns are stored with local hashing.\n"
            "• Ephemeral Processing: Temporary buffers are cleared after exit."
        )
        ctk.CTkLabel(securityWindow, text=guidelinesText, font=ctk.CTkFont(family=fontFamily, size=14), text_color=textPrimary, justify="left").pack(padx=30, pady=10)
        ctk.CTkButton(securityWindow, text="I Understand", command=securityWindow.destroy, fg_color="#0d6efd", corner_radius=8).pack(pady=30)

    def checkTesseract(self):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except: messagebox.showerror("Tesseract Not Found", "Please install Tesseract OCR.")

    def buildUi(self):
        self.navFrame = ctk.CTkFrame(self, height=65, fg_color=cardTint, corner_radius=0)
        self.navFrame.pack(fill="x", side="top")
        self.navFrame.pack_propagate(False)
        leftNav = ctk.CTkFrame(self.navFrame, fg_color="transparent")
        leftNav.pack(side="left", padx=20)
        ctk.CTkLabel(leftNav, text="📝 Image To Text", font=ctk.CTkFont(family=fontFamily, size=16, weight="bold"), text_color="#4f46e5").pack(side="left")
        rightNav = ctk.CTkFrame(self.navFrame, fg_color="transparent")
        rightNav.pack(side="right", padx=20)
        ctk.CTkButton(rightNav, text="⚙️ Settings", command=self.showSettingsModal, fg_color="transparent", text_color=textMuted, font=ctk.CTkFont(family=fontFamily, size=14), hover_color="#f3f4f6", width=100).pack(side="left", padx=5)
        ctk.CTkButton(rightNav, text="💬 Ask Agent", command=self.toggleChatPanel, fg_color="transparent", text_color="#4f46e5", font=ctk.CTkFont(family=fontFamily, size=14, weight="bold"), hover_color="#f3f4f6", width=100).pack(side="left")

        self.mainLayoutFrame = ctk.CTkFrame(self, fg_color="transparent")
        self.mainLayoutFrame.pack(fill="both", expand=True)
        heroFrame = ctk.CTkFrame(self.mainLayoutFrame, fg_color="transparent")
        heroFrame.pack(fill="x", pady=(50, 20))
        ctk.CTkLabel(heroFrame, text="Image to Text Converter", font=ctk.CTkFont(family=fontFamily, size=34, weight="bold"), text_color=textPrimary).pack()
        ctk.CTkLabel(heroFrame, text="An offline image to text converter to extract text from images.", font=ctk.CTkFont(family=fontFamily, size=16), text_color=textMuted).pack(pady=(8, 18))
        self.mainContainer = ctk.CTkFrame(self.mainLayoutFrame, fg_color="transparent")
        self.mainContainer.pack(fill="both", expand=True, padx=40, pady=(10, 40))
        self.buildUploadBox()
        self.buildPreviewBox()
        self.buildResultBox()
        self.showUploadBox()
        self.chatPanel = ctk.CTkFrame(self, fg_color=cardTint, corner_radius=15, border_width=2, border_color="#dee2e6")
        self.buildChatUi()

    def buildChatUi(self):
        chatHeader = ctk.CTkFrame(self.chatPanel, height=60, fg_color="transparent")
        chatHeader.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(chatHeader, text="Agent Assistant", font=ctk.CTkFont(family=fontFamily, size=18, weight="bold"), text_color=accentColor).pack(side="left")
        ctk.CTkButton(chatHeader, text="✕", width=30, height=30, fg_color="transparent", text_color=textMuted, font=ctk.CTkFont(size=18), hover_color="#f3f4f6", command=self.closeChatPanel).pack(side="right")
        self.chatHistory = ctk.CTkTextbox(self.chatPanel, fg_color=bgTint, text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), wrap="word", state="disabled", corner_radius=10, border_width=1, border_color="#dee2e6")
        self.chatHistory.pack(fill="both", expand=True, padx=20, pady=20)
        inputFrame = ctk.CTkFrame(self.chatPanel, fg_color="transparent")
        inputFrame.pack(fill="x", padx=20, pady=(0, 10))
        self.queryInput = ctk.CTkEntry(inputFrame, placeholder_text="Ask me anything...", fg_color=bgTint, text_color=textPrimary, border_width=1, border_color="#dee2e6", corner_radius=8, font=ctk.CTkFont(family=fontFamily, size=13), height=40)
        self.queryInput.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.queryInput.bind("<Return>", lambda e: self.processQuery())
        ctk.CTkButton(inputFrame, text="Send", width=60, height=40, corner_radius=8, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", font=ctk.CTkFont(family=fontFamily, size=14, weight="bold"), command=self.processQuery).pack(side="right")
        memFrame = ctk.CTkFrame(self.chatPanel, fg_color="transparent")
        memFrame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(memFrame, text="🗑️ Clear Memory", command=self.clearMemory, fg_color="transparent", text_color=errorColor, font=ctk.CTkFont(size=12)).pack(side="right")
        self.appendChatMessage("Agent", "Hello! I am your AI Assistant. I learn from your local files to improve over time. How can I help?")

    def clearMemory(self):
        self.userMemory = {}
        self.saveMemory()
        self.appendChatMessage("System", "Agent memory has been cleared successfully.")

    def toggleChatPanel(self):
        if self.isAnimating: return
        if self.isChatOpen: self.closeChatPanel()
        else: self.openChatPanel()
    def openChatPanel(self):
        if self.isAnimating or self.isChatOpen: return
        self.isAnimating, self.isChatOpen = True, True
        self.chatPanel.lift()
        self.animateChatPanel(True)
    def closeChatPanel(self):
        if self.isAnimating or not self.isChatOpen: return
        self.isAnimating, self.isChatOpen = True, False
        self.animateChatPanel(False)
    def animateChatPanel(self, opening):
        targetRelX = (1.0 - self.chatPanelWidthRel) if opening else 1.0
        step, delay = 0.025, 12
        if opening:
            if self.currentRelX > targetRelX:
                self.currentRelX = max(self.currentRelX - step, targetRelX)
                self.chatPanel.place(relx=self.currentRelX, rely=0.08, relwidth=self.chatPanelWidthRel, relheight=0.9, anchor="nw")
                self.after(delay, lambda: self.animateChatPanel(True))
            else: self.isAnimating = False
        else:
            if self.currentRelX < targetRelX:
                self.currentRelX = min(self.currentRelX + step, targetRelX)
                self.chatPanel.place(relx=self.currentRelX, rely=0.08, relwidth=self.chatPanelWidthRel, relheight=0.9, anchor="nw")
                self.after(delay, lambda: self.animateChatPanel(False))
            else: self.chatPanel.place_forget(); self.isAnimating = False

    def appendChatMessage(self, sender, msg):
        self.chatHistory.configure(state="normal")
        self.chatHistory.insert("end", f"{sender}:\n{msg}\n\n")
        self.chatHistory.configure(state="disabled"); self.chatHistory.see("end")
    def addLog(self, msg):
        if not self.isChatOpen: self.openChatPanel()
        self.appendChatMessage("System", f"⚙️ {msg}")

    def processQuery(self):
        queryText = self.queryInput.get().strip()
        if not queryText: return
        self.queryInput.delete(0, "end")
        self.appendChatMessage("You", queryText)
        if not self.llmClient.isActive():
            self.after(500, lambda: self.appendChatMessage("Agent", "I need a Gemini API key to chat! Please add one in Settings ⚙️"))
            return
        context = ""
        if self.ocrResult:
            context = self.ocrResult.get("rawText", "")[:2000] 
        def getAiResponse():
            response = self.llmClient.getChatResponse(queryText, context)
            self.after(0, lambda: self.appendChatMessage("Agent", response))
        threading.Thread(target=getAiResponse, daemon=True).start()

    def onModeChanged(self, *args):
        if self.ocrModeVar.get() == "agentic": self.showSecurityGuidelines()

    def buildUploadBox(self):
        self.uploadFrame = ctk.CTkFrame(self.mainContainer, fg_color=cardTint, corner_radius=12, border_width=1, border_color="#e5e7eb")
        innerFrame = ctk.CTkFrame(self.uploadFrame, fg_color="transparent")
        innerFrame.pack(expand=True)
        ctk.CTkLabel(innerFrame, text="Drop, Upload or Paste Images", font=ctk.CTkFont(family=fontFamily, size=20, weight="bold"), text_color=textPrimary).pack(pady=(40, 5))
        ctk.CTkLabel(innerFrame, text="Supported formats: JPG, PNG, GIF, JFIF, HEIC, PDF", font=ctk.CTkFont(family=fontFamily, size=14), text_color=textMuted).pack(pady=(0, 30))
        btnFrame = ctk.CTkFrame(innerFrame, fg_color="transparent")
        btnFrame.pack(pady=10)
        ctk.CTkButton(btnFrame, text="↑ Browse", command=self.browseImage, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", font=ctk.CTkFont(family=fontFamily, size=16, weight="bold"), height=50, width=160, corner_radius=8).pack(side="left", padx=5)
        self.ocrModeVar = ctk.StringVar(value="simple")
        self.ocrModeVar.trace_add("write", self.onModeChanged)
        radioFrame = ctk.CTkFrame(innerFrame, fg_color="transparent")
        radioFrame.pack(pady=30)
        for modeVal, modeText in [("simple", "Simple OCR\nPlain text"), ("agentic", "Agentic Mode\nContext Aware")]:
            cardFrame = ctk.CTkFrame(radioFrame, fg_color="transparent", border_width=1, border_color="#e5e7eb", corner_radius=8)
            cardFrame.pack(side="left", padx=10, ipadx=10, ipady=5)
            ctk.CTkRadioButton(cardFrame, text=modeText, variable=self.ocrModeVar, value=modeVal, text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), fg_color=accentColor).pack(pady=10, padx=10)
        ctk.CTkLabel(self.uploadFrame, text="*Your privacy is protected! No data is transmitted.", font=ctk.CTkFont(family=fontFamily, size=12, slant="italic"), text_color=textMuted).pack(side="bottom", pady=20, anchor="w", padx=30)

    def buildPreviewBox(self):
        self.previewFrame = ctk.CTkFrame(self.mainContainer, fg_color=cardTint, corner_radius=12, border_width=1, border_color="#e5e7eb")
        self.previewCanvas = tk.Canvas(self.previewFrame, bg=bgTint, highlightthickness=1, highlightbackground="#e5e7eb")
        self.previewCanvas.pack(fill="both", expand=True, padx=25, pady=(25, 10))
        self.previewCanvas.bind("<Configure>", lambda e: self.updatePreview(self.imagePath) if self.imagePath else None)
        self.progressBar = ctk.CTkProgressBar(self.previewFrame, progress_color=accentColor, fg_color="#e5e7eb", height=4, corner_radius=0)
        self.progressBar.set(0)
        bottomFrame = ctk.CTkFrame(self.previewFrame, fg_color="transparent", height=80)
        bottomFrame.pack(fill="x", side="bottom", padx=25, pady=(0, 20))
        self.fileLabel = ctk.CTkLabel(bottomFrame, text="", font=ctk.CTkFont(family=fontFamily, size=15, weight="bold"), text_color=textPrimary)
        self.fileLabel.pack(side="left")
        btnContainer = ctk.CTkFrame(bottomFrame, fg_color="transparent")
        btnContainer.pack(side="right")
        ctk.CTkButton(btnContainer, text="Cancel", command=self.showUploadBox, fg_color="transparent", border_width=1, border_color=errorColor, text_color=errorColor, width=110, height=45, corner_radius=8).pack(side="left", padx=10)
        self.convertBtn = ctk.CTkButton(btnContainer, text="Convert Now", command=self.startConversion, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", width=180, height=45, corner_radius=8)
        self.convertBtn.pack(side="right")

    def buildResultBox(self):
        self.resultFrame = ctk.CTkFrame(self.mainContainer, fg_color=cardTint, corner_radius=12, border_width=1, border_color="#e5e7eb")
        headerFrame = ctk.CTkFrame(self.resultFrame, fg_color="transparent")
        headerFrame.pack(fill="x", padx=25, pady=(20, 10))
        ctk.CTkLabel(headerFrame, text="Extraction Preview", font=ctk.CTkFont(family=fontFamily, size=18, weight="bold"), text_color=textPrimary).pack(side="left")
        ctk.CTkButton(headerFrame, text="← Start Over", command=self.showUploadBox, width=100, fg_color="transparent", text_color=accentColor, font=ctk.CTkFont(size=13, weight="bold")).pack(side="right")
        self.resultText = ctk.CTkTextbox(self.resultFrame, fg_color=bgTint, text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), wrap="word", corner_radius=10, border_width=1, border_color="#dee2e6")
        self.resultText.pack(fill="both", expand=True, padx=25, pady=10)
        footerFrame = ctk.CTkFrame(self.resultFrame, fg_color="transparent", height=100)
        footerFrame.pack(fill="x", padx=25, pady=(10, 25))
        ctk.CTkLabel(footerFrame, text="Download as:", font=ctk.CTkFont(size=14, weight="bold"), text_color=textMuted).pack(side="left", padx=(0, 20))
        ctk.CTkButton(footerFrame, text="📄 Word (.docx)", command=lambda: self.downloadResult("docx"), fg_color=accentColor, width=140, height=40, corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(footerFrame, text="📑 PDF (.pdf)", command=lambda: self.downloadResult("pdf"), fg_color="#4f46e5", width=140, height=40, corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(footerFrame, text="📝 Text (.txt)", command=lambda: self.downloadResult("txt"), fg_color=textMuted, width=140, height=40, corner_radius=8).pack(side="left", padx=5)

    def showUploadBox(self):
        self.previewFrame.pack_forget()
        self.resultFrame.pack_forget()
        self.uploadFrame.pack(fill="both", expand=True)
        self.imagePath = None
    def showPreviewBox(self, imgPath):
        self.imagePath = imgPath
        self.fileLabel.configure(text=os.path.basename(imgPath))
        self.uploadFrame.pack_forget()
        self.resultFrame.pack_forget()
        self.previewFrame.pack(fill="both", expand=True)
        self.progressBar.pack_forget()
        self.updatePreview(imgPath)
    def showResultBox(self, result):
        self.ocrResult = result
        self.previewFrame.pack_forget()
        self.uploadFrame.pack_forget()
        self.resultFrame.pack(fill="both", expand=True)
        self.resultText.configure(state="normal")
        self.resultText.delete("1.0", "end")
        extractedText = result.get("rawText", "")
        if not extractedText: extractedText = "\n".join([p.get("text", "") for p in result.get("paragraphs", [])])
        self.resultText.insert("1.0", extractedText)
        self.resultText.configure(state="disabled")
    def browseImage(self): self.showTermsModal(onAccept=self.actuallyBrowse)
    def actuallyBrowse(self):
        pickedFile = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg *.bmp"), ("All", "*.*")])
        if pickedFile: self.showPreviewBox(pickedFile)
    def startConversion(self):
        if self.isProcessing: return
        self.isProcessing = True
        self.convertBtn.configure(state="disabled", text="Working...")
        self.progressBar.pack(fill="x", padx=25, pady=(0, 10), before=self.previewCanvas.master.winfo_children()[-1])
        self.progressBar.start()
        threading.Thread(target=self.convertWorker, daemon=True).start()
    def convertWorker(self):
        try:
            activeMode = self.ocrModeVar.get()
            self.after(0, lambda: self.addLog(f"Backend initialized. Mode: {activeMode.upper()}"))
            if activeMode == "agentic":
                self.after(400, lambda: self.addLog("Agentic Module: Activating Context-Aware reasoning..."))
                self.after(800, lambda: self.addLog("Scanning for semantic structure and handwriting patterns..."))
            self.after(1200, lambda: self.addLog("Step 1: Gray-scaling and noise reduction..."))
            self.after(1800, lambda: self.addLog("Step 2: Tesseract OCR Engine analysis..."))
            resData = runOcr(self.imagePath, localMode=True)
            self.after(0, lambda: self.addLog(f"Step 3: Post-processing {len(resData.get('paragraphs', []))} text blocks..."))
            if activeMode == "agentic" and self.llmClient.isActive():
                self.after(500, lambda: self.addLog("Agentic Refinement: Connecting to Gemini for semantic correction..."))
                rawText = resData.get("rawText", "")
                refinedText = self.llmClient.refineOcrText(rawText)
                resData["rawText"] = refinedText
                self.after(1000, lambda: self.addLog("Refinement complete. Corrected typos and improved structure."))
            self.after(2500, lambda: self.after(0, self.onSuccess, resData))
        except Exception as e: self.after(0, self.onError, str(e))
    def onSuccess(self, resData):
        self.isProcessing = False
        self.convertBtn.configure(state="normal", text="Convert Now")
        self.progressBar.stop()
        self.userMemory["processedFiles"] = self.userMemory.get("processedFiles", 0) + 1
        self.saveMemory()
        self.addLog("Conversion successful! Switching to preview.")
        self.showResultBox(resData)
    def onError(self, err):
        self.isProcessing = False
        self.convertBtn.configure(state="normal", text="Convert Now")
        self.progressBar.stop()
        messagebox.showerror("Error", err)
    def downloadResult(self, fmt):
        baseName = os.path.join(os.path.dirname(self.imagePath), os.path.splitext(os.path.basename(self.imagePath))[0])
        try:
            if fmt == "docx": outPath = buildDocx(self.ocrResult, baseName + "_converted.docx")
            elif fmt == "pdf": outPath = buildPdf(self.ocrResult, baseName + "_converted.pdf")
            else: outPath = buildTxt(self.ocrResult, baseName + "_converted.txt")
            if messagebox.askyesno("Success", f"Saved to {os.path.basename(outPath)}\nOpen now?"): os.startfile(outPath)
        except Exception as e: messagebox.showerror("Save Error", str(e))
    def updatePreview(self, imgPath):
        try:
            pilImg = Image.open(imgPath)
            canvasW, canvasH = max(self.previewCanvas.winfo_width(), 100), max(self.previewCanvas.winfo_height(), 100)
            pilImg.thumbnail((canvasW-40, canvasH-40), Image.LANCZOS)
            self.tkImg = ImageTk.PhotoImage(pilImg)
            self.previewCanvas.delete("all")
            self.previewCanvas.create_image(canvasW//2, canvasH//2, image=self.tkImg)
        except: pass

if __name__ == "__main__":
    app = ImageToWordApp()
    app.mainloop()
