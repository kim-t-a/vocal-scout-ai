import { forwardRef } from "react";
import { motion } from "framer-motion";
import YouTube from "react-youtube";

/**
 * Responsive YouTube player inside a glass card.
 * Forwards the react-youtube ref to the parent; the parent can call
 * ref.current.getInternalPlayer().seekTo(seconds, true) to jump.
 */
const VideoPlayer = forwardRef(function VideoPlayer({ videoId }, ref) {
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
            ref={ref}
            videoId={videoId}
            opts={opts}
            className="absolute inset-0 h-full w-full"
            iframeClassName="absolute inset-0 h-full w-full"
          />
        </div>
      </motion.div>
    </section>
  );
});

export default VideoPlayer;
