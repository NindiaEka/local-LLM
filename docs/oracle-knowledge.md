# Sprint 3 - Oracle AI Knowledge Base Foundation

## Tujuan Sprint

Sprint ini bertujuan untuk menyiapkan Oracle AI Database agar mampu menghasilkan embedding secara lokal menggunakan model ONNX, menyimpan embedding ke dalam kolom VECTOR, serta menjadi fondasi Knowledge Base yang akan digunakan oleh Gateway dan OpenClaw.

Setelah Sprint 3 selesai, Oracle akan memiliki kemampuan:

- Menjalankan model embedding secara lokal.
- Menghasilkan vector embedding melalui SQL.
- Menyimpan vector ke dalam tabel.
- Melakukan similarity search.

---

# Arsitektur

OpenClaw
        │
        ▼
Gateway (FastAPI)
        │
        ▼
Oracle AI Database 26ai
        │
        ├── ONNX Model
        ├── VECTOR_EMBEDDING()
        ├── VECTOR datatype
        └── VECTOR_DISTANCE()

---

# Prasyarat

Pastikan:

- Oracle AI Database 26ai sudah berjalan di Docker.
- Docker Desktop aktif.
- SQL*Plus dapat digunakan.
- User aplikasi sudah dibuat (LLM_GATEWAY).
- Package DBMS_VECTOR tersedia.

---

# STEP 1 - Menjalankan Oracle Database

Cek container

```bash
docker ps
```

Pastikan terdapat container

```
oracle26ai
```

Masuk ke container

```bash
docker exec -it oracle26ai bash
```

Masuk ke SQLPlus

```bash
sqlplus system/Oracle123@FREEPDB1
```

---

# STEP 2 - Membuat User Aplikasi

Jalankan sebagai SYSTEM

```sql
CREATE USER llm_gateway
IDENTIFIED BY Oracle123
DEFAULT TABLESPACE USERS
QUOTA UNLIMITED ON USERS;
```

Berikan hak akses

```sql
GRANT CONNECT, RESOURCE TO llm_gateway;

GRANT CREATE MINING MODEL TO llm_gateway;
```

---

# STEP 3 - Verifikasi DBMS_VECTOR

Masih menggunakan SYSTEM

```sql
SELECT object_name, object_type
FROM all_objects
WHERE object_name='DBMS_VECTOR';
```

Output yang diharapkan

```
DBMS_VECTOR
PACKAGE
```

---

# STEP 4 - Download Model ONNX Oracle

Download model resmi Oracle.

Contoh

```
all_MiniLM_L12_v2.onnx
```

Catatan

Jangan menggunakan model ONNX biasa dari HuggingFace.

Gunakan model Oracle yang sudah di-augment agar kompatibel dengan VECTOR_EMBEDDING().

---

# STEP 5 - Copy Model ke Docker

Misal file berada di

```
C:\Users\<username>\Downloads\all_MiniLM_L12_v2.onnx
```

Copy

```powershell
docker cp C:\Users\<username>\Downloads\all_MiniLM_L12_v2.onnx oracle26ai:/opt/oracle/oradata/
```

Verifikasi

```bash
docker exec -it oracle26ai bash
```

```bash
ls -lh /opt/oracle/oradata/
```

Pastikan muncul

```
all_MiniLM_L12_v2.onnx
```

---

# STEP 6 - Membuat DIRECTORY Oracle

Masuk SQLPlus sebagai SYSTEM

```sql
CREATE OR REPLACE DIRECTORY ONNX_DIR
AS '/opt/oracle/oradata';
```

Berikan hak akses

```sql
GRANT READ, WRITE
ON DIRECTORY ONNX_DIR
TO LLM_GATEWAY;
```

---

# STEP 7 - Login ke User Aplikasi

PENTING

Model harus di-load menggunakan user aplikasi.

Login

```sql
CONN llm_gateway/Oracle123@FREEPDB1
```

Pastikan

```sql
SHOW USER;
```

Output

```
USER is "LLM_GATEWAY"
```

---

# STEP 8 - Load Model ONNX

```sql
BEGIN
    DBMS_VECTOR.LOAD_ONNX_MODEL(
        directory  => 'ONNX_DIR',
        file_name  => 'all_MiniLM_L12_v2.onnx',
        model_name => 'ALL_MINILM_L12_V2',
        metadata   => JSON(
'{
"function":"embedding",
"embeddingOutput":"embedding",
"input":{"input":["DATA"]}
}'
        )
    );
END;
/
```

Tunggu hingga selesai.

---

# STEP 9 - Verifikasi Model

Pastikan masih login sebagai

```
LLM_GATEWAY
```

Jalankan

```sql
SELECT
    model_name,
    mining_function,
    algorithm
FROM user_mining_models;
```

Output yang diharapkan

```
ALL_MINILM_L12_V2

EMBEDDING

ONNX
```

Jika

```
no rows selected
```

berarti model di-load menggunakan schema yang salah.

Load ulang menggunakan user

```
LLM_GATEWAY
```

---

# STEP 10 - Uji Embedding

```sql
SELECT VECTOR_EMBEDDING(
    ALL_MINILM_L12_V2
    USING 'Halo Oracle AI' AS DATA
)
FROM dual;
```

Output

```
[
0.012,
-0.221,
...
]
```

Jika berhasil berarti Oracle AI sudah mampu menghasilkan embedding.

---

# STEP 11 - Membuat Knowledge Table

Pastikan

```
SHOW USER;
```

masih

```
LLM_GATEWAY
```

Kemudian

```sql
CREATE TABLE knowledge (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR2(255) NOT NULL,
    content CLOB NOT NULL,
    embedding VECTOR(384, FLOAT32),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# STEP 12 - Menyimpan Knowledge

```sql
INSERT INTO knowledge(
    title,
    content,
    embedding
)
VALUES(
    'Jam Kerja',
    'Jam kerja dimulai pukul 08.00 WIB',
    VECTOR_EMBEDDING(
        ALL_MINILM_L12_V2
        USING 'Jam kerja dimulai pukul 08.00 WIB' AS DATA
    )
);
COMMIT;
```

---

# STEP 13 - Similarity Search

```sql
SELECT
    title,
    content,
    VECTOR_DISTANCE(
        embedding,
        VECTOR_EMBEDDING(
            ALL_MINILM_L12_V2
            USING 'Jam masuk kantor jam berapa?' AS DATA
        )
    ) distance
FROM knowledge
ORDER BY distance
FETCH FIRST 5 ROWS ONLY;
```

---

# Troubleshooting

## ORA-43853

```
VECTOR type cannot be used in tablespace SYSTEM
```

Penyebab

Sedang login menggunakan SYSTEM.

Solusi

Login kembali menggunakan

```sql
CONN llm_gateway/Oracle123@FREEPDB1
```

---

## ORA-40284

```
model does not exist
```

Penyebab

Model belum berada pada schema yang sedang digunakan.

Solusi

Pastikan

```sql
SHOW USER;
```

Kemudian cek

```sql
SELECT model_name
FROM user_mining_models;
```

Jika kosong

Load ulang model menggunakan user tersebut.

---

## no rows selected pada USER_MINING_MODELS

Artinya

Model berada pada schema lain.

Biasanya ter-load pada SYSTEM.

Load ulang menggunakan user aplikasi.

---