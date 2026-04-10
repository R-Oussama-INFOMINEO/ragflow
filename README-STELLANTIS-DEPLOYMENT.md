# RagFlow v0.24.0 — Deployment Guide
> Configured for local development (Docker Desktop + WSL2) and GCP production deployment.  
> Vector backend: **Infinity** (not Elasticsearch) | Embedding: **TEI local** (CPU mode)

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start — Local WSL2](#quick-start--local-wsl2)
3. [Configuration Overview](#configuration-overview)
4. [Known Issues & Fixes](#known-issues--fixes)
5. [Health Checks](#health-checks)
6. [Corporate Network (Kaspersky SSL)](#corporate-network-kaspersky-ssl)
7. [API Usage](#api-usage)
8. [YouTube Video Ingestion](#youtube-video-ingestion)
9. [GCP Production Deployment](#gcp-production-deployment)
10. [Stellantis API Endpoints](#stellantis-api-endpoints)
11. [Development Workflow](#development-workflow)

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker Desktop | ≥ 24.0.0 | WSL2 backend enabled |
| Docker Compose | ≥ v2.26.1 | Included with Docker Desktop |
| WSL2 | Ubuntu 22.04 / 24.04 | Windows only |
| RAM | ≥ 16GB allocated to WSL2 | 20GB recommended |
| Disk | ≥ 60GB free | Images + models + data |

---

## Quick Start — Local WSL2

### 1. Configure WSL2 memory (Windows only)

Create or edit `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=20GB
processors=8
swap=4GB
kernelCommandLine="sysctl.vm.max_map_count=262144"
```

Then restart WSL2:
```powershell
wsl --shutdown
```

### 2. Clone this repo into WSL2

> ⚠️ Always clone inside the WSL2 filesystem (`~/`), never under `/mnt/c/`

```bash
cd ~
git clone https://github.com/InfomineoGithub/ragflow.git
cd ragflow
git checkout feature/youtube-ingestion
```

### 3. Pull images and start the stack

```bash
cd docker
docker compose -f docker-compose.yml pull
docker compose -f docker-compose.yml up -d
```

> The stack uses the custom image `ragflow-stellantis:v0.24.0` defined in `docker/.env`.
> If this image is not available locally, build it first:
> ```bash
> cd ~/ragflow && docker build -f Dockerfile.custom -t ragflow-stellantis:v0.24.0 .
> ```

### 4. Watch startup logs

```bash
docker logs -f docker-ragflow-cpu-1
```

Wait for the RAGFlow ASCII banner and `Running on all addresses (0.0.0.0)`.
First startup takes **5–15 minutes** — DeepDoc models download from HuggingFace (~2GB).

### 5. Access the UI

Open your browser at: `http://localhost`

Register a new account on first login.

---

## Configuration Overview

Configuration lives in `docker/.env` — **never committed to git**. Copy from the template:

```bash
cp docker/.env.example docker/.env
# Edit with your local values
```

Key settings for this deployment:

| Setting | Local dev value | Production (GCP) | Notes |
|---|---|---|---|
| `DOC_ENGINE` | `infinity` | `elasticsearch` | Vector DB backend |
| `RAGFLOW_IMAGE` | `ragflow-stellantis:v0.24.0` | `ragflow-stellantis:v0.24.0` | Custom image |
| `COMPOSE_PROFILES` | `tei-cpu` | `tei-gpu` | Embedding service profile |
| `TEI_MODEL` | `BAAI/bge-small-en-v1.5` | `Qwen/Qwen3-Embedding-0.6B` | Embedding model |
| `TZ` | your local timezone | `Asia/Shanghai` | Timezone |

### Services and ports

| Service | Container | Port | Role |
|---|---|---|---|
| RagFlow UI + API | `docker-ragflow-cpu-1` | 80, 9380 | Main application |
| Infinity | `docker-infinity-1` | 23820 | Vector database |
| MySQL | `docker-mysql-1` | 5455 | Metadata storage |
| MinIO | `docker-minio-1` | 9000, 9001 | File storage |
| Redis/Valkey | `docker-redis-1` | 6379 | Task queue |
| TEI | `docker-tei-cpu-1` | 6380 | Embedding service |

---

## Known Issues & Fixes

### Fix 1 — Embedding model `@None` not authorized

**Symptom:** Document parsing fails with:
```
[ERROR]Fail to bind embedding model: Model(BAAI/bge-small-en-v1.5@None) not authorized
```

**Cause:** v0.24.0 bug — tenant table stores embedding model ID without `@Builtin` suffix.

**Fix:** Run once after fresh deployment:
```bash
docker exec docker-mysql-1 mysql -u root -pinfini_rag_flow rag_flow \
  -e "UPDATE tenant SET embd_id='BAAI/bge-small-en-v1.5@Builtin' \
      WHERE embd_id='BAAI/bge-small-en-v1.5';" 2>/dev/null
```

**Verify:**
```bash
docker exec docker-mysql-1 mysql -u root -pinfini_rag_flow rag_flow \
  -e "SELECT name, embd_id FROM tenant;" 2>/dev/null
```
Both rows must show `BAAI/bge-small-en-v1.5@Builtin`.

---

### Fix 2 — vm.max_map_count too low

**Symptom:** Infinity container crashes or fails health check.

**Fix:** Already handled by `.wslconfig` `kernelCommandLine` setting.

**Verify:**
```bash
cat /proc/sys/vm/max_map_count
# Must print: 262144
```

---

### Fix 3 — Port 80 already in use

**Symptom:** Stack fails to start, port binding error.

**Fix:** Edit `docker/docker-compose.yml` and change `80:80` to `8080:80`,
then access the UI at `http://localhost:8080`.

---

### Fix 4 — Custom image not found

**Symptom:** Stack fails to start with `pull access denied for ragflow-stellantis`.

**Cause:** The custom image hasn't been built locally yet.

**Fix:**
```bash
cd ~/ragflow && docker build -f Dockerfile.custom -t ragflow-stellantis:v0.24.0 .
```

This takes 8–10 minutes and layers on top of `infiniflow/ragflow:v0.24.0`.
It installs ffmpeg, all Whisper backends, and pre-downloads the `tiny` and `base` models.

---

### Fix 5 — Corporate SSL proxy (HuggingFace / OpenAI SDK)

**Symptom:** Whisper model download or OpenAI API calls fail with:
```
SSL: CERTIFICATE_VERIFY_FAILED — self-signed certificate in certificate chain
```

**Cause:** Corporate SSL inspection (e.g. Kaspersky) intercepts HTTPS connections.

**Fix:** Already baked into `Dockerfile.custom` via three ENV variables:
```dockerfile
ENV HF_HUB_DISABLE_SSL_VERIFICATION=1   # HuggingFace model downloads
ENV CURL_CA_BUNDLE=""                    # curl/requests based libraries
ENV REQUESTS_CA_BUNDLE=""               # OpenAI SDK (httpx)
```

No manual action needed — these are set automatically in the custom image.

> ⚠️ For LLM/chat calls (Gemini API), a separate Kaspersky certificate injection
> is still required. See the [Corporate Network](#corporate-network-kaspersky-ssl) section.

---

## Health Checks

Run after stack startup to verify all services:

```bash
# All containers status
docker compose -f docker/docker-compose.yml ps

# MySQL
docker exec docker-mysql-1 mysqladmin -u root -pinfini_rag_flow ping 2>/dev/null

# MinIO
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live

# TEI embedding service
docker logs --tail=5 docker-tei-cpu-1 | grep -E "Ready|Error"

# Infinity
docker inspect docker-infinity-1 --format='{{.State.Health.Status}}'

# Video parser registration
docker exec docker-ragflow-cpu-1 /ragflow/.venv/bin/python3 -c "
from common.constants import ParserType
from rag.svr.task_executor import FACTORY
assert ParserType.VIDEO.value in FACTORY
print('Video parser: OK')
" 2>&1 | grep "Video parser"

# Whisper backends availability
docker exec docker-ragflow-cpu-1 /ragflow/.venv/bin/python3 -c "
import subprocess
for pkg in ['faster_whisper', 'yt_dlp', 'whisper']:
    try:
        __import__(pkg)
        print(f'✅ {pkg} importable')
    except ImportError:
        print(f'❌ {pkg} missing')
r = subprocess.run(['ffmpeg', '-version'], capture_output=True)
print('✅ ffmpeg available' if r.returncode == 0 else '❌ ffmpeg missing')
from faster_whisper import WhisperModel
for size in ['tiny', 'base']:
    try:
        WhisperModel(size, device='cpu', compute_type='int8')
        print(f'✅ faster-whisper {size} model cached')
    except Exception as e:
        print(f'❌ faster-whisper {size} failed: {e}')
"
```

---

## Corporate Network (Kaspersky SSL)

If your machine uses Kaspersky Endpoint Security with SSL inspection
(common in corporate environments), the RagFlow container cannot reach
external APIs (Gemini, HuggingFace) without trusting the Kaspersky CA certificate.

> ⚠️ The SSL fix is only needed for **LLM/chat calls** (Gemini API).
> Whisper model downloads and OpenAI API calls are handled automatically
> via ENV variables baked into the image (see Fix 5 above).

### Export the certificate (Windows PowerShell)

```powershell
$cert = Get-ChildItem -Path Cert:\LocalMachine\Root |
  Where-Object { $_.Subject -like "*Kaspersky*" } |
  Select-Object -First 1

$b64 = [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks')
"-----BEGIN CERTIFICATE-----`n$b64`n-----END CERTIFICATE-----" |
  Out-File -FilePath "$env:USERPROFILE\kaspersky-ca.pem" -Encoding ASCII

# Copy to WSL2
Copy-Item "$env:USERPROFILE\kaspersky-ca.pem" "\\wsl$\Ubuntu\home\$env:USERNAME\kaspersky-ca.pem"
```

### Inject into RagFlow container

```bash
# Copy cert into container
docker cp ~/kaspersky-ca.pem docker-ragflow-cpu-1:/tmp/kaspersky-ca.pem

# Add to system CA store
docker exec -u root docker-ragflow-cpu-1 bash -c \
  'cp /tmp/kaspersky-ca.pem /usr/local/share/ca-certificates/kaspersky-ca.crt && \
   update-ca-certificates'

# Add to Python certifi stores (required for LLM API calls)
docker exec -u root docker-ragflow-cpu-1 bash -c \
  'find / -name "cacert.pem" 2>/dev/null | grep -i certifi | \
   while read f; do cat /tmp/kaspersky-ca.pem >> "$f"; done'
```

> ⚠️ This fix does not persist across container restarts.
> Re-run after any `docker compose down && up` cycle.
> Not needed when running outside the corporate network (e.g. GCP, home).

---

## API Usage

### Get your API key

UI → Avatar (top-right) → API KEY → Create new key

### List datasets

```bash
API_KEY="ragflow-xxxxxxxxxxxx"

curl -s -X GET "http://localhost:9380/api/v1/datasets" \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool
```

### Upload and parse a document

```bash
DATASET_ID="your_dataset_id"

curl -s -X POST "http://localhost:9380/api/v1/datasets/${DATASET_ID}/documents" \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "file=@/path/to/your/document.pdf"
```

### Retrieval query

```bash
curl -s -X POST "http://localhost:9380/api/v1/retrieval" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{
    "question": "Your question here",
    "dataset_ids": ["'"${DATASET_ID}"'"],
    "similarity_threshold": 0.1,
    "keywords_similarity_weight": 0.7,
    "top_n": 3
  }' | python3 -m json.tool
```

### Extract page numbers from retrieval response

```python
import json, requests

response = requests.post(
    "http://localhost:9380/api/v1/retrieval",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"question": "...", "dataset_ids": [DATASET_ID], "top_n": 3}
)

for chunk in response.json()["data"]["chunks"]:
    pages = sorted(set([p[0] for p in chunk.get("positions", []) if p]))
    print(f"chunk_id : {chunk['id']}")
    print(f"source   : {chunk['document_keyword']}")
    print(f"pages    : {pages}")
    print(f"content  : {chunk['content'][:200]}")
```

---

## YouTube Video Ingestion

This deployment includes a custom YouTube transcript ingestion pipeline built on top of RagFlow v0.24.0.

### Architecture

```
Orchestrator (The Brain)
    │
    ▼
POST /api/v1/stellantis/datasets           ← create one analysis dataset per run
    │  returns { analysis_id, name }       ← orchestrator stores analysis_id
    ▼
POST /api/v1/stellantis/ingest/video       ← register YouTube URL + business metadata
POST /api/v1/stellantis/ingest/document    ← upload PDF / HTML / Image + business metadata
    │  business metadata stored via DocMetadataService (never in parser_config)
    │  brand, car_model, year, market, trim, source_type, retrieval_date
    ▼
task_executor.py (parser_id="video"|"naive"|"picture")
    │  video: fetches youtube_url from DocMetadataService → passes to video.py
    │  bypasses MinIO for video — no file upload needed
    ▼
rag/app/video.py → _fetch_transcript()     ← video pipeline (orchestrator only)
    ├── video_backends/youtube_transcript.py  → captions (fast, default) + Retry
    ├── video_backends/faster_whisper.py      → local CTranslate2 (CPU/GPU)
    ├── video_backends/openai_whisper.py      → local original lib (CPU/GPU)
    └── video_backends/openai_api.py          → cloud REST API + Retry + Circuit Breaker

DeepDoc Engine                             ← docs pipeline
    ├── PDF parser (naive)
    ├── HTML parser (naive)
    └── Image parser (picture / vision OCR)
    │
    │  merge into 60-second overlapping segments (video)
    │  or structured chunks (docs)
    │  tokenize via rag_tokenizer
    ▼
TEI embedding (BAAI/bge-small-en-v1.5@Builtin)
    ▼
Infinity vector store
    │  stores: youtube_url, video_id, video_title,
    │          timestamp_seconds, transcript_segment
    ▼
GET /api/v1/stellantis/retrieve?analysis_id=...&question=...
    │  single dataset lookup by analysis_id
    │  optional source_type filter
    │  optional reranker (falls back silently if not configured)
    │  highlight=True for PDF bounding box support
    ▼
chunks with timestamp deep-links + full source traceability
```

---

### Dataset Naming Convention

All datasets follow this standardized naming format:

```
{Brand}_{Model}_{Year}_{Market}_{Trim}_{YYYYMMDD}_{HHMM}
```

**Examples:**
```
Opel_Corsa_2023_UK_All_20260327_2005
Opel_Corsa_2025_IE_All_20260327_2005
Peugeot_208_2023_FR_All_20260327_2009
Opel_Corsa_2025_IE_GS_20260328_0900    ← trim-specific
```

> All source types (Video, PDF, HTML, Image) share one dataset per analysis run.
> Source type is tracked per-document via DocMetadataService metadata, not in the dataset name.

**Market ISO codes:**

| Country | Code |
|---|---|
| United Kingdom | `UK` |
| Ireland | `IE` |
| France | `FR` |
| Germany | `DE` |
| Italy | `IT` |
| Spain | `ES` |
| Belgium | `BE` |
| Netherlands | `NL` |

> Date and time are **auto-generated** at ingestion time — no manual input needed.
> Full country names are automatically normalized to ISO codes.

---

### Transcript Backends

The pipeline supports 4 configurable backends selected via `whisper_backend` in `parser_config`:

| Backend | Speed (5-min video) | Requires | Best for |
|---|---|---|---|
| `youtube-transcript-api` | ~1 sec | Nothing | Local dev, videos with captions |
| `faster-whisper` | ~30 sec (tiny/CPU), ~8 sec (large/GPU) | yt-dlp + ffmpeg (baked in) | Production CPU/GPU |
| `openai-whisper` | ~2 min (tiny/CPU) | yt-dlp + ffmpeg (baked in) | Alternative local option |
| `openai-api` | ~10 sec | OpenAI API key | Cloud, fastest, $0.006/min |

All backends return the same format: `[{"text": str, "start": float, "duration": float}, ...]`

---

### Business metadata reference

Business metadata is stored **per-document** via `DocMetadataService` — never in `parser_config`.
This keeps `parser_config` focused on parser behaviour settings only.

| Field | Type | Required | Description |
|---|---|---|---|
| `brand` | string | ✅ | Car manufacturer e.g. `"Opel"`, `"Peugeot"` |
| `car_model` | string | ✅ | Car model e.g. `"Corsa"`, `"208"` |
| `year` | string | ✅ | Model year e.g. `"2023"`, `"2025"` |
| `market` | string | ✅ | Target market ISO code e.g. `"UK"`, `"FR"`, `"IE"` |
| `trim` | string | ✅ | Trim level e.g. `"All"`, `"GS"`, `"Elegance"` |
| `source_type` | string | ✅ | Content type: `"Video"`, `"Docs"`, `"Web"`, `"Images"` |
| `retrieval_date` | string | auto | Auto-generated ingestion date `"YYYY-MM-DD"` |

### `parser_config` reference (video only)

Only Whisper-related fields belong in `parser_config`:

| Field | Type | Required | Description |
|---|---|---|---|
| `whisper_backend` | string | video only | Transcription backend (see above) |
| `whisper_model` | string | video only | Model size: `tiny`, `base`, `small`, `medium`, `large` |
| `openai_api_key` | string | openai-api only | Required only for `openai-api` backend |

> **Model size guidance:**
> - `tiny` — fastest, lower accuracy (~29 sec on CPU for 3.5-min video)
> - `base` — good balance of speed and accuracy (~60 sec on CPU)
> - `large` — best accuracy, requires GPU (~8 sec on GCP GPU)

---

### Files modified / created

| File | Change |
|---|---|
| `common/constants.py` | Added `ParserType.VIDEO = "video"` |
| `rag/app/video.py` | Orchestrator only — dispatches to `video_backends/` |
| `rag/app/video_backends/youtube_transcript.py` | Backend 1: youtube-transcript-api + Retry |
| `rag/app/video_backends/whisper_shared.py` | Shared: `download_audio()` + `with_retry()` utility |
| `rag/app/video_backends/faster_whisper.py` | Backend 2: faster-whisper (local CTranslate2) |
| `rag/app/video_backends/openai_whisper.py` | Backend 3: openai-whisper (local original lib) |
| `rag/app/video_backends/openai_api.py` | Backend 4: OpenAI API + Retry + Circuit Breaker |
| `rag/svr/task_executor.py` | Registered video parser; fetches `youtube_url` from DocMetadataService |
| `rag/nlp/search.py` | Added video fields to Infinity retrieval field list |
| `api/apps/sdk/stellantis.py` | 4 Stellantis REST endpoints (datasets, ingest/video, ingest/document, retrieve) |
| `api/apps/sdk/dataset.py` | Business metadata stored via DocMetadataService per-document |
| `api/apps/sdk/doc.py` | Generic `properties` dict in Chunk model (replaces video root fields) |
| `api/utils/validation_utils.py` | Business fields removed from `ParserConfig` |
| `api/utils/api_utils.py` | Added `"video": None` to `get_parser_config` map |
| `api/db/init_data.py` | Added `video:Video` to tenant `parser_ids` |
| `conf/infinity_mapping.json` | Added 5 video columns in compact format |
| `docker/.env.example` | Template for team — never commit `docker/.env` |
| `Dockerfile.custom` | ffmpeg, all Whisper backends; SSL bypasses; pre-cached models |
| `tests/test_ragflow_pipeline.py` | MCP-ready async pipeline test utility |

---

### Step-by-step ingestion workflow

**Step 1 — Create an analysis dataset**

```bash
API_KEY="your_api_key"

curl -s -X POST "http://localhost:9380/api/v1/stellantis/datasets" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Opel",
    "car_model": "Corsa",
    "year": "2023",
    "market": "UK",
    "trim": "All",
    "whisper_backend": "youtube-transcript-api",
    "whisper_model": "base"
  }' | python3 -m json.tool
```

Save the returned `id` as `ANALYSIS_ID` — this is your analysis_id for all subsequent calls.

**Step 2 — Ingest a YouTube video**

```bash
curl -s -X POST "http://localhost:9380/api/v1/stellantis/ingest/video" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "'"${ANALYSIS_ID}"'",
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "title": "Opel Corsa 2023 review",
    "brand": "Opel", "car_model": "Corsa",
    "year": "2023", "market": "UK",
    "source_type": "Video"
  }' | python3 -m json.tool
```

**Step 3 — Ingest a PDF/HTML/Image document**

```bash
curl -s -X POST "http://localhost:9380/api/v1/stellantis/ingest/document" \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "dataset_id=${ANALYSIS_ID}" \
  -F "brand=Opel" -F "car_model=Corsa" -F "year=2023" -F "market=UK" \
  -F "source_type=Docs" \
  -F "file=@/path/to/corsa_specs.pdf" | python3 -m json.tool
```

**Step 4 — Trigger processing**

```bash
DOC_ID="doc_id_from_ingest_response"

curl -s -X POST "http://localhost:9380/api/v1/datasets/${ANALYSIS_ID}/chunks" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"document_ids\": [\"${DOC_ID}\"]}" | python3 -m json.tool
```

Processing time depends on backend:
- `youtube-transcript-api`: ~10 seconds
- `faster-whisper` tiny on CPU: ~30–60 seconds
- `faster-whisper` large on GPU (GCP): ~8 seconds

Monitor with:
```bash
docker logs docker-ragflow-cpu-1 --tail=5 -f 2>&1 | grep -i "done\|fail\|video\|whisper"
```

**Step 5 — Retrieve by analysis_id**

```bash
curl -s "http://localhost:9380/api/v1/stellantis/retrieve?analysis_id=${ANALYSIS_ID}&question=engine+performance&top_n=3" \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool
```

Or using the test utility:

```python
from tests.test_ragflow_pipeline import load_config, retrieve_by_analysis_id

cfg = load_config()

# Query all sources in one analysis run
chunks = await retrieve_by_analysis_id(cfg, analysis_id, "engine performance")

# Query only Video sources
chunks = await retrieve_by_analysis_id(cfg, analysis_id, "engine performance",
                                        source_type="Video")
```

---

### Retrieval response fields

Each chunk in the retrieval response includes these video-specific fields:

| Field | Type | Description |
|---|---|---|
| `youtube_url` | string | Original YouTube URL |
| `video_id` | string | 11-character YouTube video ID |
| `video_title` | string | Title provided at ingestion time |
| `timestamp_seconds` | integer | Start time of this segment in the video |
| `transcript_segment` | string | Deep-link URL (`&t=Xs`) to jump to exact moment |

### Example retrieval response (video chunk)

```json
{
  "content": "it rides on the stellantis CMP platform which is shared with the Peugeot 208...",
  "document_keyword": "https://www.youtube.com/watch?v=QFzEVtY_1lQ",
  "youtube_url": "https://www.youtube.com/watch?v=QFzEVtY_1lQ",
  "video_id": "QFzEVtY_1lQ",
  "video_title": "Opel Corsa 2023 review",
  "timestamp_seconds": 60,
  "transcript_segment": "https://www.youtube.com/watch?v=QFzEVtY_1lQ&t=60s",
  "similarity": 0.689,
  "positions": []
}
```

---

### Python ingestion helper (using test_ragflow_pipeline.py)

The recommended way to interact with the pipeline is via `tests/test_ragflow_pipeline.py`:

```python
import asyncio
import importlib.util

spec = importlib.util.spec_from_file_location("trp", "/ragflow/tests/test_ragflow_pipeline.py")
trp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trp)
cfg = trp.load_config()

async def main():
    # Step 1 — Create one analysis dataset
    dataset = await trp.create_analysis_dataset(
        cfg, "Opel", "Corsa", "2023", "UK",
        whisper_backend="youtube-transcript-api"
    )
    analysis_id = dataset["id"]
    print(f"analysis_id: {analysis_id}")

    # Step 2 — Ingest a YouTube video
    doc = await trp.ingest_video(
        cfg, analysis_id,
        url="https://www.youtube.com/watch?v=VIDEO_ID",
        title="Opel Corsa 2023 review",
        brand="Opel", car_model="Corsa", year="2023", market="UK",
        source_type="Video"
    )

    # Step 3 — Ingest a PDF into the same dataset
    doc = await trp.ingest_pdf(
        cfg, analysis_id,
        file_path="/ragflow/tests/Corsa_PDF.pdf",
        brand="Opel", car_model="Corsa", year="2023", market="UK",
        source_type="Docs"
    )

    # Step 4 — Trigger parsing and wait
    await trp.trigger_parsing(cfg, analysis_id, doc["id"])
    await trp.wait_for_completion(cfg, analysis_id, doc["id"], timeout=300)

    # Step 5 — Retrieve by analysis_id
    chunks = await trp.retrieve_by_analysis_id(
        cfg, analysis_id, "engine performance", top_n=3
    )

    # Print results
    for c in chunks:
        props = c.get("properties", {})
        if props.get("timestamp_seconds") is not None:
            print(f"[Video {props['timestamp_seconds']}s] {c['content'][:100]}")
        else:
            print(f"[Doc] {c['content'][:100]}")

asyncio.run(main())
```

### Requirements and constraints

- `youtube-transcript-api` backend: video must have English captions (manual or auto-generated)
- `faster-whisper` / `openai-whisper` / `openai-api` backends: works on any video with audio, no captions needed
- All Whisper dependencies (ffmpeg, yt-dlp, faster-whisper, openai-whisper) are baked into `ragflow-stellantis:v0.24.0` — no manual install needed
- `faster-whisper` tiny and base models are pre-cached in the image — no download on first use
- The dataset must be created with `chunk_method: "video"` — the UI dropdown does not show `video` (UI is hardcoded); always use the API
- Dataset names are auto-generated — do not set them manually
- On GCP with `bge-m3`, re-index from scratch — `parser_id` stays `"video"`, no code changes needed
- The UI Files tab shows "No data available" for video datasets — this is expected (URL-based, no MinIO upload); use the Retrieval Testing tab instead

---

## GCP Production Deployment

> 🚧 This section will be updated after GCP deployment is completed.

### Planned changes for GCP

| Setting | Local value | GCP value |
|---|---|---|
| `RAGFLOW_IMAGE` | `ragflow-stellantis:v0.24.0` | rebuild from `Dockerfile.custom` on GCP |
| `TEI_MODEL` | `BAAI/bge-small-en-v1.5` | `BAAI/bge-m3` |
| `COMPOSE_PROFILES` | `tei-cpu` | `tei-gpu` |
| `DOC_BULK_SIZE` | `4` | `16` (higher throughput) |
| `EMBEDDING_BATCH_SIZE` | `8` | `32` (GPU handles larger batches) |
| `whisper_model` | `tiny` / `base` (CPU) | `large` (GPU, ~8 sec/video) |
| LLM provider | Gemini via OpenAI-compatible | Gemini via OpenAI-compatible |

### Important: re-indexing required on GCP

`BAAI/bge-small-en-v1.5` produces **512-dimension** vectors.
`BAAI/bge-m3` produces **1024-dimension** vectors.

These are **incompatible**. All datasets must be re-created and re-parsed
from scratch on the GCP instance. Do not migrate data volumes from local to GCP.

### GCP prerequisites (to be documented)

- [ ] GCP project with required APIs enabled
- [ ] Terraform service account with appropriate IAM roles (`stellantis-terraform-sa@stellantis-490509.iam.gserviceaccount.com`)
- [ ] Gemini API key (restricted to Generative Language API)
- [ ] GCS bucket for Terraform state (optional)
- [ ] VM instance with GPU support (for bge-m3 embedding + faster-whisper large)
- [ ] Docker and Docker Compose installed on GCP VM
- [ ] Firewall rules for ports 80, 443, 9380
- [ ] Build `ragflow-stellantis:v0.24.0` image on the GCP VM

---

---

## Stellantis API Endpoints

The pipeline exposes 4 dedicated REST endpoints under `/api/v1/stellantis/`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/stellantis/datasets` | Create one analysis dataset per run |
| `POST` | `/api/v1/stellantis/ingest/video` | Ingest YouTube video with business metadata |
| `POST` | `/api/v1/stellantis/ingest/document` | Ingest PDF, HTML or Image with business metadata |
| `GET` | `/api/v1/stellantis/retrieve` | Retrieve chunks by analysis_id |

All endpoints:
- Require Bearer token authentication
- Store business metadata via `DocMetadataService` — never in `parser_config`
- Follow existing RagFlow response conventions (`get_result` / `get_error_data_result`)

### Retrieve endpoint parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `analysis_id` | string | ✅ | Dataset ID from create dataset response |
| `question` | string | ✅ | Natural language query |
| `source_type` | string | optional | Filter by `"Video"`, `"Docs"`, `"Web"`, `"Images"` |
| `top_n` | integer | optional | Max chunks to return (default: 5) |
| `similarity_threshold` | float | optional | Min similarity 0.0–1.0 (default: 0.1) |

---

## Development Workflow

### Making code changes

When modifying Python source files, the container must be restarted to pick up changes. Use the helper script:

```bash
bash docker/deploy-local.sh
```

This restarts the container, prints the running image name as a sanity check,
and re-copies all modified source files in one command.

### Updating test scripts only (no restart needed)

```bash
docker cp tests/test_ragflow_pipeline.py \
  docker-ragflow-cpu-1:/ragflow/tests/test_ragflow_pipeline.py
```

### Rebuilding the custom Docker image

After significant changes that should be permanent (not just for a session):

```bash
cd ~/ragflow
docker build -f Dockerfile.custom -t ragflow-stellantis:v0.24.0 .
```

Then force-recreate the container from the new image:
```bash
cd docker && docker compose up -d --no-deps --force-recreate ragflow-cpu
```

> ⚠️ `docker compose down && up` restarts the existing container from the old image.
> Always use `--force-recreate` after rebuilding the image.

### Files tracked by deploy-local.sh

The script re-copies these files on every deploy:

```
common/constants.py
rag/app/video.py
rag/app/video_backends/  (all 5 files)
rag/svr/task_executor.py
rag/nlp/search.py
api/apps/sdk/dataset.py
api/apps/sdk/stellantis.py
api/apps/sdk/doc.py
api/utils/validation_utils.py
api/utils/api_utils.py
api/db/init_data.py
conf/infinity_mapping.json
tests/test_ragflow_pipeline.py
tests/.env.test
tests/  (test asset files)
```

## Stack management commands

```bash
# Stop without deleting data
docker compose -f docker/docker-compose.yml stop

# Full restart
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d

# Force-recreate container from new image (after docker build)
cd docker && docker compose up -d --no-deps --force-recreate ragflow-cpu

# DANGER: delete all data and start fresh
docker compose -f docker/docker-compose.yml down -v

# View logs
docker logs -f docker-ragflow-cpu-1   # Main app
docker logs -f docker-tei-cpu-1       # Embedding service
docker logs -f docker-infinity-1      # Vector DB

# Check disk usage
docker system df

# Re-deploy source files without full rebuild (dev only)
bash docker/deploy-local.sh
```

---

*Last updated: April 2026 | RagFlow v0.24.0 | Branch: `feature/stellantis-pipeline` | One-dataset-per-analysis-run | analysis_id retrieval | Retry + Circuit Breaker | video_backends/ package*
