import gsap from "gsap";
import { CINEMATIC } from "../config/cinematic";

interface TimelineOptions {
  reducedMotion: boolean;
  onProgress: (value: number) => void;
  onComplete: () => void;
}

export function createMasterTimeline(
  playhead: { time: number },
  options: TimelineOptions,
) {
  let lastReported = -1;
  const duration = options.reducedMotion
    ? CINEMATIC.reducedMotionDuration
    : CINEMATIC.duration;
  const timeline = gsap.timeline({
    paused: true,
    defaults: { ease: "none" },
    onComplete: options.onComplete,
  });
  timeline.to(playhead, {
    time: CINEMATIC.duration,
    duration,
    onUpdate: () => {
      const progress = timeline.progress();
      if (progress - lastReported >= 0.01 || progress === 1) {
        lastReported = progress;
        options.onProgress(progress);
      }
    },
  });
  return timeline;
}
