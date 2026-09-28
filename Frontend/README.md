# VocalScout — Frontend

Ask any question about a YouTube video and jump directly to the moment it's answered.

React + Vite + Tailwind CSS + Framer Motion + react-youtube.

## Run

```bash
# 1. Start the backend (from repo root)
cd Backend
uvicorn main:app --reload

#  keys live in .env at the repo root
# NVIDIA_API_KEY, ASSEMBLYAI_API_KEY

# 2. Start the frontend (new terminal)
cd Frontend
npm install
npm run dev
```

Open http://localhost:5173

The frontend expects the API at `http://127.0.0.1:8000`. Override with a
`.env` file in `Frontend/`:

```
VITE_API_URL=https://your-backend-url
```

## Features

- Paste any YouTube URL → builds an AI tutor (download → transcribe → chunk → embed) with live stage progress
- Embedded YouTube player (`react-youtube`) swaps to your video and restores the last active video on load
- AI search box sends the active `video_id` with every question
- Shimmer loading state — "Searching the transcript..."
- Premium answer card with supporting quote callout
- "Jump to 07:59" — seeks the player to the answer's timestamp
- Quiz mode — ask "quiz me" for 3 transcript-based questions with answers
- Copy answer / regenerate buttons
- Light & dark mode (persisted)
- Toasts for backend-offline / timeout / invalid-URL errors
- Responsive (mobile → desktop, max width ~1100px)

## Structure

```
src/
  api.js              # axios: /ask (+video_id), /process-video, /video-status, /current-video
  App.jsx             # state + wiring, build-tutor polling flow
  components/
    AuroraBackground.jsx
    Header.jsx
    Hero.jsx
    VideoPlayer.jsx
    VideoLoader.jsx   # URL input + pipeline-stage progress
    SearchBox.jsx
    LoadingCard.jsx
    AnswerCard.jsx
    EmptyState.jsx
    Toast.jsx
    Footer.jsx
  utils/
    formatTime.js     # 479080 -> "07:59"
    getYouTubeId.js   # URL -> video ID
```
