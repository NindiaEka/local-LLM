# Local LLM Gateway - Documentation Phase 4.1

Phase: Phase 4.1 - OpenAI-Compatible Streaming (Complete)
Previous Reference: Phase 1 and Phase 2 docs
Scope: Streaming for POST /v1/chat/completions only

---

## 1. Ringkasan

Milestone 4.1 menambahkan dukungan streaming untuk endpoint OpenAI-compatible:

- Endpoint tetap sama: POST /v1/chat/completions
- Mode non-stream tetap backward compatible
- Mode stream menggunakan SSE (text/event-stream)
- Layering dipertahankan:
  - Router: HTTP adapter (SSE framing + HTTP mapping)
  - OpenAI Service: protocol translation
  - Ollama Service: provider transport + stream parsing + normalization

---

## 2. Status Kompatibilitas

Perilaku lama tetap berjalan:

- complete() di OpenAI Service tidak diubah
- ask_ollama() dan ask_ollama_raw() tetap ada dan tetap dipakai untuk non-stream
- Authentication via Depends(verify_api_key) tetap sama
- Schema request existing tetap dipakai (field stream sudah ada)

Tambahan baru:

- ask_ollama_stream() di Ollama Service
- stream_complete() di OpenAI Service
- Router v1/chat/completions sekarang branch berdasarkan body.stream

---

## 3. Arsitektur Final Phase 4.1

Client
-> Router
-> OpenAI Service
-> Ollama Service
-> Ollama

### Tanggung Jawab Layer

1. Router
- Memilih mode non-stream vs stream
- Untuk stream: buat StreamingResponse
- Framing SSE: data: <json>\n\n
- Emit data: [DONE] sekali saat sukses
- Mapping domain exception -> HTTPException

2. OpenAI Service
- Menerjemahkan request OpenAI ke format internal call
- Menerjemahkan internal normalized chunk ke OpenAI-compatible chunk dict
- Menjaga request context immutable per stream:
  - request_id
  - created
  - model
- Tidak membuat SSE frame
- Tidak memakai StreamingResponse

3. Ollama Service
- Mengirim stream request ke /api/chat dengan stream=true
- Membaca response incremental
- Parse JSON tiap chunk
- Validasi basic field
- Yield normalized internal chunk

---

## 4. Alur Request

### Non-Stream (stream=false)

1. Client kirim POST /v1/chat/completions
2. Router validasi auth dependency
3. Router panggil openai_service.complete(body)
4. OpenAI Service panggil ask_ollama_raw()
5. Ollama Service panggil Ollama non-stream
6. Response diterjemahkan ke ChatCompletionResponse
7. JSON response dikembalikan ke client

### Stream (stream=true)

1. Client kirim POST /v1/chat/completions dengan stream=true
2. Router validasi auth dependency
3. Router membuat StreamingResponse(text/event-stream)
4. Generator router konsumsi openai_service.stream_complete(body)
5. OpenAI Service konsumsi ask_ollama_stream()
6. Ollama Service yield normalized internal chunks
7. OpenAI Service translate ke OpenAI-compatible chunk dict
8. Router serialize tiap chunk via json.dumps dan frame sebagai SSE
9. Setelah selesai sukses, router emit data: [DONE]

---

## 5. Kontrak Streaming Chunk

Setiap chunk yang keluar dari OpenAI Service berbentuk OpenAI-compatible dictionary:

- id
- object = chat.completion.chunk
- created
- model
- choices: list dengan item berisi:
  - index
  - delta
  - finish_reason

Router tidak menginspeksi konten delta/finish_reason. Router hanya serialize + frame.

---

## 6. Error Handling

### Domain Exceptions (Service Layer)

OpenAI streaming path mengangkat exception domain, bukan HTTP transport exception.

Sumber utama dari Ollama stream:
- koneksi gagal
- timeout
- upstream status error
- protocol/malformed chunk/interrupted stream

### HTTP Mapping (Router Layer)

Router memetakan domain exception menjadi HTTP status:

- connection -> 503
- timeout -> 504
- upstream/protocol -> 502

Ini menjaga boundary tetap bersih: service tidak tahu detail HTTP transport.

---

## 7. File yang Relevan di Phase 4.1

1. app/services/ollama_service.py
- Menambahkan streaming transport function + normalized chunk emission
- Menambahkan exception hierarchy untuk path stream/non-stream service-level

2. app/services/openai_service.py
- Menambahkan stream_complete() yang yield OpenAI chunk dictionaries
- Menambahkan streaming domain exceptions untuk boundary service
- complete() non-stream tetap dipertahankan

3. app/routers/v1/chat.py
- Menambahkan branch stream=false vs stream=true
- Menambahkan StreamingResponse untuk stream=true
- Menambahkan SSE framing dan [DONE]
- Menambahkan exception mapping domain -> HTTP

---

## 8. Contoh Perilaku API

### Request non-stream

POST /v1/chat/completions
body.stream = false

Hasil: 1 JSON response final (sama seperti sebelumnya)

### Request stream

POST /v1/chat/completions
body.stream = true

Hasil: SSE event stream:
- data: {chunk1}
- data: {chunk2}
- ...
- data: [DONE]

---

## 9. Checklist Verifikasi Manual

1. Non-stream regression
- Endpoint lama tetap memberi ChatCompletionResponse valid
- Status dan shape response tidak berubah

2. Streaming success
- Header response text/event-stream
- Muncul beberapa data: <json>
- [DONE] muncul tepat sekali di akhir

3. Streaming error path
- Jika Ollama mati -> 503
- Jika timeout -> 504
- Jika malformed/protocol/upstream -> 502

4. Auth
- Tanpa bearer token tetap gagal sesuai mekanisme existing

---

## 10. Next Milestone

Setelah Phase 4.1 stabil, langkah berikut yang direkomendasikan:

1. Embeddings endpoint (POST /v1/embeddings)
2. Model Registry internal + GET /v1/models
3. Shared domain error policy lintas chat, streaming, embeddings, models
4. Integration test matrix untuk stream success/failure/disconnect
