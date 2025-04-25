from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import httpx
import uuid
import os
import secrets
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO

app = FastAPI()
security = HTTPBasic()

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

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Authentication helper
def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    is_username_correct = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    is_password_correct = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

# Admin routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, credentials: HTTPBasicCredentials = Depends(verify_admin)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?select=*&order=created_at.desc",
            headers=headers
        )
        notes = res.json() if res.status_code == 200 else []

    response = templates.TemplateResponse("admin.html", {
        "request": request,
        "notes": notes
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.delete("/admin/delete/{note_id}")
async def delete_note(
    note_id: str,
    request: Request, 
    credentials: HTTPBasicCredentials = Depends(verify_admin)
):
    # Create headers with specific content types
    db_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"  # Add this for Supabase DELETE operations
    }
    
    storage_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        # Get note details
        get_res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?id=eq.{note_id}&select=*",
            headers=db_headers
        )
        
        if get_res.status_code != 200:
            return JSONResponse(
                content={"error": "Failed to fetch note"},
                status_code=404
            )
            
        notes = get_res.json()
        if not notes:
            return JSONResponse(
                content={"error": "Note not found"},
                status_code=404
            )
            
        note = notes[0]
        
        # Delete image if exists
        if note.get('image_url'):
            try:
                # Extract filename from URL
                filename = note['image_url'].split('/')[-1]
                
                # Delete from storage
                del_img_res = await client.delete(
                    f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}",
                    headers=storage_headers
                )
                
                # Log error but continue with note deletion
                if del_img_res.status_code not in [200, 404]:
                    print(f"Warning: Failed to delete image {filename}")
            except Exception as e:
                print(f"Error deleting image: {str(e)}")

        # Delete note from database
        del_res = await client.delete(
            f"{SUPABASE_URL}/rest/v1/notes?id=eq.{note_id}",
            headers=db_headers
        )
        
        if del_res.status_code not in [200, 204]:
            return JSONResponse(
                content={"error": "Failed to delete note"},
                status_code=500
            )
            
        return JSONResponse(content={"message": "Note deleted successfully"})

@app.get("/admin/download")
async def download_data(credentials: HTTPBasicCredentials = Depends(verify_admin)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?select=*&order=created_at.desc",
            headers=headers
        )
        
        if res.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch data")
            
        notes = res.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(notes)
        
        # Rename columns to be more readable
        column_names = {
            'id': 'No.',  # Changed from 'ID' to shorter 'No.'
            'created_at': 'Tanggal',  # Shortened from 'Tanggal Dibuat'
            'jenis_keluhan': 'Jenis Keluhan',
            'title': 'Judul',
            'content': 'Isi Keluhan',
            'name': 'Oleh',
            'image_url': 'Gambar'  # Shortened from 'URL Gambar'
        }
        df = df.rename(columns=column_names)

        # Format datetime
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.strftime('%d-%m-%Y')  # Removed time for shorter format
        
        # Shorten IDs to last 8 characters
        df['No.'] = df['No.'].apply(lambda x: x[-8:])
        
        # Shorten image URLs to just filename
        df['Gambar'] = df['Gambar'].apply(lambda x: x.split('/')[-1] if pd.notna(x) else '')

        # Create Excel file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"laporan_keluhan_{timestamp}.xlsx"
        # Use a platform-independent temporary directory
        import tempfile
        # Detect if running on Vercel
        if os.getenv("VERCEL"):
            temp_dir = "/tmp"
        else:
            temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)
        
        # Ensure the directory exists (tempfile.gettempdir() should exist, but just in case)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create Excel writer with xlsxwriter engine
        writer = pd.ExcelWriter(filepath, engine='xlsxwriter')
        
        # Write to Excel with styling, skip header and start at row 2
        df.to_excel(writer, sheet_name='Laporan Keluhan', index=False, header=False, startrow=2)
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Laporan Keluhan']
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#4B8BBE',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        cell_format = workbook.add_format({
            'font_size': 11,
            'border': 1,
            'align': 'left',
            'valign': 'top',
            'text_wrap': True
        })
        
        # Write header row at row 1
        worksheet.write_row(1, 0, df.columns, header_format)
        
        # Set column widths with updated sizes
        worksheet.set_column('A:A', 10)  # No. (shortened from 36)
        worksheet.set_column('B:B', 15)  # Judul
        worksheet.set_column('C:C', 50)  # Isi Keluhan
        worksheet.set_column('D:D', 20)  # Nama
        worksheet.set_column('E:E', 15)  # Gambar
        worksheet.set_column('F:F', 20)  # Jenis Keluhan
        worksheet.set_column('F:F', 15)  # Tanggal
        # Apply cell format to data rows starting from row 2
        for row in range(len(df)):
            for col in range(len(df.columns)):
                worksheet.write(row + 2, col, df.iloc[row, col], cell_format)
        
        # Add title
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center'
        })
        worksheet.merge_range('A1:F1', 'LAPORAN KELUHAN SISWA', title_format)
        
        # Save and close
        writer.close()
        
        # Return file
        return FileResponse(
            filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

@app.get("/admin/logout")
async def logout():
    return RedirectResponse(
        url="/",
        status_code=status.HTTP_302_FOUND,
        headers={"WWW-Authenticate": "Basic"}
    )

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
    jenis_keluhan: str = Form(...),
    image: UploadFile = File(None)
):
    image_url = None

    if image and image.filename:
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
        "jenis_keluhan": jenis_keluhan,
        "image_url": image_url
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{SUPABASE_URL}/rest/v1/notes", json=payload, headers=headers)
        print(f"Submit note response: {res.status_code}, {res.text}")  # Debug log

    if res.status_code == 201:
        return RedirectResponse(url="/", status_code=303)
    return JSONResponse(content={"error": "Failed to submit note"}, status_code=500)
