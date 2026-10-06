import axios from "axios";

// Backend base URL. Override with VITE_API_URL in a .env file if needed.
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const askQuestion = async (question, videoId, history = [], quizCount = null) => {
  const { data } = await axios.post(
    `${API_BASE}/ask`,
    { question, video_id: videoId, history, quiz_count: quizCount },
    { timeout: 45000 }
  );
  return data;
};

/**
 * Ask a question and hand each event to `onEvent` as it arrives.
 *
 * Uses fetch + a stream reader rather than axios because the response is a
 * long-lived Server-Sent Events body, not one JSON blob. The backend sends one
 * JSON object per `data:` frame (`meta`, `token`…, `suggestions`, `done`).
 */
export const askQuestionStream = async (
  question,
  videoId,
  history = [],
  quizCount = null,
  onEvent = () => {}
) => {
  const response = await fetch(`${API_BASE}/ask-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      video_id: videoId,
      history,
      quiz_count: quizCount,
    }),
  });

  if (!response.ok) {
    const error = new Error(`Backend error (${response.status})`);
    error.status = response.status;
    throw error;
  }

  if (!response.body) throw new Error("This browser can't stream responses.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const handleFrame = (frame) => {
    const line = frame.split("\n").find((l) => l.startsWith("data:"));
    if (!line) return; // comment / keep-alive line
    try {
      onEvent(JSON.parse(line.slice(5).trim()));
    } catch {
      /* malformed frame — skip it and keep reading */
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line; a chunk can hold several.
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      handleFrame(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
  }
};

export const processVideo = async (url) => {
  const { data } = await axios.post(
    `${API_BASE}/process-video`,
    { url },
    { timeout: 30000 }
  );
  return data;
};

export const getVideoStatus = async (videoId) => {
  const { data } = await axios.get(
    `${API_BASE}/video-status/${videoId}`,
    { timeout: 15000 }
  );
  return data;
};

export const getCurrentVideo = async () => {
  const { data } = await axios.get(`${API_BASE}/current-video`, {
    timeout: 10000,
  });
  return data;
};

/**
 * The video's timestamped transcript chunks for the clickable transcript
 * panel. 404 when the video hasn't been processed yet.
 */
export const getTranscript = async (videoId) => {
  const { data } = await axios.get(`${API_BASE}/transcript/${videoId}`, {
    timeout: 15000,
  });
  return data;
};
