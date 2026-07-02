# Local LLM Gateway

Local LLM Gateway adalah platform yang berfungsi sebagai penghubung antara aplikasi chatbot dengan berbagai Large Language Model (LLM), baik model lokal maupun cloud.

Gateway ini dibuat agar aplikasi seperti OpenClaw dapat menggunakan berbagai model AI melalui satu endpoint yang kompatibel dengan OpenAI API.

---

# Tujuan

Project ini bertujuan untuk:

- Menggunakan model AI lokal tanpa bergantung pada layanan cloud.
- Menyediakan satu endpoint yang kompatibel dengan OpenAI API.
- Mempermudah integrasi berbagai aplikasi chatbot.
- Menjadi fondasi untuk pengembangan RAG (Retrieval Augmented Generation), multi-model, dan manajemen API Key.

---

# Arsitektur

```
                 +----------------+
                 |   OpenClaw UI  |
                 +-------+--------+
                         |
                         |
                 OpenAI Compatible API
                         |
                         v
               +---------------------+
               | Local LLM Gateway   |
               +---------------------+
                         |
          +--------------+---------------+
          |                              |
      Ollama Local                 Cloud Provider
      (Qwen, Gemma)              (OpenAI, Gemini, dll)
```

---

# Fitur Saat Ini

✅ API OpenAI Compatible

- Chat Completion
- Streaming Response (SSE)
- Model Listing
- API Key Authentication

✅ Integrasi OpenClaw

- Chat dapat berjalan melalui OpenClaw
- Mendukung streaming
- Mendukung pemilihan model

---

# Roadmap

v1.0

- Chat Completion
- API Key
- Model List
- OpenClaw Integration

v1.1

- Oracle RAG
- Knowledge Base
- Multi Model
- Dashboard sederhana

---

# Struktur Project

```
backend/
│
├── app/
│   ├── routers/
│   ├── services/
│   ├── schemas/
│   ├── middleware/
│   ├── database/
│   └── dependencies/
│
└── main.py

frontend/

OpenClaw (External UI)
```

---

# Cara Kerja Sistem

## 1. User membuka OpenClaw

OpenClaw digunakan sebagai antarmuka chatbot.

User cukup memasukkan:

- Base URL Gateway
- API Key

Setelah berhasil terhubung, OpenClaw akan mengirim seluruh request ke Local LLM Gateway.

---

## 2. Gateway menerima request

Gateway menerima request menggunakan format OpenAI API.

Contoh endpoint:

```
POST /v1/chat/completions
```

Gateway akan:

- Memvalidasi API Key
- Membaca model yang dipilih
- Mengubah request menjadi format internal

---

## 3. Gateway meneruskan ke LLM

Jika model lokal dipilih:

```
Gateway
      ↓
Ollama
      ↓
Qwen
```

Jika model cloud dipilih:

```
Gateway
      ↓
OpenAI
```

Tahapan ini bersifat transparan sehingga aplikasi tidak perlu mengetahui model yang digunakan.

---

## 4. Model menghasilkan jawaban

Model mengembalikan jawaban secara streaming.

Gateway kemudian mengubah format tersebut menjadi format OpenAI Streaming sehingga dapat dipahami oleh OpenClaw.

---

## 5. Jawaban ditampilkan

OpenClaw menerima hasil streaming dan menampilkan jawaban kepada pengguna secara real-time.

---

# API

## List Model

GET

```
/v1/models
```

Mengembalikan daftar model yang tersedia.

---

## Chat Completion

POST

```
/v1/chat/completions
```

Digunakan untuk mengirim percakapan ke model AI.

Mendukung:

- Streaming
- Non Streaming

---

# Model yang Didukung

Saat ini:

- Qwen2.5
- Gemma
- Mistral
- Llama

Model lain dapat ditambahkan melalui konfigurasi provider.

---

# API Key

Gateway menggunakan API Key untuk memastikan hanya pengguna yang memiliki akses yang dapat menggunakan layanan.

API Key dikirim melalui:

```
Authorization: Bearer <API_KEY>
```

---

# Rencana Pengembangan

Tahap berikutnya adalah menambahkan Retrieval Augmented Generation (RAG).

Dengan adanya RAG, AI tidak hanya menjawab berdasarkan pengetahuan bawaan model, tetapi juga dapat mengambil informasi dari dokumen atau basis pengetahuan perusahaan sehingga jawaban menjadi lebih relevan dan akurat.

---

# Cara Menjalankan Project

## 1. Jalankan Ollama

```
ollama serve
```

Pastikan model telah tersedia.

Contoh:

```
ollama list
```

---

## 2. Jalankan Backend

```
cd backend

uv run uvicorn app.main:app --reload
```

Backend akan berjalan pada:

```
http://localhost:8000
```

---

## 3. Jalankan OpenClaw

```
ollama launch openclaw
```

Masukkan:

Base URL

```
http://localhost:8000/v1
```

API Key

```
sk_local_xxxxxxxxx
```

Pilih model yang tersedia, kemudian chatbot siap digunakan.

---

# Status Project

Versi saat ini:

v1.0

Status:

🟢 Stable

OpenClaw berhasil terintegrasi dengan Local LLM Gateway menggunakan endpoint OpenAI Compatible.