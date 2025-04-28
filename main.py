from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
# from email_sender import send_email_report
from discord_sender import send_discord_report # Bisa diganti disini kalau mw pakai email atau discord webhook
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import httpx
import uuid
import os
import secrets
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO
import locale

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

# Add session middleware with a secret key
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "supersecretkey"))

# Authentication helper for HTTP Basic (keep for other uses)
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

# New login page GET route
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_get(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})

# New login page POST route
@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["admin_logged_in"] = True
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid username or password"})

# Modified admin dashboard route to check session instead of HTTP Basic Auth
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not request.session.get("admin_logged_in"):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?select=*&order=created_at.desc",
            headers=headers
        )
        notes = res.json() if res.status_code == 200 else []

    # Compute statistics
    total_notes = len(notes)
    jenis_keluhan_counts = {
        "Perundungan": 0,
        "Sarana/prasarana": 0,
        "Saran": 0
    }
    status_counts = {
        "Sedang diproses": 0,
        "Menunggu Respon": 0,
        "Telah ditindaklanjuti": 0,
        "Ditolak": 0
    }

    for note in notes:
        jk = note.get("jenis_keluhan")
        st = note.get("status")
        if jk in jenis_keluhan_counts:
            jenis_keluhan_counts[jk] += 1
        if st in status_counts:
            status_counts[st] += 1

    response = templates.TemplateResponse("admin.html", {
        "request": request,
        "notes": notes,
        "total_notes": total_notes,
        "jenis_keluhan_counts": jenis_keluhan_counts,
        "status_counts": status_counts
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.get("/admin/statistics")
async def admin_statistics(request: Request):
    if not request.session.get("admin_logged_in"):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?select=*&order=created_at.desc",
            headers=headers
        )
        notes = res.json() if res.status_code == 200 else []

    total_notes = len(notes)
    jenis_keluhan_counts = {
        "Perundungan": 0,
        "Sarana/prasarana": 0,
        "Saran": 0
    }
    status_counts = {
        "Sedang diproses": 0,
        "Menunggu Respon": 0,
        "Telah ditindaklanjuti": 0,
        "Ditolak": 0
    }

    for note in notes:
        jk = note.get("jenis_keluhan")
        st = note.get("status")
        if jk in jenis_keluhan_counts:
            jenis_keluhan_counts[jk] += 1
        if st in status_counts:
            status_counts[st] += 1

    return JSONResponse(content={
        "total_notes": total_notes,
        "jenis_keluhan_counts": jenis_keluhan_counts,
        "status_counts": status_counts
    })

@app.delete("/admin/delete/{note_id}")
async def delete_note(
    note_id: str,
    request: Request, 
    # Remove HTTP Basic Auth dependency here since session is used
):
    if not request.session.get("admin_logged_in"):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

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
async def download_data(request: Request):
    if not request.session.get("admin_logged_in"):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

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
            'id': 'No.',
            'created_at': 'Tanggal',
            'jenis_keluhan': 'Jenis Keluhan',
            'title': 'Judul',
            'content': 'Isi Keluhan',
            'name': 'Oleh',
            'image_url': 'Gambar' ,
            'status': 'Status'
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
        worksheet.set_column('G:G', 15)  # Tanggal
        worksheet.set_column('H:H', 25)  # Status
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

        # Header OwO
        try:
            locale.setlocale(locale.LC_TIME, 'id_ID.utf8')
        except:
            # fallback kalau locale gak tersedia di server
            locale.setlocale(locale.LC_TIME, 'C')

        tanggal_laporan = datetime.now().strftime('%d %B %Y')
        judul_laporan = f"LAPORAN KELUHAN SISWA {tanggal_laporan.upper()}"

        worksheet.merge_range('A1:H1', judul_laporan, title_format)
        
        # Save and close
        writer.close()
        
        # Return file
        return FileResponse(
            filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

@app.get("/admin/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

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

from pydantic import BaseModel

class StatusUpdate(BaseModel):
    status: str

@app.patch("/admin/update_status/{note_id}")
async def update_note_status(
    note_id: str,
    status_update: StatusUpdate,
    request: Request
):
    if not request.session.get("admin_logged_in"):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    status = status_update.status
    async with httpx.AsyncClient() as client:
        url = f'{SUPABASE_URL}/rest/v1/notes'
        params = {"id": f"eq.{note_id}"}
        res = await client.patch(
            url,
            params=params,
            json={"status": status},
            headers={**headers, "Content-Type": "application/json", "Prefer": "return=representation"},
        )
        print(f"Update status response: {res.status_code}, {res.text}")  # Debug log
    if res.status_code in [200, 204]:
        return JSONResponse(content={"message": "Status updated successfully"})
    else:
        error_detail = res.text
        return JSONResponse(content={"error": f"Failed to update status: {error_detail}"}, status_code=500)

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_get(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["admin_logged_in"] = True
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid username or password"})

@app.post("/submit")
async def submit_note(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    name: str = Form("Anon"),
    jenis_keluhan: str = Form(...),
    status: str = Form("Menunggu Respon"),
    image: UploadFile = File(None)
):
    image_url = None
    tgl_laporan_perundungan = datetime.now().strftime('%d %B %Y')
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
        "status": status,
        "image_url": image_url
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{SUPABASE_URL}/rest/v1/notes", json=payload, headers=headers)
        print(f"Submit note response: {res.status_code}, {res.text}")  # Debug log

    if res.status_code == 201:
        if jenis_keluhan.lower() == "perundungan":
            # Yang ini untuk discord webhook
            # Comment ini bila memakai method email
            content = f"\n**Laporan Perundungan Baru ({tgl_laporan_perundungan}):**\n\n**Judul:** {title}\n\n**Isi:**\n{content}\n\n**Oleh:** {name}\n\n**Status:** *{status}*\n"
            send_discord_report(content)
            # Yang di comment ini pakai method email
            # subject = "Laporan Perundungan Baru"
            # body = f"Judul: {title}\nIsi Keluhan: {content}\nOleh: {name}\nStatus: {status}"
            # send_email_report(subject, body)
        return RedirectResponse(url="/", status_code=303)
    return JSONResponse(content={"error": "Failed to submit note"}, status_code=500)

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
