# VocalScout — Frontend

Ask any question about a YouTube video and jump directly to the moment it's answered.

React + Vite + Tailwind CSS + Framer Motion + react-youtube.

## Run

```bash
# 1. Start the backend (from repo root)
cd Backend
uvicorn main:app --reload

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

- Hero with animated gradient blobs and glassmorphism cards
- Embedded YouTube player (`react-youtube`)
- AI search box (Enter to submit, ⌘/Ctrl+K optional future)
- Shimmer loading state — "Searching the transcript..."
- Premium answer card with supporting quote callout
- "Jump to 07:59" — seeks the player to the backend's millisecond timestamp
- Copy answer / regenerate buttons
- Light & dark mode (persisted)
- Toasts for backend-offline / timeout / empty-question errors
- Responsive (mobile → desktop, max width ~1100px)

## Structure

```
src/
  api.js              # axios POST /ask
  App.jsx             # state + wiring
  components/
    AuroraBackground.jsx
    Header.jsx
    Hero.jsx
    VideoPlayer.jsx
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
