# 🎓 VocalScout

**Ask a YouTube video anything. Jump straight to the moment it's answered.**

VocalScout turns any YouTube video into an AI tutor: paste a link, it downloads the audio, transcribes it, indexes it, and lets you ask questions — each answer comes with a quote from the transcript and a **Jump to 07:59** button that seeks the embedded player to the exact moment. You can also say *"quiz me"* to get quiz questions built from the video's content.

## ✨ Features

- 🔗 **Any YouTube URL** — `watch`, `youtu.be`, `/shorts/`, `/live/`, `/embed/`, or a raw video ID
- 🏗️ **Live build progress** — download → transcribe → chunk → embed, with per-stage status
- 💬 **Grounded answers** — the AI answers only from the video's transcript, with a supporting quote
- ⏱️ **Jump to the answer** — one click seeks the player to the answer's timestamp
- 🧠 **Adaptive explanations** — confused? Ask to "explain simply" and get a beginner-friendly breakdown
- 🧪 **Quiz mode** — "quiz me on this" generates 3 questions with answers from the transcript
- 🌗 **Light/dark mode**, animated UI, toasts, responsive layout

## 📸 Screenshot

![VocalScout in action — paste a YouTube URL, build an AI tutor, ask questions and jump to the answer](docs/screenshot.png)

## 🏗️ How it works

```
YouTube URL
   │
   ▼
┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌──────────┐
│ yt-dlp   │──▶│ AssemblyAI   │──▶│ Chunker  │──▶│ NVIDIA   │
│ download │   │ transcribe   │   │ 45s win, │   │ embed +  │
│ audio    │   │ (word times) │   │ 5s overlap│  │ ChromaDB │
└──────────┘   └──────────────┘   └──────────┘   └──────────┘
                                                    │
   Question ──▶ embed ──▶ top-3 chunks ──▶ Nemotron LLM ──▶ answer + timestamp
```

**Stack:** FastAPI · ChromaDB · yt-dlp · AssemblyAI · NVIDIA NIM (Nemotron) · React 18 · Vite · Tailwind CSS · Framer Motion · react-youtube

## 📁 Project structure

```
Backend/
  main.py                  # FastAPI app: /ask /process-video /video-status /current-video
  tutor_engine.py          # Orchestrates intent → planner → RAG
  rag_service.py           # Retrieval + prompt building (answer & quiz modes)
  ingest.py                # yt-dlp download + availability probe
  agents/
    intent.py              # Rule-based intent: explain / compare / quiz / clarify
    planner.py             # Lesson-plan strategies per intent
  services/
    video_manager.py       # URL parsing, collection management
    transcriber.py         # AssemblyAI upload + polling
    chunker.py             # Word-level transcript → 45s overlapping chunks
    embeddings.py          # NVIDIA embedding API
    vector_store.py        # Chroma per-video collections
    retriever.py           # Top-k chunk search
    chat.py                # NVIDIA chat completions (with retries)
  orchestrators/
    ingestion.py           # 5-step pipeline with error → status=error

Frontend/
  src/
    App.jsx                # State + wiring (build flow, polling, ask, seek)
    api.js                 # Typed API client
    components/            # VideoLoader, VideoPlayer, SearchBox, AnswerCard, ...
    utils/                 # formatTime, getYouTubeId
```

## 🚀 Getting started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- API keys (both have free tiers):
  - [NVIDIA NIM](https://build.nvidia.com) — chat + embeddings → `NVIDIA_API_KEY`
  - [AssemblyAI](https://www.assemblyai.com/dashboard/api-key) — transcription → `ASSEMBLYAI_API_KEY`

### 1. Get the code

```bash
git clone https://github.com/kim-t-a/vocal-scout-ai.git
cd vocalscout
```

### 2. Backend

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cp .env.example .env              # macOS/Linux
copy .env.example .env            # Windows
#   → open .env and paste your keys

# Run
cd Backend
uvicorn main:app --reload
```

The API is now at `http://127.0.0.1:8000` — interactive docs at `/docs`.

### 3. Frontend

```bash
cd Frontend
npm install
npm run dev
```

Open **http://localhost:5173**, paste a YouTube URL, hit **Build tutor**, wait for the stages to complete, then ask away.

### Frontend configuration (optional)

The frontend expects the API at `http://127.0.0.1:8000`. To point elsewhere, create `Frontend/.env`:

```
VITE_API_URL=https://your-backend-url
```

## 🔧 Environment variables

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_API_KEY` | ✅ | NVIDIA NIM key for chat + embeddings |
| `ASSEMBLYAI_API_KEY` | ✅ | AssemblyAI key for transcription |
| `CORS_ORIGINS` | — | Comma-separated allowed origins. Unset = allow all (fine for local dev). **Set this in production**, e.g. `https://myapp.com` |

## 📡 API reference

| Method | Endpoint | Body / Params | Description |
|---|---|---|---|
| `POST` | `/ask` | `{"question": "...", "video_id": "..." (optional)}` | Ask the active (or given) video a question. Quiz intent detected automatically. |
| `POST` | `/process-video` | `{"url": "https://youtu.be/..."}` | Start building a tutor for a video (background). Returns `processing` or `cached`. |
| `GET` | `/video-status/{video_id}` | — | Pipeline status: `queued / downloading / transcribing / chunking / embedding / ready / error` (+ `detail` on error) |
| `GET` | `/current-video` | — | Server's active video |
| `GET` | `/` | — | Health check |

## ⚠️ Known limitations

- **Single-user session** — the "active video" is server-global; fine for local use, not for many simultaneous users. Per-request `video_id` support in `/ask` mitigates this.
- **In-memory status** — processing state resets when the backend restarts (restart mid-build = re-paste the URL).
- **No streaming** — answers arrive after several seconds; SSE streaming is a planned improvement.
- **English-first** — transcription auto-detects language, but prompts/UX are English-centric.

## 🗺️ Roadmap ideas

- [ ] Streaming answers (SSE)
- [ ] Persistent job queue (e.g. Celery/Redis) + user sessions
- [ ] Chat history & follow-up questions
- [ ] Chapter-aware chunking using AssemblyAI `auto_chapters`
- [ ] Deployment guide (Docker, Render/Railway + Vercel)

## 🤝 Contributing

Issues and PRs welcome! Keep changes minimal and consistent with the existing structure (`agents/` for AI decision logic, `services/` for external integrations, `orchestrators/` for pipelines).

## 📄 License

[MIT](LICENSE) — free to use, modify, and share.
