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

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI()  # picks up OPENAI_API_KEY

security = HTTPBasic()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "secret123")

def check_admin(creds: HTTPBasicCredentials = Depends(security)):
    if creds.username == ADMIN_USERNAME and creds.password == ADMIN_PASSWORD:
        return True
    raise HTTPException(401, "Unauthorized")

def extract_text(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file_bytes)
        tmp.seek(0)
        doc = Document(tmp.name)
    return "\n".join(p.text for p in doc.paragraphs)

@app.post("/validate")
async def validate(file: UploadFile = File(...)):
    try:
        base = Path(__file__).parent
        with open(base / "prompt.json") as f:
            prompt = json.load(f)

        system = prompt["system"]
        checklist = prompt["checklist"]

        soa = extract_text(await file.read())
        results = []
        for item in checklist:
            resp = client.chat.completions.create(
                model="gpt-4o-128k",
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Checklist item: {item}\n\nSOA content:\n{soa}"}
                ]
            )
            text = resp.choices[0].message.content.strip()
            bullets = [l.strip("•- ") for l in text.splitlines() if l.strip()]
            results.append({"item": item, "points": bullets})

        return results

    except Exception as e:
        print("ERROR:", e)
        return JSONResponse(500, {"error": str(e)})

@app.get("/prompt")
def get_prompt(auth=Depends(check_admin)):
    base = Path(__file__).parent
    return json.load(open(base / "prompt.json"))

@app.put("/prompt")
def update_prompt(new: dict, auth=Depends(check_admin)):
    base = Path(__file__).parent
    with open(base / "prompt.json", "w") as f:
        json.dump(new, f, indent=2)
    return {"msg": "Prompt updated"}

static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/{full_path:path}")
async def spa(full_path: str):
    return FileResponse(static_dir / "index.html")
