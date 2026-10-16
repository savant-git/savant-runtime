import { useEffect } from "react";
import gsap from "gsap";
import { CINEMATIC } from "../config/cinematic";

export function useEntryTransition(
  active: boolean,
  root: React.RefObject<HTMLDivElement | null>,
  onComplete: () => void,
) {
  useEffect(() => {
    if (!active || !root.current) return;
    const context = gsap.context(() => {
      gsap
        .timeline({ onComplete })
        .to(root.current, {
          clipPath: "inset(49.9% 0 49.9% 0)",
          filter: "brightness(2) blur(2px)",
          duration: 0.42,
          ease: "power3.in",
        })
        .to(root.current, {
          opacity: 0,
          duration: CINEMATIC.transitionDuration - 0.42,
          ease: "power2.out",
        });
    }, root);
    return () => context.revert();
  }, [active, onComplete, root]);
}
