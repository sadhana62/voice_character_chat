import os
import tempfile
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import spacy
from collections import Counter
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# ===== Load environment variables =====
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ===== Load spaCy model =====
nlp = spacy.load("en_core_web_sm")

# ===== FastAPI app =====
app = FastAPI()

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store uploaded book text globally
BOOK_TEXT = ""

# ===== Data Models =====
class UploadResponse(BaseModel):
    text_preview: str
    total_chars: int
    characters: list

class ChatRequest(BaseModel):
    character: str
    message: str

class ChatResponse(BaseModel):
    reply: str

# ===== Helper: Extract text from PDF =====
def extract_text_from_pdf(file_path):
    text = ""
    pdf = fitz.open(file_path)
    for page in pdf:
        text += page.get_text()
    pdf.close()
    return text

# ===== Helper: Extract text from URL =====
def extract_text_from_url(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.get_text(separator=" ", strip=True)

# ===== Helper: Filter characters =====
def filter_character_list(chars):
    banned_keywords = ["travels", "kingdom", "city", "island", "country", "lord", "sir"]
    filtered = []
    for c in chars:
        name = c.strip()
        if not name:
            continue
        # Remove obviously non-person entities
        if any(bad in name.lower() for bad in banned_keywords):
            continue
        if len(name.split()) > 4:  # avoid long sentences
            continue
        if name not in filtered:
            filtered.append(name)
    return filtered

# ===== /upload =====
@app.get("/")
def root():
    print("this path called")
    return {"message": "Welcome to Character Chat API"}

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(None),
    url: str = Form(None)
):
    print("upload called")
    global BOOK_TEXT
    extracted_text = ""

    # Handle PDF file
    if file:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        extracted_text = extract_text_from_pdf(tmp_path)

    # Handle URL
    elif url:
        extracted_text = extract_text_from_url(url)

    else:
        return UploadResponse(
            text_preview="",
            total_chars=0,
            characters=[]
        )

    # Save globally
    BOOK_TEXT = extracted_text

    # Step 1: SpaCy extraction
    doc = nlp(extracted_text)
    name_entities = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            if len(name.split()) <= 3:
                name_entities.append(name)

    name_counts = Counter(name_entities)
    spacy_top = [name for name, count in name_counts.most_common(15) if count > 3]

    # Step 2: Gemma extraction
    model = genai.GenerativeModel("models/gemma-3-1b-it") 
    char_prompt = f"""
Extract only the main fictional characters' names (people or beings) from this text.
Do NOT include places, titles of books, events, or organizations.
Return each name on a new line, no numbering, no extra words.

Text:
{extracted_text[:4000]}
"""
    char_response = model.generate_content(char_prompt)
    gemma_chars = [
        c.strip("-• \t") for c in char_response.text.split("\n") if c.strip()
    ]

    # Step 3: Merge + filter
    merged = gemma_chars + spacy_top
    final_characters = filter_character_list(merged)

    preview = extracted_text[:500]
    return UploadResponse(
        text_preview=preview,
        total_chars=len(extracted_text),
        characters=final_characters
    )

# ===== /chat =====
@app.post("/chat", response_model=ChatResponse)
async def chat_with_character(chat: ChatRequest):
    print("chat called")
    global BOOK_TEXT
    if not BOOK_TEXT:
        return ChatResponse(reply="Please upload a book or website first.")

    prompt = f"""
You are the character '{chat.character}' from the uploaded book.
Only respond as this character would, based on events, personality, and worldview in the book text below.
Book Text Context:
{BOOK_TEXT[:5000]}
---
User says: "{chat.message}"
"""

    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    response = model.generate_content(prompt)

    return ChatResponse(reply=response.text)
