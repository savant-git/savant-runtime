import { useEffect } from "react";
import type gsap from "gsap";
export function usePageVisibility(
  timeline: React.MutableRefObject<gsap.core.Timeline | null>,
) {
  useEffect(() => {
    const onChange = () => {
      if (document.hidden) timeline.current?.pause();
      else timeline.current?.resume();
    };
    document.addEventListener("visibilitychange", onChange);
    return () => document.removeEventListener("visibilitychange", onChange);
  }, [timeline]);
}
