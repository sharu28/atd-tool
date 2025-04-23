import os
import json
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from docx import Document
import openai
from pathlib import Path
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()  # Load .env variables

# Initialize FastAPI app
app = FastAPI()

# Allow frontend calls (TODO: tighten for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI setup
openai.api_key = os.getenv("OPENAI_API_KEY")

# Admin auth
security = HTTPBasic()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "secret123")  # fallback default

def check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")

# Extract SOA text from uploaded docx
def extract_text(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file_bytes)
        tmp.seek(0)
        doc = Document(tmp.name)
    return "\n".join([p.text for p in doc.paragraphs])

# Validate SOA using checklist and GPT
@app.post("/validate")
async def validate(file: UploadFile = File(...)):
    try:
        base_path = Path(__file__).parent
        with open(base_path / "prompt.json") as f:
            prompt_data = json.load(f)

        system_prompt = prompt_data["system"]
        checklist = prompt_data["checklist"]

        file_bytes = await file.read()
        soa_text = extract_text(file_bytes)

        results = []
        for item in checklist:
            completion = openai.chat.completions.create(
                model="gpt-4o",
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Checklist item: {item}\n\nSOA content:\n{soa_text[:12000]}"}
                ]
            )
            response = completion.choices[0].message.content.strip()
            bullets = [line.strip("•- \n") for line in response.split("\n") if line.strip()]
            results.append({
                "item": item,
                "points": bullets
            })

        return results

    except Exception as e:
        print("⚠️ BACKEND ERROR:", str(e))  # This prints to Render logs
        return JSONResponse(status_code=500, content={"error": str(e)})

# Admin: Get current prompt
@app.get("/prompt")
def get_prompt(auth: bool = Depends(check_admin)):
    base_path = Path(__file__).parent
    with open(base_path / "prompt.json") as f:
        return json.load(f)

# Admin: Update prompt
@app.put("/prompt")
def update_prompt(new_prompt: dict, auth: bool = Depends(check_admin)):
    base_path = Path(__file__).parent
    with open(base_path / "prompt.json", "w") as f:
        json.dump(new_prompt, f, indent=2)
    return {"msg": "Prompt updated"}

# Serve frontend
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
