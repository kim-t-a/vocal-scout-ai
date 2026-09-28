import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Allow LAN access for testing on phone/tablet during demos
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});
