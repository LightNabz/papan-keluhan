O-oi, Sharky! Y-you're making me explain *everything*? What am I, your personal assistant or something?! *blushes and fidgets* F-fine! I'll do it, but only because you're cute when you're coding seriously, not because I care or anything! Hmph!

Here's your `README.md` for your project **Papan Keluhan Siswa**, all nicely explained from the basics so even total newbies won't get lost~ 💻✨

---

```markdown
# 📝 Papan Keluhan Siswa

**Papan Keluhan Siswa** adalah aplikasi berbasis web sederhana menggunakan FastAPI dan Supabase, tempat siswa bisa mengirimkan keluhan atau masukan, baik secara anonim maupun dengan nama. Bisa juga melampirkan gambar sebagai bukti. Proyek ini bertujuan untuk belajar dan memperkenalkan backend dengan Python dan layanan Supabase sebagai BaaS (Backend as a Service).

---

## 🚀 Fitur

- Form pengaduan siswa (dengan opsi nama dan upload gambar)
- Menyimpan data di Supabase
- Melihat daftar keluhan terbaru di halaman utama
- Upload file ke Supabase Storage

---

## 🛠️ Teknologi

- [FastAPI](https://fastapi.tiangolo.com/) - Backend Web Framework
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine untuk HTML
- [httpx](https://www.python-httpx.org/) - Async HTTP client
- [Supabase](https://supabase.com/) - Backend as a Service
- [dotenv](https://pypi.org/project/python-dotenv/) - Untuk mengelola environment variables

---

## 📁 Struktur Proyek

```
papan-keluhan-siswa/
│
├── main.py                # File utama FastAPI
├── .env                   # File environment variables (SUPABASE_URL, KEY, dll)
├── static/
│   ├── index.html         # Template halaman utama
│   └── ...                # CSS, gambar, dll.
└── README.md              # Dokumentasi ini
```

---

## 💡 Penjelasan `main.py` (Kode Utama)

### Setup Awal
```python
app = FastAPI()
```
Ini bikin instance aplikasi FastAPI kita, duh.

```python
BASE_DIR = Path(__file__).resolve().parent
```
Biar tahu direktori kerja aplikasi sekarang (buat nyari file `static`/template).

```python
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=str(templates_dir))
```
Ini buat handle file statis dan template HTML.

```python
load_dotenv()
```
Ngambil variabel dari file `.env`, kayak `SUPABASE_URL` dan `SUPABASE_KEY`.

### Supabase Config

```python
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "note-uploads")
```
Ngambil info Supabase dari environment. Bucket ini tempat upload file gambar.

---

### 📄 Endpoint

#### GET `/notes`
```python
@app.get("/notes")
```
Ambil semua catatan dari tabel `notes` di Supabase dan tampilkan sebagai JSON.

#### GET `/`
```python
@app.get("/", response_class=HTMLResponse)
```
Render halaman utama (`index.html`) dan ambil data notes terbaru.

#### POST `/submit`
```python
@app.post("/submit")
```
Handle form kiriman dari pengguna:
- Simpan judul, isi, nama, dan gambar (kalau ada) ke Supabase
- Upload gambar ke storage Supabase
- Kalo sukses, redirect ke `/`

---

## 🔧 Cara Menjalankan Proyek

1. **Clone Repo-nya**
```bash
git clone https://github.com/kamu/papan-keluhan-siswa.git
cd papan-keluhan-siswa
```

2. **Buat Virtual Env & Install Dependency**
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
```

4. **Jalankan Server**
```bash
uvicorn main:app --reload
```
Akses di `http://127.0.0.1:8000`

---

## ✨ Pengembangan Selanjutnya

- 💬 Sistem komentar untuk tiap keluhan
- 🧾 Validasi input yang lebih baik
- 🛡️ Autentikasi siswa (biar gak spam!)
- 📱 Responsif & tampilan UI lebih manis pakai Tailwind
- 🔔 Notifikasi admin untuk keluhan baru
- 🗃️ Export laporan keluhan ke PDF atau Excel

---

## 👀 Screenshots (Kalau Ada)

_(Tambahkan gambar tampilan `index.html` dan form-nya biar makin kece!)_

---

## 📄 Lisensi

MIT License. Silakan forking dan pakai buat belajar atau proyek sejenis~