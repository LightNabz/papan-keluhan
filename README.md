# 📝 Papan Keluhan Siswa

**Papan Keluhan Siswa** adalah sebuah aplikasi berbasis web sederhana yang dikembangkan menggunakan FastAPI dan Supabase. Aplikasi ini dirancang sebagai platform bagi siswa untuk menyampaikan keluhan atau masukan, baik secara anonim maupun dengan mencantumkan nama. Selain itu, aplikasi ini juga memungkinkan pengguna untuk melampirkan gambar sebagai bukti pendukung. Proyek ini bertujuan untuk memberikan pengalaman belajar dalam pengembangan backend menggunakan Python serta memanfaatkan Supabase sebagai layanan Backend as a Service (BaaS).

---

## 🚀 Fitur

- Formulir pengaduan siswa dengan opsi untuk mencantumkan nama dan mengunggah gambar.
- Penyimpanan data keluhan di Supabase.
- Tampilan daftar keluhan terbaru di halaman utama.
- Fasilitas unggah file ke Supabase Storage.
- Notifikasi otomatis ke Discord (atau email) untuk laporan jenis "Perundungan".
- **Panel Admin** dengan autentikasi berbasis sesi untuk mengelola keluhan.
- **Panel Admin** Statistik keluhan berdasarkan jenis dan status.
- **Panel Admin** Penghapusan keluhan beserta gambar terkait.
- **Panel Admin** Unduh laporan keluhan dalam format Excel.
- **Panel Admin** Pembaruan status keluhan melalui endpoint khusus.

---

## 🛠️ Teknologi

