import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { motion } from "framer-motion";
import YouTube from "react-youtube";

/**
 * Responsive YouTube player inside a glass card.
 *
 * Exposes an imperative handle so the parent can seek without reaching
 * into react-youtube internals:
 *   ref.current.isReady()           -> bool
 *   ref.current.seekTo(seconds)     -> bool (false = queued for later)
 *   ref.current.getCurrentTime()    -> seconds | null (transcript highlight)
 *
 * The player instance is captured from onReady (the documented way to get
 * the YouTubePlayer). If a seek is requested while the player is missing or
 * mid-rebuild — e.g. right after the video was swapped — it is queued and
 * applied as soon as onReady fires for the new player.
 */
const VideoPlayer = forwardRef(function VideoPlayer({ videoId }, ref) {
  const playerRef = useRef(null);
  const pendingSeekRef = useRef(null);

  // When the video changes, react-youtube destroys and re-creates the player.
  // Invalidate the captured instance so we never seek a dying player; the
  // new player's onReady re-captures it.
  useEffect(() => {
    playerRef.current = null;
  }, [videoId]);

  useImperativeHandle(
    ref,
    () => ({
      isReady: () => Boolean(playerRef.current),
      // Current playback position in seconds, or null when the player isn't
      // alive — the transcript panel polls this to highlight the active chunk.
      getCurrentTime: () => {
        try {
          const t = playerRef.current?.getCurrentTime?.();
          return typeof t === "number" ? t : null;
        } catch {
          return null;
        }
      },
      seekTo: (seconds) => {
        const player = playerRef.current;
        if (player && typeof player.seekTo === "function") {
          try {
            player.seekTo(seconds, true);
            if (typeof player.playVideo === "function") player.playVideo();
            return true;
          } catch {
            /* player died mid-swap — queue the seek instead */
          }
        }
        pendingSeekRef.current = seconds;
        return false;
      },
    }),
    []
  );

  const handleReady = (event) => {
    playerRef.current = event.target;

    // Apply a seek that was requested before the player was ready.
    if (pendingSeekRef.current != null) {
      const seconds = pendingSeekRef.current;
      pendingSeekRef.current = null;
      try {
        event.target.seekTo(seconds, true);
        if (typeof event.target.playVideo === "function") event.target.playVideo();
      } catch {
        /* player died again — drop the queued seek */
      }
    }
  };

  const opts = {
    width: "100%",
    height: "100%",
    playerVars: {
      rel: 0,
      modestbranding: 1,
      playsinline: 1,
    },
  };

  return (
    <section aria-label="YouTube video" className="relative">
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
        whileHover={{ y: -4 }}
        className="glass rounded-2xl p-2 sm:p-3"
      >
        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black/90">
          <YouTube
            videoId={videoId}
            opts={opts}
            onReady={handleReady}
            className="absolute inset-0 h-full w-full"
            iframeClassName="absolute inset-0 h-full w-full"
          />
        </div>
      </motion.div>
    </section>
  );
});

export default VideoPlayer;
