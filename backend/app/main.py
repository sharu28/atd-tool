from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import json
from docx import Document
from openai import OpenAI
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file

security = HTTPBasic()

app = FastAPI()

# Let React frontend call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: lock this down later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file_bytes)
        tmp.seek(0)
        doc = Document(tmp.name)
    return "\n".join([p.text for p in doc.paragraphs])

@app.post("/validate")
async def validate(file: UploadFile = File(...)):
    # Step 1: Load the prompt
    with open("app/prompt.json") as f:
        prompt_data = json.load(f)
    system_prompt = prompt_data["system"]
    checklist = prompt_data["checklist"]

    # Step 2: Extract text from uploaded .docx
    file_bytes = await file.read()
    soa_text = extract_text(file_bytes)

    # Step 3: Ask GPT for each checklist item
    results = []
    for item in checklist:
        completion = client.chat.completions.create(
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

# Set this once in your env or hardcode for now
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "secret123")  # ← replace or set in Render later

def check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/prompt")
def get_prompt(auth: bool = Depends(check_admin)):
    with open("app/prompt.json") as f:
        return json.load(f)

@app.put("/prompt")
def update_prompt(new_prompt: dict, auth: bool = Depends(check_admin)):
    with open("app/prompt.json", "w") as f:
        json.dump(new_prompt, f, indent=2)
    return {"msg": "Prompt updated"}
