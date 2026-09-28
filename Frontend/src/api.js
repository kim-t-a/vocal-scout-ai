import axios from "axios";

// Backend base URL. Override with VITE_API_URL in a .env file if needed.
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const askQuestion = async (question, videoId, history = []) => {
  const { data } = await axios.post(
    `${API_BASE}/ask`,
    { question, video_id: videoId, history },
    { timeout: 45000 }
  );
  return data;
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
