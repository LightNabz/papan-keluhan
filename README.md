# 📝 Papan Keluhan Siswa

**Papan Keluhan Siswa** adalah sebuah aplikasi berbasis web sederhana yang dikembangkan menggunakan FastAPI dan Supabase. Aplikasi ini dirancang sebagai platform bagi siswa untuk menyampaikan keluhan atau masukan, baik secara anonim maupun dengan mencantumkan nama. Selain itu, aplikasi ini juga memungkinkan pengguna untuk melampirkan gambar sebagai bukti pendukung. Proyek ini bertujuan untuk memberikan pengalaman belajar dalam pengembangan backend menggunakan Python serta memanfaatkan Supabase sebagai layanan Backend as a Service (BaaS).

---

## 🚀 Fitur

- Formulir pengaduan siswa dengan opsi untuk mencantumkan nama dan mengunggah gambar.
- Penyimpanan data keluhan di Supabase.
- Tampilan daftar keluhan terbaru di halaman utama.
- Fasilitas unggah file ke Supabase Storage.

---

## 🛠️ Teknologi

- [FastAPI](https://fastapi.tiangolo.com/) - Framework untuk pengembangan backend berbasis web.
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine untuk menghasilkan halaman HTML dinamis.
- [httpx](https://www.python-httpx.org/) - Klien HTTP asinkron untuk komunikasi dengan API eksternal.
- [Supabase](https://supabase.com/) - Layanan Backend as a Service (BaaS).
- [dotenv](https://pypi.org/project/python-dotenv/) - Library untuk mengelola variabel lingkungan (environment variables).

---

## 📁 Struktur Proyek

```
papan-keluhan-siswa/
│
├── main.py                # File utama aplikasi FastAPI
├── .env                   # File untuk menyimpan variabel lingkungan (SUPABASE_URL, KEY, dll.)
├── static/
│   ├── index.html         # Template halaman utama
│   └── ...                # File CSS, gambar, dan aset lainnya
└── README.md              # Dokumentasi proyek
```

---

## 💡 Penjelasan `main.py` (Kode Utama)

### Setup Awal
```python
app = FastAPI()
```
Kode ini membuat sebuah instance dari aplikasi FastAPI yang akan digunakan untuk mendefinisikan endpoint dan menjalankan server.

```python
BASE_DIR = Path(__file__).resolve().parent
```
Kode ini menentukan direktori kerja aplikasi saat ini. Variabel `BASE_DIR` digunakan untuk memastikan bahwa aplikasi dapat menemukan file statis dan template HTML dengan benar.

```python
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=str(templates_dir))
```
- `app.mount` digunakan untuk mengatur direktori file statis agar dapat diakses melalui URL. Misalnya, file CSS atau gambar.
- `Jinja2Templates` digunakan untuk menghubungkan aplikasi dengan template HTML yang akan dirender.

```python
load_dotenv()
```
Fungsi ini memuat variabel lingkungan dari file `.env`. Variabel ini biasanya berisi informasi sensitif seperti URL dan kunci API Supabase.

### Konfigurasi Supabase

```python
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "note-uploads")
```
- `SUPABASE_URL` adalah URL proyek Supabase Anda.
- `SUPABASE_KEY` adalah kunci API untuk mengakses layanan Supabase.
- `SUPABASE_BUCKET` adalah nama bucket di Supabase Storage tempat file gambar akan diunggah. Jika tidak ditentukan, nilai default adalah `note-uploads`.

---

### 📄 Endpoint

#### GET `/notes`
```python
@app.get("/notes")
```
Endpoint ini digunakan untuk mengambil semua catatan dari tabel `notes` di Supabase. Data akan dikembalikan dalam format JSON.

#### GET `/`
```python
@app.get("/", response_class=HTMLResponse)
```
Endpoint ini merender halaman utama (`index.html`) dan menampilkan daftar keluhan terbaru yang diambil dari database.

#### POST `/submit`
```python
@app.post("/submit")
```
Endpoint ini menangani pengiriman formulir dari pengguna. Proses yang dilakukan meliputi:
- Menyimpan data seperti judul, isi, nama, dan gambar (jika ada) ke tabel `notes` di Supabase.
- Mengunggah file gambar ke Supabase Storage.
- Jika berhasil, pengguna akan diarahkan kembali ke halaman utama (`/`).

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
- 🛡️ Menyediakan autentikasi siswa untuk mencegah spam.
- 📱 Membuat tampilan UI lebih responsif dan menarik menggunakan Tailwind CSS.
- 🔔 Menambahkan notifikasi untuk admin saat ada keluhan baru.
- 🗃️ Menyediakan fitur ekspor laporan keluhan ke format PDF atau Excel.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah MIT License. Anda bebas untuk melakukan forking dan menggunakan proyek ini untuk keperluan belajar atau pengembangan proyek serupa.