from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, requests, smtplib, mimetypes, base64, json
from typing import List, Optional
from email.message import EmailMessage
from dotenv import load_dotenv
import sys
from pathlib import Path

# Get the project root directory (one level up from current directory)
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = os.path.join(ROOT_DIR, '.env')

# Load environment variables from the root .env file
load_dotenv(ENV_PATH)
print(f"Loading .env from: {ENV_PATH}")

app = FastAPI(title="Email Generator & Sender")

# CORS (optional, helpful during local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Get environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Extract Google credentials from base64
google_credentials = None
token_json = None
if os.getenv("GOOGLE_CREDENTIALS_BASE64"):
    try:
        decoded_credentials = base64.b64decode(os.getenv("GOOGLE_CREDENTIALS_BASE64")).decode('utf-8')
        google_credentials = json.loads(decoded_credentials)
    except Exception as e:
        print(f"Error decoding Google credentials: {e}")

if os.getenv("TOKEN_JSON_BASE64"):
    try:
        decoded_token = base64.b64decode(os.getenv("TOKEN_JSON_BASE64")).decode('utf-8')
        token_json = json.loads(decoded_token)
    except Exception as e:
        print(f"Error decoding token JSON: {e}")

# Set Gmail credentials - need to add these to your .env file
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

@app.get("/")
def root():
    return {"ok": True, "service": "email-api", "endpoints": ["/generate-email", "/send-email"]}

@app.get("/health")
def health():
    env_status = {
        "TELEGRAM_TOKEN": bool(TELEGRAM_TOKEN),
        "COHERE_API_KEY": bool(COHERE_API_KEY),
        "GMAIL_CREDENTIALS": bool(google_credentials),
        "GMAIL_TOKEN": bool(token_json),
        "GMAIL_USER": bool(GMAIL_USER),
        "GMAIL_PASS": bool(GMAIL_PASS),
    }
    return {"status": "ok", "environment": env_status}

def _auto_subject(topic: str, tone: str) -> str:
    return f"Regarding: {topic}" if tone.lower() == "formal" else f"Let's talk about {topic}"

@app.post("/generate-email")
def generate_email(
    role: str = Form(...),
    tone: str = Form(...),
    topic: str = Form(...),
    subject: str = Form("auto"),
    name: str = Form(""),
    position: str = Form(""),
    recipient_name: str = Form("Dear Sir/Madam")
):
    # Check for Azure OpenAI credentials
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    azure_api_version = os.getenv("AZURE_API_VERSION", "2023-05-15")
    
    if not (azure_key and azure_endpoint and azure_deployment):
        return JSONResponse(status_code=500, content={"error": "Missing Azure OpenAI credentials"})

    subject_final = _auto_subject(topic, tone) if subject.strip().lower() == "auto" else subject.strip()
    
    # Enhanced prompt with name and position
    prompt = f"""Write a {tone} email from a {role} named {name} ({position}) about: {topic}.
Address it to "{recipient_name}". 
Subject: "{subject_final}"."""

    try:
        # Azure OpenAI API call
        headers = {
            "api-key": azure_key,
            "Content-Type": "application/json"
        }
        
        body = {
            "messages": [
                {"role": "system", "content": "You are a professional email assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        # Format Azure OpenAI URL
        url = f"{azure_endpoint}openai/deployments/{azure_deployment}/chat/completions?api-version={azure_api_version}"
        
        r = requests.post(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Extract text from Azure OpenAI response
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        if not text:
            return JSONResponse(status_code=502, content={"error": "Empty response from Azure OpenAI"})
        return {"subject": subject_final, "email": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/send-email")
async def send_email(
    recipient: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    attachments: Optional[List[UploadFile]] = File(None)
):
    print(f"Email credentials: {os.getenv('GMAIL_USER')}, pass length: {len(os.getenv('GMAIL_PASS', ''))}")
    
    if not (GMAIL_USER and GMAIL_PASS):
        return JSONResponse(status_code=500, content={"error": "Missing GMAIL_USER/GMAIL_PASS"})

    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    # Attach multiple files (optional)
    if attachments:
        for file in attachments:
            file_bytes = await file.read()
            guessed = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
            maintype, subtype = guessed.split("/")
            msg.add_attachment(file_bytes, maintype=maintype, subtype=subtype, filename=file.filename)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        return {"status": "sent", "to": recipient}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})