import os
import json
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from docx import Document
from pathlib import Path
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS—allows your React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client (v1 SDK)
client = OpenAI()  # Reads OPENAI_API_KEY automatically

# Admin authentication
security = HTTPBasic()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "secret123")

def check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")

# Utility: extract plain text from a .docx
def extract_text(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file_bytes)
        tmp.seek(0)
        doc = Document(tmp.name)
    return "\n".join(p.text for p in doc.paragraphs)

# --- API ENDPOINTS ---

# 1. Validate SOA via GPT
@app.post("/validate")
async def validate(file: UploadFile = File(...)):
    try:
        base = Path(__file__).parent
        prompt_path = base / "prompt.json"
        with open(prompt_path) as f:
            prompt_data = json.load(f)

        system_prompt = prompt_data["system"]
        checklist     = prompt_data["checklist"]

        file_bytes = await file.read()
        soa_text   = extract_text(file_bytes)

        results = []
        for item in checklist:
            completion = client.chat.completions.create(
                model="gpt-4o-128k",       # use full 128k context
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": f"Checklist item: {item}\n\nSOA content:\n{soa_text}"}
                ]
            )
            text   = completion.choices[0].message.content.strip()
            bullets = [line.strip("•- \n") for line in text.split("\n") if line.strip()]
            results.append({"item": item, "points": bullets})

        return results

    except Exception as e:
        # Log to Render console
        print("⚠️ VALIDATION ERROR:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

# 2. Get current prompt (admin only)
@app.get("/prompt")
def get_prompt(auth: bool = Depends(check_admin)):
    base = Path(__file__).parent
    with open(base / "prompt.json") as f:
        return json.load(f)

# 3. Update prompt JSON (admin only)
@app.put("/prompt")
def update_prompt(new_prompt: dict, auth: bool = Depends(check_admin)):
    base = Path(__file__).parent
    with open(base / "prompt.json", "w") as f:
        json.dump(new_prompt, f, indent=2)
    return {"msg": "Prompt updated"}

# 4. Serve React frontend static files
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# 5. SPA catch-all for React Router (optional)
@app.get("/{full_path:path}")
async def spa_catch_all(full_path: str):
    return FileResponse(static_dir / "index.html")
