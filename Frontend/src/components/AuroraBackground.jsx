import { motion } from "framer-motion";

const BLOBS = [
  {
    className:
      "w-[34rem] h-[34rem] bg-primary/25 dark:bg-primary/20 -top-24 -left-24",
    animate: { x: [0, 60, -30, 0], y: [0, 40, 10, 0] },
    duration: 22,
  },
  {
    className:
      "w-[30rem] h-[30rem] bg-primary-blue/20 dark:bg-primary-blue/15 top-1/4 -right-32",
    animate: { x: [0, -50, 30, 0], y: [0, 50, -20, 0] },
    duration: 26,
  },
  {
    className:
      "w-[26rem] h-[26rem] bg-primary-soft/15 dark:bg-primary-soft/10 bottom-0 left-1/3",
    animate: { x: [0, 40, -40, 0], y: [0, -30, 20, 0] },
    duration: 30,
  },
];

/** Subtle animated gradient blobs floating behind the whole page. */
export default function AuroraBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      {BLOBS.map((blob, i) => (
        <motion.div
          key={i}
          className={`absolute rounded-full blur-3xl ${blob.className}`}
          animate={blob.animate}
          transition={{ duration: blob.duration, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
      {/* faint grid for a modern SaaS feel */}
      <div
        className="absolute inset-0 opacity-[0.35] dark:opacity-20"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(100,116,139,0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(100,116,139,0.08) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
        }}
      />
    </div>
  );
}
