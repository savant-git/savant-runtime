import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { RefObject } from "react";

gsap.registerPlugin(ScrollTrigger);

interface SavantExperienceOptions {
  root: RefObject<HTMLElement | null>;
  entered: boolean;
}

type Cleanup = () => void;

const reducedMotionQuery = "(prefers-reduced-motion: reduce)";
const finePointerQuery = "(pointer: fine)";

function reducedMotion() {
  return window.matchMedia(reducedMotionQuery).matches;
}

function supportsFinePointer() {
  return (
    window.matchMedia(finePointerQuery).matches
    && !reducedMotion()
  );
}

function clamp(
  value: number,
  minimum: number,
  maximum: number,
) {
  return Math.max(
    minimum,
    Math.min(maximum, value),
  );
}

function dispatchActiveSection(
  root: HTMLElement,
  section: string,
) {
  root.dataset.activeSection = section;

  window.dispatchEvent(
    new CustomEvent(
      "savant:section",
      {
        detail: { section },
      },
    ),
  );
}

function mountScrollState(
  root: HTMLElement,
): Cleanup {
  let frame = 0;
  let previousY = window.scrollY;

  const update = () => {
    frame = 0;

    const documentElement =
      document.documentElement;

    const maximum =
      documentElement.scrollHeight
      - documentElement.clientHeight;

    const progress =
      maximum > 0
        ? clamp(
            window.scrollY / maximum,
            0,
            1,
          )
        : 0;

    const direction =
      window.scrollY > previousY
        ? "down"
        : window.scrollY < previousY
          ? "up"
          : "idle";

    previousY = window.scrollY;

    root.style.setProperty(
      "--scroll-progress",
      String(progress),
    );

    root.style.setProperty(
      "--scroll-progress-percent",
      `${progress * 100}%`,
    );

    root.dataset.scrollDirection =
      direction;
  };

  const requestUpdate = () => {
    if (frame) return;

    frame =
      window.requestAnimationFrame(
        update,
      );
  };

  update();

  window.addEventListener(
    "scroll",
    requestUpdate,
    { passive: true },
  );

  window.addEventListener(
    "resize",
    requestUpdate,
    { passive: true },
  );

  return () => {
    window.removeEventListener(
      "scroll",
      requestUpdate,
    );

    window.removeEventListener(
      "resize",
      requestUpdate,
    );

    if (frame) {
      window.cancelAnimationFrame(frame);
    }
  };
}

function mountPointerProjection(
  root: HTMLElement,
): Cleanup {
  if (!supportsFinePointer()) {
    return () => undefined;
  }

  let frame = 0;
  let latestX = window.innerWidth / 2;
  let latestY = window.innerHeight / 2;

  const commit = () => {
    frame = 0;

    const width =
      Math.max(1, window.innerWidth);

    const height =
      Math.max(1, window.innerHeight);

    root.style.setProperty(
      "--pointer-x",
      `${latestX}px`,
    );

    root.style.setProperty(
      "--pointer-y",
      `${latestY}px`,
    );

    root.style.setProperty(
      "--pointer-x-normalized",
      String(
        latestX / width - 0.5,
      ),
    );

    root.style.setProperty(
      "--pointer-y-normalized",
      String(
        latestY / height - 0.5,
      ),
    );
  };

  const move = (
    event: PointerEvent,
  ) => {
    latestX = event.clientX;
    latestY = event.clientY;

    if (frame) return;

    frame =
      window.requestAnimationFrame(
        commit,
      );
  };

  window.addEventListener(
    "pointermove",
    move,
    { passive: true },
  );

  return () => {
    window.removeEventListener(
      "pointermove",
      move,
    );

    if (frame) {
      window.cancelAnimationFrame(frame);
    }
  };
}

