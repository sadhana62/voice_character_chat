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
from sklearn.metrics.pairwise import cosine_similarity
import difflib
from sentence_transformers import SentenceTransformer  # ✅ local embeddings
import time
import random

# ===== Load environment variables =====
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ===== Load spaCy model =====
nlp = spacy.load("en_core_web_sm")

# ===== Load local embedding model =====
local_embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ===== FastAPI app =====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Global Storage =====
BOOK_TEXT = ""
BOOK_CHUNKS = []
BOOK_EMBEDDINGS = []
CHAT_HISTORY = {}   # keep per-character history

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

# ===== Helpers =====
def extract_text_from_pdf(file_path):
    text = ""
    pdf = fitz.open(file_path)
    for page in pdf:
        text += page.get_text()
    pdf.close()
    return text

def extract_text_from_url(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def split_into_chunks(text, size=2000):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ✅ Local embedding instead of Gemini
def embed_text(text):
    emb = local_embedder.encode([text])[0]
    return emb.tolist()

def semantic_search(query, top_k=3):
    if not BOOK_EMBEDDINGS:
        return []
    q_emb = embed_text(query)
    sims = cosine_similarity([q_emb], BOOK_EMBEDDINGS)[0]
    top_ids = sims.argsort()[-top_k:][::-1]
    return [BOOK_CHUNKS[i] for i in top_ids]

def filter_character_list(chars):
    banned_keywords = [
        "travels", "kingdom", "city", "island", "country",
        "lord", "sir", "school", "hogwarts", "house", "place","Download"
    ]
    clean = []
    for c in chars:
        name = c.strip()
        if not name:
            continue
        if any(bad in name.lower() for bad in banned_keywords):
            continue
        if len(name.split()) > 4:  # ignore long phrases
            continue

        # ✅ only first name
        first_name = name.split()[0].title()

        # ✅ fuzzy dedup (skip if very similar to existing name)
        if any(difflib.SequenceMatcher(None, first_name, x).ratio() > 0.85 for x in clean):
            continue

        clean.append(first_name)

    return clean

# ===== Routes =====
@app.get("/")
def root():
    return {"message": "Welcome to Character Chat API"}

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(None), url: str = Form(None)):
    print("upload called")
    global BOOK_TEXT, BOOK_CHUNKS, BOOK_EMBEDDINGS, CHAT_HISTORY
    extracted_text = ""

    if file:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        extracted_text = extract_text_from_pdf(tmp_path)
    elif url:
        extracted_text = extract_text_from_url(url)
    else:
        return UploadResponse(text_preview="", total_chars=0, characters=[])

    BOOK_TEXT = extracted_text
    BOOK_CHUNKS = split_into_chunks(BOOK_TEXT)

    # ✅ Embed locally
    BOOK_EMBEDDINGS = [embed_text(chunk) for chunk in BOOK_CHUNKS]

    # ✅ SpaCy character detection only
    doc = nlp(extracted_text)
    name_entities = [
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ == "PERSON" and len(ent.text.split()) <= 3
    ]
    name_counts = Counter(name_entities)
    spacy_top = [name for name, count in name_counts.most_common(20) if count > 3]

    final_characters = filter_character_list(spacy_top)

    CHAT_HISTORY = {c: [] for c in final_characters}  # reset history

    preview = extracted_text[:500]
    return UploadResponse(text_preview=preview, total_chars=len(extracted_text), characters=final_characters)


# ... (rest of your imports)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_character(chat: ChatRequest):
    global BOOK_TEXT, CHAT_HISTORY
    if not BOOK_TEXT:
        return ChatResponse(reply="Please upload a book or website first.")

    relevant_context = semantic_search(chat.message, top_k=3)
    history = "\n".join([
        f"User: {m['user']}\n{chat.character}: {m['ai']}"
        for m in CHAT_HISTORY.get(chat.character, [])[-5:]
    ])

    prompt = f"""
You are roleplaying as **{chat.character}** from the uploaded book.

Stay in character. Speak in a natural conversational style.
If the book does not provide enough info, politely say so.

Conversation history:
{history}

Relevant book context:
{relevant_context}

---
User: "{chat.message}"
{chat.character}:
"""

    reply = ""
    retries = 3
    delay = 1  # Initial delay in seconds
    for i in range(retries):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            response = model.generate_content(prompt)
            reply = response.text.strip()
            # print("reply",reply)
            break  # If successful, exit the loop
        except Exception as e:
            if "429" in str(e): # Check if the error is a rate limit error
                print(f"Rate limit exceeded. Retrying in {delay} seconds.")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
                delay += random.uniform(0, 1) # Add jitter
            else:
                reply = f"(⚠️ Error talking to model: {str(e)})"
                break
    else:
        reply = "(⚠️ Error: The model is currently unavailable after multiple retries.)"


    if reply: # Only append to history if a reply was generated
        CHAT_HISTORY[chat.character].append({"user": chat.message, "ai": reply})

    return ChatResponse(reply=reply)