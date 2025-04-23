from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import httpx
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "note-uploads")

# Validate environment variables
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set.")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

@app.get("/notes")
async def get_notes():
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?select=*&order=created_at.desc",
            headers=headers
        )
        if res.status_code == 200:
            return JSONResponse(content=res.json())
        return JSONResponse(content={"error": "Failed to fetch notes"}, status_code=500)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?select=*&order=created_at.desc",
            headers=headers
        )
        notes = res.json() if res.status_code == 200 else []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "notes": notes
    })

@app.post("/submit")
async def submit_note(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    name: str = Form("Anon"),
    image: UploadFile = File(None)
):
    image_url = None

    if image:
        image_bytes = await image.read()
        filename = f"{uuid.uuid4()}_{image.filename}"
        async with httpx.AsyncClient() as client:
            res = await client.put(
                f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}",
                headers={**headers, "Content-Type": image.content_type},
                content=image_bytes
            )
        print(f"Upload image response: {res.status_code}, {res.text}")  # Debug log
        if res.status_code == 200:
            image_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"

    payload = {
        "title": title,
        "content": content,
        "name": name,
        "image_url": image_url
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{SUPABASE_URL}/rest/v1/notes", json=payload, headers=headers)
        print(f"Submit note response: {res.status_code}, {res.text}")  # Debug log

    if res.status_code == 201:
        return RedirectResponse(url="/", status_code=303)
    return JSONResponse(content={"error": "Failed to submit note"}, status_code=500)