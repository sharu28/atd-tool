# main.py (backend)

import os
import json
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from docx import Document
from openai import OpenAI

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

client = OpenAI()  # uses OPENAI_API_KEY
security = HTTPBasic()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "secret123")

BASE_DIR    = Path(__file__).parent
PROMPT_FILE = BASE_DIR / "prompt.json"

def check_admin(cred: HTTPBasicCredentials = Depends(security)):
    if cred.username == ADMIN_USERNAME and cred.password == ADMIN_PASSWORD:
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
        prompt_data   = json.loads(PROMPT_FILE.read_text())
        system_prompt = prompt_data["system"]

        soa_text = extract_text(await file.read())[:120000]  # cap to 120k chars

        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
Return a JSON object EXACTLY like this:
{{
  "CLIENT_INFORMATION": [],
  "FIGURES_AND_VALUES": [],
  "TYPOGRAPHY_AND_LANGUAGE": []
}}

• Each array element must be an object with "issue" and "details".  
• If no issues in a category, leave the array empty.

SOA to analyse:
```txt
{soa_text}
```"""}
            ],
            timeout=120,
        )

        result = resp.choices[0].message.content
        # If the SDK already returned a dict, just return it
        if isinstance(result, dict):
            return result

        # Otherwise parse the JSON string
        return json.loads(result)

    except Exception as e:
        print("⚠️ VALIDATION ERROR:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

# Admin endpoints

@app.get("/prompt")
def get_prompt(_: bool = Depends(check_admin)):
    return json.loads(PROMPT_FILE.read_text())

@app.put("/prompt")
def update_prompt(new: dict, _: bool = Depends(check_admin)):
    PROMPT_FILE.write_text(json.dumps(new, indent=2))
    return {"msg": "Prompt updated"}

# Serve React build

static_dir = BASE_DIR / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/{full_path:path}")
def spa(full_path: str):
    return FileResponse(static_dir / "index.html")
