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
import openai  # old v0.28 import

# 1) Load env
load_dotenv()

# 2) FastAPI + CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3) OpenAI global setup
openai.api_key = os.getenv("OPENAI_API_KEY")

# 4) Admin auth
security = HTTPBasic()
ADMIN_USER = "admin"
ADMIN_PASS = os.getenv("ADMIN_PASS", "secret123")

def check_admin(creds: HTTPBasicCredentials = Depends(security)):
    if creds.username == ADMIN_USER and creds.password == ADMIN_PASS:
        return True
    raise HTTPException(401, "Unauthorized")

# 5) .docx → text
def extract_text(bytes_data: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(bytes_data)
        tmp.seek(0)
        doc = Document(tmp.name)
    return "\n".join(p.text for p in doc.paragraphs)

# 6) /validate endpoint
@app.post("/validate")
async def validate(file: UploadFile = File(...)):
    try:
        base = Path(__file__).parent
        prompt = json.loads((base / "prompt.json").read_text())
        system   = prompt["system"]
        checklist = prompt["checklist"]

        soa_text = extract_text(await file.read())

        results = []
        for item in checklist:
            resp = openai.ChatCompletion.create(
                model="gpt-4o",     # revert to a model you have access to
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": f"Checklist item: {item}\n\nSOA content:\n{soa_text}"}
                ]
            )
            text = resp.choices[0].message.content.strip()
            bullets = [ln.strip("•- \n") for ln in text.splitlines() if ln.strip()]
            results.append({"item": item, "points": bullets})

        return results

    except Exception as e:
        # This will now correctly return status 500 with a JSON body
        return JSONResponse(status_code=500, content={"error": str(e)})

# 7) /prompt GET & PUT (admin only)
@app.get("/prompt")
def get_prompt(ok: bool = Depends(check_admin)):
    base = Path(__file__).parent
    return json.loads((base / "prompt.json").read_text())

@app.put("/prompt")
def set_prompt(new_prompt: dict, ok: bool = Depends(check_admin)):
    base = Path(__file__).parent
    (base / "prompt.json").write_text(json.dumps(new_prompt, indent=2))
    return {"msg": "Prompt updated"}

# 8) Serve frontend
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# 9) SPA catch-all
@app.get("/{full_path:path}")
async def spa(full_path: str):
    return FileResponse(static_dir / "index.html")
