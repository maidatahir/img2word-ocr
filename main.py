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
        self.isProcessing = False
        
        self.chatPanelWidth = 380
        self.isChatOpen = False
        self.isAnimating = False

        self.checkTermsAndConditions()
        self.buildUi()
        self.checkTesseract()

        self.pastelColors = [(255, 209, 220), (230, 230, 250), (209, 236, 241), (212, 237, 218), (255, 243, 205)]
        self.currentColorIndex = 0
        self.nextColorIndex = 1
        self.gradientStep = 0.0
        self.animateBackground()

    def animateBackground(self):
        c1 = self.pastelColors[self.currentColorIndex]
        c2 = self.pastelColors[self.nextColorIndex]
        
        r = int(c1[0] + (c2[0] - c1[0]) * self.gradientStep)
        g = int(c1[1] + (c2[1] - c1[1]) * self.gradientStep)
        b = int(c1[2] + (c2[2] - c1[2]) * self.gradientStep)
        
        hexColor = f"#{r:02x}{g:02x}{b:02x}"
        self.configure(fg_color=hexColor)
        
        if hasattr(self, 'mainLayoutFrame'):
            self.mainLayoutFrame.configure(fg_color="transparent")
        if hasattr(self, 'mainContainer'):
            self.mainContainer.configure(fg_color="transparent")
        
        self.gradientStep += 0.005
        if self.gradientStep >= 1.0:
            self.gradientStep = 0.0
            self.currentColorIndex = self.nextColorIndex
            self.nextColorIndex = (self.nextColorIndex + 1) % len(self.pastelColors)
            
        self.after(50, self.animateBackground)

    def checkTermsAndConditions(self):
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
                "Tesseract OCR is not installed or not on PATH."
            )

    def buildUi(self):
        # Top Navbar
        navFrame = ctk.CTkFrame(self, height=65, fg_color=cardTint, corner_radius=0)
        navFrame.pack(fill="x", side="top")
        navFrame.pack_propagate(False)

        leftNav = ctk.CTkFrame(navFrame, fg_color="transparent")
        leftNav.pack(side="left", padx=20)
        ctk.CTkLabel(leftNav, text="📝 Image To Text", font=ctk.CTkFont(family=fontFamily, size=16, weight="bold"), text_color="#4f46e5").pack(side="left")

        rightNav = ctk.CTkFrame(navFrame, fg_color="transparent")
        rightNav.pack(side="right", padx=20)
        
        self.chatToggleBtn = ctk.CTkButton(rightNav, text="💬 Ask Agent", command=self.toggleChatPanel, fg_color="transparent", text_color="#4f46e5", font=ctk.CTkFont(family=fontFamily, size=14, weight="bold"), hover_color="#f3f4f6", width=100)
        self.chatToggleBtn.pack(side="left", padx=10)

        # Body Layout
        self.bodyFrame = ctk.CTkFrame(self, fg_color="transparent")
        self.bodyFrame.pack(fill="both", expand=True)

        self.mainLayoutFrame = ctk.CTkFrame(self.bodyFrame, fg_color="transparent")
        self.mainLayoutFrame.pack(side="left", fill="both", expand=True)

        # Hero
        heroFrame = ctk.CTkFrame(self.mainLayoutFrame, fg_color="transparent")
        heroFrame.pack(fill="x", pady=(50, 20))
        ctk.CTkLabel(heroFrame, text="Image to Text Converter", font=ctk.CTkFont(family=fontFamily, size=34, weight="bold"), text_color=textPrimary).pack()
        ctk.CTkLabel(heroFrame, text="An offline image to text converter to extract text from images.", font=ctk.CTkFont(family=fontFamily, size=16), text_color=textMuted).pack(pady=(8, 18))

        # Main Container
        self.mainContainer = ctk.CTkFrame(self.mainLayoutFrame, fg_color="transparent")
        self.mainContainer.pack(fill="both", expand=True, padx=40, pady=(10, 40))

        self.buildUploadBox()
        self.buildPreviewBox()
        self.showUploadBox()

        # Chat Panel
        self.chatPanel = ctk.CTkFrame(self.bodyFrame, width=0, fg_color=cardTint, corner_radius=0, border_width=1, border_color="#e5e7eb")
        self.chatPanel.pack(side="right", fill="y")
        self.chatPanel.pack_propagate(False)
        self.buildChatUi()

    def buildChatUi(self):
        chatHeader = ctk.CTkFrame(self.chatPanel, height=60, fg_color="transparent")
        chatHeader.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(chatHeader, text="Agent Assistant", font=ctk.CTkFont(family=fontFamily, size=18, weight="bold"), text_color=accentColor).pack(side="left")
        ctk.CTkButton(chatHeader, text="✕", width=30, height=30, fg_color="transparent", text_color=textMuted, command=self.closeChatPanel).pack(side="right")

        self.chatHistory = ctk.CTkTextbox(self.chatPanel, fg_color=bgTint, text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), wrap="word", state="disabled", corner_radius=10, border_width=1, border_color="#dee2e6")
        self.chatHistory.pack(fill="both", expand=True, padx=20, pady=20)

        inputFrame = ctk.CTkFrame(self.chatPanel, fg_color="transparent")
        inputFrame.pack(fill="x", padx=20, pady=(0, 20))

        self.queryInput = ctk.CTkEntry(inputFrame, placeholder_text="Ask me anything...", fg_color=bgTint, text_color=textPrimary, border_width=1, border_color="#dee2e6", corner_radius=8, font=ctk.CTkFont(family=fontFamily, size=13), height=40)
        self.queryInput.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.queryInput.bind("<Return>", lambda e: self.processQuery())

        ctk.CTkButton(inputFrame, text="Send", width=60, height=40, corner_radius=8, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", font=ctk.CTkFont(family=fontFamily, size=14, weight="bold"), command=self.processQuery).pack(side="right")

        self.appendChatMessage("Agent", "Hello! I am your AI Assistant. How can I help you today?")

    def openChatPanel(self):
        if self.isAnimating or self.isChatOpen:
            return
        self.isAnimating = True
        self.isChatOpen = True
        self.animateChatPanel(True)

    def closeChatPanel(self):
        if self.isAnimating or not self.isChatOpen:
            return
        self.isAnimating = True
        self.isChatOpen = False
        self.animateChatPanel(False)

    def toggleChatPanel(self):
        if self.isChatOpen:
            self.closeChatPanel()
        else:
            self.openChatPanel()

    def animateChatPanel(self, opening):
        currentWidth = self.chatPanel.winfo_width()
        targetWidth = self.chatPanelWidth if opening else 0
        
        step = 25
        delay = 10
        
        if opening:
            if currentWidth < targetWidth:
                newWidth = min(currentWidth + step, targetWidth)
                self.chatPanel.configure(width=newWidth)
                self.after(delay, lambda: self.animateChatPanel(True))
            else:
                self.isAnimating = False
        else:
            if currentWidth > targetWidth:
                newWidth = max(currentWidth - step, targetWidth)
                self.chatPanel.configure(width=newWidth)
                self.after(delay, lambda: self.animateChatPanel(False))
            else:
                self.chatPanel.configure(width=0) # Force absolute 0
                self.isAnimating = False

    def appendChatMessage(self, sender, msg):
        self.chatHistory.configure(state="normal")
        self.chatHistory.insert("end", f"{sender}:\n{msg}\n\n")
        self.chatHistory.configure(state="disabled")
        self.chatHistory.see("end")

    def processQuery(self):
        userText = self.queryInput.get().strip()
        if not userText: return
        self.queryInput.delete(0, "end")
        self.appendChatMessage("You", userText)
        
        reply = "I'm a rule-based agent. I can help with privacy, memory, and OCR info!"
        if "privacy" in userText.lower(): reply = "All processing is done locally on your machine. No data leaves your device."
        elif "memory" in userText.lower(): reply = "You can clear agent memory anytime. It stores handwriting patterns locally."
        
        self.after(500, lambda: self.appendChatMessage("Agent", reply))

    def buildUploadBox(self):
        self.uploadFrame = ctk.CTkFrame(self.mainContainer, fg_color=cardTint, corner_radius=12, border_width=1, border_color="#e5e7eb")
        inner = ctk.CTkFrame(self.uploadFrame, fg_color="transparent")
        inner.pack(expand=True)
        ctk.CTkLabel(inner, text="Drop, Upload or Paste Images", font=ctk.CTkFont(family=fontFamily, size=20, weight="bold"), text_color=textPrimary).pack(pady=(40, 5))
        ctk.CTkLabel(inner, text="Supported formats: JPG, PNG, GIF, JFIF, HEIC, PDF", font=ctk.CTkFont(family=fontFamily, size=14), text_color=textMuted).pack(pady=(0, 30))
        btnF = ctk.CTkFrame(inner, fg_color="transparent")
        btnF.pack(pady=10)
        ctk.CTkButton(btnF, text="↑ Browse", command=self.browseImage, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", font=ctk.CTkFont(family=fontFamily, size=16, weight="bold"), height=50, width=160, corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(btnF, text="🔗", fg_color="transparent", border_width=1, border_color=accentColor, text_color=accentColor, height=50, width=50, corner_radius=8).pack(side="left", padx=5)
        
        self.ocrModeVar = ctk.StringVar(value="formatted")
        radioF = ctk.CTkFrame(inner, fg_color="transparent")
        radioF.pack(pady=30)
        for m, t in [("simple", "Simple OCR\nPlain text"), ("formatted", "Formatted Text\nTables/Styles")]:
            f = ctk.CTkFrame(radioF, fg_color="transparent", border_width=1, border_color="#e5e7eb", corner_radius=8)
            f.pack(side="left", padx=10, ipadx=10, ipady=5)
            ctk.CTkRadioButton(f, text=t, variable=self.ocrModeVar, value=m, text_color=textPrimary, font=ctk.CTkFont(family=fontFamily, size=13), fg_color=accentColor).pack(pady=10, padx=10)
        ctk.CTkLabel(self.uploadFrame, text="*Your privacy is protected! No data is transmitted.", font=ctk.CTkFont(family=fontFamily, size=12, slant="italic"), text_color=textMuted).pack(side="bottom", pady=20, anchor="w", padx=30)

    def buildPreviewBox(self):
        self.previewFrame = ctk.CTkFrame(self.mainContainer, fg_color=cardTint, corner_radius=12, border_width=1, border_color="#e5e7eb")
        self.previewCanvas = tk.Canvas(self.previewFrame, bg=bgTint, highlightthickness=1, highlightbackground="#e5e7eb")
        self.previewCanvas.pack(fill="both", expand=True, padx=25, pady=(25, 10))
        self.previewCanvas.bind("<Configure>", lambda e: self.updatePreview(self.imagePath) if self.imagePath else None)
        self.progressBar = ctk.CTkProgressBar(self.previewFrame, progress_color=accentColor, fg_color="#e5e7eb", height=4, corner_radius=0)
        self.progressBar.set(0)
        bottom = ctk.CTkFrame(self.previewFrame, fg_color="transparent", height=80)
        bottom.pack(fill="x", side="bottom", padx=25, pady=(0, 20))
        self.fileLabel = ctk.CTkLabel(bottom, text="", font=ctk.CTkFont(family=fontFamily, size=15, weight="bold"), text_color=textPrimary)
        self.fileLabel.pack(side="left")
        self.statusLabel = ctk.CTkLabel(bottom, text="", font=ctk.CTkFont(family=fontFamily, size=13), text_color=successColor)
        self.statusLabel.pack(side="left", padx=25)
        btnC = ctk.CTkFrame(bottom, fg_color="transparent")
        btnC.pack(side="right")
        ctk.CTkButton(btnC, text="Cancel", command=self.showUploadBox, fg_color="transparent", border_width=1, border_color=errorColor, text_color=errorColor, width=110, height=45, corner_radius=8).pack(side="left", padx=10)
        self.convertBtn = ctk.CTkButton(btnC, text="Convert to Word", command=self.startConversion, fg_color=accentColor, hover_color=accentHover, text_color="#ffffff", width=180, height=45, corner_radius=8)
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

    def browseImage(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"), ("All", "*.*")])
        if p: self.showPreviewBox(p)

    def updatePreview(self, imgPath):
        try:
            i = Image.open(imgPath)
            w = max(self.previewCanvas.winfo_width(), 100)
            h = max(self.previewCanvas.winfo_height(), 100)
            i.thumbnail((w-40, h-40), Image.LANCZOS)
            self.tkImg = ImageTk.PhotoImage(i)
            self.previewCanvas.delete("all")
            self.previewCanvas.create_image(w//2, h//2, image=self.tkImg)
        except: pass

    def startConversion(self):
        if self.isProcessing: return
        self.isProcessing = True
        self.convertBtn.configure(state="disabled", text="Processing...")
        self.progressBar.pack(fill="x", padx=25, pady=(0, 10), before=self.previewCanvas.master.winfo_children()[-1])
        self.progressBar.start()
        threading.Thread(target=self.convertWorker, daemon=True).start()

    def convertWorker(self):
        try:
            res = runOcr(self.imagePath, localMode=True)
            out = os.path.join(os.path.dirname(self.imagePath), os.path.splitext(os.path.basename(self.imagePath))[0] + "_converted.docx")
            buildDocx(res, out)
            self.after(0, lambda: self.onSuccess(out))
        except Exception as e:
            self.after(0, lambda: self.onError(str(e)))

    def onSuccess(self, out):
        self.isProcessing = False
        self.progressBar.stop()
        self.convertBtn.configure(state="normal", text="Convert to Word")
        if messagebox.askyesno("Done", f"Saved to {out}\nOpen now?"): os.startfile(out)

    def onError(self, err):
        self.isProcessing = False
        self.progressBar.stop()
        self.convertBtn.configure(state="normal", text="Convert to Word")
        messagebox.showerror("Error", err)

if __name__ == "__main__":
    app = ImageToWordApp()
    app.mainloop()