function mountMagnetism(
  root: HTMLElement,
): Cleanup {
  if (!supportsFinePointer()) {
    return () => undefined;
  }

  const cleanups: Cleanup[] = [];

  const targets =
    Array.from(
      root.querySelectorAll<HTMLElement>(
        "[data-magnetic]",
      ),
    );

  targets.forEach((target) => {
    const xTo =
      gsap.quickTo(
        target,
        "x",
        {
          duration: 0.32,
          ease: "power3.out",
        },
      );

    const yTo =
      gsap.quickTo(
        target,
        "y",
        {
          duration: 0.32,
          ease: "power3.out",
        },
      );

    const move = (
      event: PointerEvent,
    ) => {
      const rect =
        target.getBoundingClientRect();

      const x =
        event.clientX
        - rect.left
        - rect.width / 2;

      const y =
        event.clientY
        - rect.top
        - rect.height / 2;

      xTo(x * 0.12);
      yTo(y * 0.12);
    };

    const reset = () => {
      gsap.to(
        target,
        {
          x: 0,
          y: 0,
          duration: 0.52,
          ease: "power3.out",
          overwrite: true,
        },
      );
    };

    target.addEventListener(
      "pointermove",
      move,
      { passive: true },
    );

    target.addEventListener(
      "pointerleave",
      reset,
    );

    cleanups.push(() => {
      target.removeEventListener(
        "pointermove",
        move,
      );

      target.removeEventListener(
        "pointerleave",
        reset,
      );

      gsap.killTweensOf(target);
    });
  });

  return () => {
    cleanups
      .reverse()
      .forEach((cleanup) => cleanup());
  };
}

function mountDepth(
  root: HTMLElement,
): Cleanup {
  if (!supportsFinePointer()) {
    return () => undefined;
  }

  const cleanups: Cleanup[] = [];

  const cards =
    Array.from(
      root.querySelectorAll<HTMLElement>(
        "[data-depth]",
      ),
    );

  cards.forEach((card) => {
    let frame = 0;
    let x = 0;
    let y = 0;

    const commit = () => {
      frame = 0;

      card.style.setProperty(
        "--depth-x",
        String(x),
      );

      card.style.setProperty(
        "--depth-y",
        String(y),
      );
    };

    const move = (
      event: PointerEvent,
    ) => {
      const rect =
        card.getBoundingClientRect();

      x =
        (
          event.clientX
          - rect.left
        )
        / Math.max(rect.width, 1)
        - 0.5;

      y =
        (
          event.clientY
          - rect.top
        )
        / Math.max(rect.height, 1)
        - 0.5;

      if (frame) return;

      frame =
        window.requestAnimationFrame(
          commit,
        );
    };

    const leave = () => {
      x = 0;
      y = 0;
      commit();
    };

    card.addEventListener(
      "pointermove",
      move,
      { passive: true },
    );

    card.addEventListener(
      "pointerleave",
      leave,
    );

    cleanups.push(() => {
      card.removeEventListener(
        "pointermove",
        move,
      );

      card.removeEventListener(
        "pointerleave",
        leave,
      );

      if (frame) {
        window.cancelAnimationFrame(frame);
      }
    });
  });

  return () => {
    cleanups
      .reverse()
      .forEach((cleanup) => cleanup());
  };
}

function mountSections(
  root: HTMLElement,
): Cleanup {
  if (
    !("IntersectionObserver" in window)
  ) {
    return () => undefined;
  }

  const sections =
    Array.from(
      root.querySelectorAll<HTMLElement>(
        "[data-section]",
      ),
    );

  const observer =
    new IntersectionObserver(
      (entries) => {
        const visible =
          entries
            .filter(
              (entry) =>
                entry.isIntersecting,
            )
            .sort(
              (a, b) =>
                b.intersectionRatio
                - a.intersectionRatio,
            )[0];

        if (!visible) return;

        const target =
          visible.target as HTMLElement;

        const section =
          target.dataset.section;

        if (
          !section
          || section
            === root.dataset.activeSection
        ) {
          return;
        }

        dispatchActiveSection(
          root,
          section,
        );
      },
      {
        rootMargin:
          "-16% 0px -46% 0px",

        threshold: [
          0.12,
          0.24,
          0.42,
          0.62,
        ],
      },
    );

  sections.forEach(
    (section) =>
      observer.observe(section),
  );

  return () =>
    observer.disconnect();
}