- [FastAPI](https://fastapi.tiangolo.com/) - Framework untuk pengembangan backend berbasis web.
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine untuk menghasilkan halaman HTML dinamis.
- [httpx](https://www.python-httpx.org/) - Klien HTTP asinkron untuk komunikasi dengan API eksternal.
- [Supabase](https://supabase.com/) - Layanan Backend as a Service (BaaS).
- [dotenv](https://pypi.org/project/python-dotenv/) - Library untuk mengelola variabel lingkungan (environment variables).
- [pandas](https://pandas.pydata.org/) - Library untuk manipulasi data dan analisis.
- [xlsxwriter](https://xlsxwriter.readthedocs.io/) - Library untuk membuat file Excel dengan format khusus.

---

## 📁 Struktur Proyek

```
papan-keluhan-siswa/
│
├── main.py                # File utama aplikasi FastAPI
├── email_sender.py        # Modul untuk pengiriman email (opsional)
├── discord_sender.py      # Modul untuk pengiriman notifikasi Discord
├── .env                   # File untuk menyimpan variabel lingkungan (SUPABASE_URL, KEY, dll.)
├── static/
│   ├── index.html         # Template halaman utama
│   ├── admin.html         # Template dashboard admin
│   ├── admin_login.html   # Template halaman login admin
│   └── ...                # File CSS, gambar, dan aset lainnya
└── README.md              # Dokumentasi proyek
```

---

## 💡 Penjelasan `main.py` (Kode Utama)

Berikut adalah penjelasan baris demi baris untuk endpoint utama dalam `main.py`:

### Setup Awal dan Konfigurasi

```python
app = FastAPI()
```
Membuat instance FastAPI untuk aplikasi.

```python
BASE_DIR = Path(__file__).resolve().parent
```
Menentukan direktori kerja aplikasi.

```python
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=str(templates_dir))
```
Mengatur direktori file statis dan template HTML.

```python
load_dotenv()
```
Memuat variabel lingkungan dari file `.env`.

### Variabel Lingkungan dan Middleware

```python
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "note-uploads")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
```
Mengambil variabel lingkungan untuk Supabase dan admin.

```python
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "supersecretkey"))
```
Menambahkan middleware sesi untuk autentikasi admin berbasis sesi.

---

### Endpoint GET `/`

```python
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
```

- Mengambil daftar keluhan terbaru dari Supabase.
- Merender halaman `index.html` dengan data keluhan.

---

### Endpoint POST `/submit`

```python
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

    if image and image.filename:
        image_bytes = await image.read()
        filename = f"{uuid.uuid4()}_{image.filename}"
        async with httpx.AsyncClient() as client:
            res = await client.put(
                f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}",
                headers={**headers, "Content-Type": image.content_type},
                content=image_bytes
            )
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

    if res.status_code == 201:
        if jenis_keluhan.lower() == "perundungan":
            content = f"**Laporan Perundungan Baru**\n\nJudul: {title}\nIsi Keluhan: {content}\nOleh: {name}\nStatus: {status}"
            send_discord_report(content)
        return RedirectResponse(url="/", status_code=303)
    return JSONResponse(content={"error": "Failed to submit note"}, status_code=500)
```

- Menerima data keluhan dari form.
- Mengunggah gambar ke Supabase Storage jika ada.
- Menyimpan data keluhan ke tabel `notes` di Supabase.
- Mengirim notifikasi Discord jika jenis keluhan adalah "Perundungan".
- Mengarahkan pengguna kembali ke halaman utama jika berhasil.

---

### Endpoint GET `/notes`

```python
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
```

- Mengambil semua catatan keluhan dalam format JSON.
- Mengembalikan error jika gagal mengambil data.

---

### Endpoint GET `/admin/login` dan POST `/admin/login`

```python
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
```

- Menampilkan halaman login admin.
- Memproses login dan menyimpan status login di sesi.
- Mengarahkan ke dashboard admin jika berhasil, atau menampilkan error jika gagal.

---

### Endpoint GET `/admin`

```python
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

    total_notes = len(notes)
    jenis_keluhan_counts = {"Perundungan": 0, "Sarana/prasarana": 0, "Saran": 0}
    status_counts = {"Sedang diproses": 0, "Menunggu Respon": 0, "Telah ditindaklanjuti": 0}

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
```

- Memeriksa status login admin.
- Mengambil data keluhan dari Supabase.
- Menghitung statistik jenis keluhan dan status.
- Merender halaman dashboard admin dengan data dan statistik.

---

### Endpoint DELETE `/admin/delete/{note_id}`

```python
@app.delete("/admin/delete/{note_id}")
async def delete_note(
    note_id: str,
    request: Request,
):
    if not request.session.get("admin_logged_in"):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    db_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    storage_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    async with httpx.AsyncClient() as client:
        get_res = await client.get(
            f"{SUPABASE_URL}/rest/v1/notes?id=eq.{note_id}&select=*",
            headers=db_headers
        )
        if get_res.status_code != 200:
            return JSONResponse(content={"error": "Failed to fetch note"}, status_code=404)

        notes = get_res.json()
        if not notes:
            return JSONResponse(content={"error": "Note not found"}, status_code=404)

        note = notes[0]

        if note.get('image_url'):
            try:
                filename = note['image_url'].split('/')[-1]
                del_img_res = await client.delete(
                    f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}",
                    headers=storage_headers
                )
                if del_img_res.status_code not in [200, 404]:
                    print(f"Warning: Failed to delete image {filename}")
            except Exception as e:
                print(f"Error deleting image: {str(e)}")

        del_res = await client.delete(
            f"{SUPABASE_URL}/rest/v1/notes?id=eq.{note_id}",
            headers=db_headers
        )
        if del_res.status_code not in [200, 204]:
            return JSONResponse(content={"error": "Failed to delete note"}, status_code=500)

        return JSONResponse(content={"message": "Note deleted successfully"})
```

- Memeriksa status login admin.
- Mengambil data keluhan berdasarkan `note_id`.
- Menghapus gambar terkait dari Supabase Storage jika ada.
- Menghapus data keluhan dari Supabase.
- Mengembalikan pesan sukses atau error.

---

### Endpoint PATCH `/admin/update_status/{note_id}`

```python
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
    if res.status_code in [200, 204]:
        return JSONResponse(content={"message": "Status updated successfully"})
    else:
        error_detail = res.text
        return JSONResponse(content={"error": f"Failed to update status: {error_detail}"}, status_code=500)
```

- Memeriksa status login admin.
- Memperbarui status keluhan berdasarkan `note_id`.
- Mengembalikan pesan sukses atau error.

---

### Endpoint GET `/admin/download`

```python
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
        df = pd.DataFrame(notes)
        column_names = {
            'id': 'No.',
            'created_at': 'Tanggal',
            'jenis_keluhan': 'Jenis Keluhan',
            'title': 'Judul',
            'content': 'Isi Keluhan',
            'name': 'Oleh',
            'image_url': 'Gambar',
            'status': 'Status'
        }
        df = df.rename(columns=column_names)
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.strftime('%d-%m-%Y')
        df['No.'] = df['No.'].apply(lambda x: x[-8:])
        df['Gambar'] = df['Gambar'].apply(lambda x: x.split('/')[-1] if pd.notna(x) else '')

        import tempfile
        if os.getenv("VERCEL"):
            temp_dir = "/tmp"
        else:
            temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, f"laporan_keluhan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        os.makedirs(temp_dir, exist_ok=True)

        writer = pd.ExcelWriter(filepath, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Laporan Keluhan', index=False, header=False, startrow=2)
        workbook = writer.book
        worksheet = writer.sheets['Laporan Keluhan']

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
        worksheet.write_row(1, 0, df.columns, header_format)
        worksheet.set_column('A:A', 10)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 50)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 25)
        for row in range(len(df)):
            for col in range(len(df.columns)):
                worksheet.write(row + 2, col, df.iloc[row, col], cell_format)

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center'
        })

        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'id_ID.utf8')
        except:
            locale.setlocale(locale.LC_TIME, 'C')

        tanggal_laporan = datetime.now().strftime('%d %B %Y')
        judul_laporan = f"LAPORAN KELUHAN SISWA {tanggal_laporan.upper()}"
        worksheet.merge_range('A1:H1', judul_laporan, title_format)

        writer.close()

        return FileResponse(
            filepath,
            filename=os.path.basename(filepath),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
```

- Memeriksa status login admin.
- Mengambil data keluhan dari Supabase.
- Mengubah data menjadi DataFrame pandas dan memformat kolom.
- Membuat file Excel dengan styling menggunakan xlsxwriter.
- Mengembalikan file Excel sebagai response untuk diunduh.

---

### Endpoint GET `/admin/logout`

```python
@app.get("/admin/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
```

- Menghapus sesi login admin.
- Mengarahkan ke halaman login admin.

---

Penjelasan ini memberikan gambaran rinci tentang fungsi setiap endpoint utama dalam aplikasi.
BASE_DIR = Path(__file__).resolve().parent

---

## 📄 Endpoint

#### GET `/`
Menampilkan halaman utama dengan daftar keluhan terbaru.

#### POST `/submit`
Menerima pengiriman keluhan baru, termasuk judul, isi, nama, jenis keluhan, status, dan gambar (opsional). Jika jenis keluhan adalah "Perundungan", akan mengirim notifikasi ke Discord (atau Email bila memilih opsi email).

#### GET `/notes`
Mengambil semua catatan keluhan dalam format JSON.

#### Admin Panel

- GET `/admin/login` dan POST `/admin/login`  
  Halaman login admin dengan autentikasi berbasis sesi.

- GET `/admin`  
  Dashboard admin yang menampilkan daftar keluhan, statistik jenis keluhan dan status.

- DELETE `/admin/delete/{note_id}`  
  Menghapus keluhan beserta gambar terkait.

- PATCH `/admin/update_status/{note_id}`  
  Memperbarui status keluhan.

- GET `/admin/download`  
  Mengunduh laporan keluhan dalam format Excel.

- GET `/admin/logout`  
  Logout dari panel admin.

---

## 🔔 Notifikasi

Notifikasi otomatis dikirim ke Discord webhook untuk laporan jenis "Perundungan" menggunakan modul `discord_sender.py`. Modul ini mengirim pesan ke URL webhook Discord yang disimpan dalam variabel lingkungan `DISCORD_WEBHOOK_URL`. Berikut adalah ringkasan fungsinya:

- Fungsi `send_discord_report(content: str)` mengirimkan konten pesan ke Discord.
- Jika pengiriman berhasil (status 204), akan mencetak pesan sukses.
- Jika gagal, mencetak status dan respons error.
- Menangani exception dan mencetak pesan error jika terjadi.

Modul `email_sender.py` juga tersedia untuk pengiriman email (opsional dan dapat diaktifkan sesuai kebutuhan).

### Mengganti Notifikasi dari Discord ke Email

Untuk mengganti notifikasi pengiriman laporan dari Discord webhook ke email pada endpoint `/submit`, lakukan langkah-langkah berikut:

1. Buka file `main.py`.
2. Cari bagian import dan ubah:
```python
# from email_sender import send_email_report
from discord_sender import send_discord_report
```
Menjadi:
```python
from email_sender import send_email_report
# from discord_sender import send_discord_report
```

3. Pada fungsi `submit_note` di `main.py`, cari bagian pengiriman notifikasi setelah berhasil submit keluhan:
```python
if jenis_keluhan.lower() == "perundungan":
    # Yang ini untuk discord webhook
    content = f"**Laporan Perundungan Baru**\n\nJudul: {title}\nIsi Keluhan: {content}\nOleh: {name}\nStatus: {status}"
    send_discord_report(content)
    # Yang di comment ini pakai method email
    # subject = "Laporan Perundungan Baru"
    # body = f"Judul: {title}\nIsi Keluhan: {content}\nOleh: {name}\nStatus: {status}"
    # send_email_report(subject, body)
```
Ubah menjadi:
```python
if jenis_keluhan.lower() == "perundungan":
    subject = "Laporan Perundungan Baru"
    body = f"Judul: {title}\nIsi Keluhan: {content}\nOleh: {name}\nStatus: {status}"
    send_email_report(subject, body)
    # send_discord_report(content)  # Nonaktifkan notifikasi Discord jika tidak digunakan
```

4. Pastikan variabel lingkungan untuk email sudah diatur di file `.env`:
```dotenv
SENDER_EMAIL=your_sender_email@example.com
RECEIVER_EMAIL=your_receiver_email@example.com
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_PASSWORD=your_smtp_password
```

5. Install library `smtplib` sudah termasuk di Python standar, jadi tidak perlu instalasi tambahan.

Dengan langkah ini, notifikasi akan dikirim melalui email, bukan Discord webhook.
    # send_email_report(subject, body)

SMTP_PASSWORD=your_smtp_password
    # send_discord_report(content)  # Nonaktifkan notifikasi Discord jika tidak digunakan
# from discord_sender import send_discord_report
from discord_sender import send_discord_report

---

## 🔧 Cara Menjalankan Proyek

1. **Clone Repositori**
```bash
git clone https://github.com/LightNabz/papan-keluhan.git
cd papan-keluhan-siswa
```

2. **Buat Virtual Environment & Install Dependency**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Buat File `.env`**
```dotenv
SUPABASE_URL=https://abcxyz.supabase.co
SUPABASE_KEY=your-secret-api-key
SUPABASE_BUCKET=note-uploads
ADMIN_USERNAME=admin
ADMIN_PASSWORD=yourpassword
```

Tambahkan ini ke .env bila memakai email:
```dotenv
SENDER_EMAIL=pengirim@gmail.com
RECEIVER_EMAIL=penerima@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_PASSWORD=isi-di-sini-owo
```

Tambahkan ini ke .env bila memakai discord webhook:
```dotenv
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/ID_WEBHOOK/WEBHOOK_TOKEN
```
4. **Jalankan Server**
```bash
uvicorn main:app --reload
```
Akses aplikasi di `http://127.0.0.1:8000`.

---

## ✨ Pengembangan Selanjutnya

- 💬 Menambahkan sistem komentar untuk setiap keluhan.
- 🧾 Validasi input yang lebih ketat.
- 📱 Membuat tampilan UI lebih responsif dan menarik menggunakan framework JS seperti Tailwind CSS atau NextJS.
- ~~🔔 Menambahkan notifikasi untuk admin saat ada keluhan baru.~~
- ~~🗃️ Menyediakan fitur ekspor laporan keluhan ke format PDF atau Excel.~~


---

## 📄 Lisensi

Proyek ini dilisensikan di bawah MIT License. Anda bebas untuk melakukan forking dan menggunakan proyek ini untuk keperluan belajar atau pengembangan proyek serupa.
