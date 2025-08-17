
# 📖 Character Chat from your books/novels/urls

Welcome to the Character Chat API! This powerful backend service allows you to upload a book (as a PDF or from a URL) and chat with the characters from the story. The API extracts characters, understands the book's content, and uses Google's Gemini to generate in-character, context-aware responses.

This backend is designed to be the engine for a Flutter application, providing a seamless and interactive experience for users to engage with their favorite literary worlds.

## ✨ Key Features

*   **Dynamic Document Handling**: Upload books directly as PDF files or scrape text from a website URL.
*   **Intelligent Character Extraction**: Automatically identifies and lists the main characters from the text using NLP (spaCy).
*   **Retrieval-Augmented Generation (RAG)**: Uses local sentence embeddings (`Sentence-Transformers`) for efficient and powerful semantic search to find the most relevant context from the book for any question.
*   **State-of-the-Art AI Chat**: Leverages Google's `gemini-1.5-flash-latest` model to generate natural, in-character conversations.
*   **Conversation Memory**: Remembers the recent history of your chat with each character for more coherent and engaging dialogue.
*   **Fast & Modern API**: Built with FastAPI, providing a robust, high-performance, and well-documented API.

## 🚀 Tech Stack

### Backend
*   **Framework**: FastAPI
*   **AI Model**: Google Gemini (`gemini-1.5-flash-latest`)
*   **Embeddings**: Sentence-Transformers (`all-MiniLM-L6-v2`) for local, private, and fast semantic search.
*   **NLP for Character Extraction**: spaCy
*   **PDF Processing**: PyMuPDF (`fitz`)
*   **Web Scraping**: BeautifulSoup & Requests
*   **Core Language**: Python 3.9+

### Frontend
*   **Framework**: Flutter (This API is the backend for the Flutter app)

## ⚙️ How It Works

The API follows a Retrieval-Augmented Generation (RAG) architecture:

1.  **Upload & Process**: When a user uploads a PDF or URL, the text is extracted, cleaned, and split into smaller, manageable chunks.
2.  **Embed**: The entire text is processed by `spaCy` to identify characters. Simultaneously, each text chunk is converted into a numerical representation (an embedding) using a local `Sentence-Transformer` model. These embeddings are stored in memory.
3.  **Chat & Retrieve**: When a user sends a message to a character, the API embeds the user's query and performs a semantic search (using cosine similarity) against the stored book embeddings to find the most relevant text chunks.
4.  **Generate**: The relevant chunks, the character's name, and the recent chat history are combined into a rich prompt. This prompt is sent to the Gemini API, which generates a response in the voice of the character.

  <!-- You can create and host a simple diagram if you want -->

## 🛠️ Setup and Installation

Follow these steps to get the backend server running locally.

### 1. Prerequisites

*   Python 3.9 or higher
*   A Google Gemini API Key

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-project-directory>
```

### 3. Install Dependencies

It is highly recommended to use a virtual environment.

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```
*(Note: You will need to create a `requirements.txt` file from your project setup. A typical file would include `fastapi`, `uvicorn`, `python-dotenv`, `google-generativeai`, `pydantic`, `sentence-transformers`, `spacy`, `beautifulsoup4`, `requests`, `PyMuPDF`, `scikit-learn`, `python-multipart`)*

### 4. Download spaCy Model

You need to download the English language model for spaCy.

```bash
python -m spacy download en_core_web_sm
```

### 5. Set Up Environment Variables

Create a file named `.env` in the root of your project directory and add your Gemini API key:

```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

### 6. Run the Server

Use `uvicorn` to run the FastAPI application.

```bash
uvicorn main:app --reload
```*(`main` refers to your Python file `main.py`)*

The API will now be running at **http://127.0.0.1:8000**. You can access the interactive API documentation at **http://127.0.0.1:8000/docs**.

## 🔌 API Endpoints for Flutter Integration

Here are the endpoints your Flutter app will interact with.

### `POST /upload`

This endpoint handles the upload of a document (PDF or URL) and returns the initial data.

*   **Request Type**: `multipart/form-data`
*   **Form Fields**:
    *   `file`: (Optional) An uploaded PDF file.
    *   `url`: (Optional) A string containing a URL to a webpage.
*   **Response Body (`UploadResponse`)**:
    ```json
    {
      "text_preview": "A snippet of the extracted text...",
      "total_chars": 123456,
      "characters": ["Harry Potter", "Hermione Granger", "Ron Weasley"]
    }
    ```

### `POST /chat`

This endpoint handles sending a user's message to a character and getting a reply.

*   **Request Body (`ChatRequest`)**:
    ```json
    {
      "character": "Harry Potter",
      "message": "What was your scariest moment at Hogwarts?"
    }
    ```
*   **Response Body (`ChatResponse`)**:
    ```json
    {
      "reply": "It would have to be the time I faced the Dementors near the Black Lake. I felt a coldness I'd never known..."
    }
    ```

### Connecting from Flutter

In your Flutter app, you'll use an HTTP client (like `http` or `dio`) to make POST requests to your local server's IP address (e.g., `http://192.168.1.10:8000`) or the deployed server URL.

**Example Flutter `http` call:**

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<String> sendMessageToCharacter(String character, String message) async {
  final response = await http.post(
    Uri.parse('http://YOUR_API_URL/chat'),
    headers: <String, String>{
      'Content-Type': 'application/json; charset=UTF-8',
    },
    body: jsonEncode(<String, String>{
      'character': character,
      'message': message,
    }),
  );

  if (response.statusCode == 200) {
    return jsonDecode(response.body)['reply'];
  } else {
    throw Exception('Failed to get reply from character.');
  }
}
```

## 🤝 Contributing

Contributions are welcome! If you have suggestions or want to improve the code, please feel free to open an issue or submit a pull request.