function mountReveals(
  root: HTMLElement,
): Cleanup {
  const targets =
    gsap.utils.toArray<HTMLElement>(
      "[data-reveal]",
      root,
    );

  if (reducedMotion()) {
    gsap.set(
      targets,
      {
        opacity: 1,
        y: 0,
        filter: "blur(0px)",
      },
    );

    return () => undefined;
  }

  const context =
    gsap.context(
      () => {
        targets.forEach((target) => {
          gsap.fromTo(
            target,
            {
              opacity: 0,
              y: 30,
              filter: "blur(7px)",
            },
            {
              opacity: 1,
              y: 0,
              filter: "blur(0px)",
              duration: 0.88,
              ease: "power4.out",
              scrollTrigger: {
                trigger: target,
                start: "top 90%",
                once: true,
              },
            },
          );
        });

        gsap.utils
          .toArray<HTMLElement>(
            "[data-parallax]",
            root,
          )
          .forEach((target) => {
            const strength =
              Number(
                target.dataset.parallax
                ?? "7",
              );

            gsap.fromTo(
              target,
              {
                yPercent:
                  strength * -0.4,
              },
              {
                yPercent:
                  strength * 0.4,
                ease: "none",
                scrollTrigger: {
                  trigger:
                    target.closest(
                      "section",
                    )
                    ?? target,
                  start: "top bottom",
                  end: "bottom top",
                  scrub: 1,
                },
              },
            );
          });

        gsap.utils
          .toArray<HTMLElement>(
            "[data-trace]",
            root,
          )
          .forEach((target) => {
            gsap.fromTo(
              target,
              {
                scaleX: 0,
              },
              {
                scaleX: 1,
                ease: "none",
                scrollTrigger: {
                  trigger: target,
                  start: "top 92%",
                  end: "top 42%",
                  scrub: 0.7,
                },
              },
            );
          });
      },
      root,
    );

  return () =>
    context.revert();
}

function mountVisibilityState(
  root: HTMLElement,
): Cleanup {
  const update = () => {
    root.dataset.visibility =
      document.hidden
        ? "hidden"
        : "visible";

    if (document.hidden) {
      gsap.globalTimeline.pause();
    } else {
      gsap.globalTimeline.resume();
      ScrollTrigger.refresh();
    }
  };

  update();

  document.addEventListener(
    "visibilitychange",
    update,
  );

  return () => {
    document.removeEventListener(
      "visibilitychange",
      update,
    );

    gsap.globalTimeline.resume();
  };
}

function mountInteractionModality(
  root: HTMLElement,
): Cleanup {
  const pointer = () => {
    root.dataset.input =
      "pointer";
  };

  const keyboard = (
    event: KeyboardEvent,
  ) => {
    if (
      event.key === "Tab"
      || event.key.startsWith(
        "Arrow",
      )
    ) {
      root.dataset.input =
        "keyboard";
    }
  };

  window.addEventListener(
    "pointerdown",
    pointer,
    { passive: true },
  );

  window.addEventListener(
    "keydown",
    keyboard,
  );

  return () => {
    window.removeEventListener(
      "pointerdown",
      pointer,
    );

    window.removeEventListener(
      "keydown",
      keyboard,
    );
  };
}

export function mountSavantExperience({
  root,
  entered,
}: SavantExperienceOptions): () => void {
  const element =
    root.current;

  if (
    !element
    || !entered
  ) {
    return () => undefined;
  }

  const cleanups: Cleanup[] = [];

  element.dataset.motion =
    reducedMotion()
      ? "reduced"
      : "full";

  element.dataset.visibility =
    document.hidden
      ? "hidden"
      : "visible";

  element.dataset.input =
    "pointer";

  cleanups.push(
    mountReveals(element),
    mountScrollState(element),
    mountPointerProjection(element),
    mountMagnetism(element),
    mountDepth(element),
    mountSections(element),
    mountVisibilityState(element),
    mountInteractionModality(element),
  );

  const refresh = () => {
    ScrollTrigger.refresh();
  };

  window.addEventListener(
    "load",
    refresh,
    { once: true },
  );

  cleanups.push(() => {
    window.removeEventListener(
      "load",
      refresh,
    );
  });

  return () => {
    cleanups
      .reverse()
      .forEach(
        (cleanup) =>
          cleanup(),
      );

    ScrollTrigger
      .getAll()
      .forEach(
        (trigger) =>
          trigger.kill(),
      );
  };
}
