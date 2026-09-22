(() => {
  "use strict";

  const doc = document;
  const root = doc.documentElement;
  const body = doc.body;

  if (
    !body ||
    body.dataset.presentUltra === "2"
  ) {
    return;
  }

  body.dataset.presentUltra = "2";
  body.dataset.hudGeneration = "20260819-hud2";

  const motionQuery =
    window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

  const pointerQuery =
    window.matchMedia(
      "(hover: none), (pointer: coarse)"
    );

  const reducedMotion =
    motionQuery.matches;

  const coarsePointer =
    pointerQuery.matches;

  const hardware =
    Number(
      navigator.hardwareConcurrency || 4
    );

  const memory =
    Number(
      navigator.deviceMemory || 4
    );

  const performanceTier =
    reducedMotion
      ? "reduced"
      : hardware >= 8 && memory >= 4
        ? "ultra"
        : hardware >= 4
          ? "standard"
          : "lite";

  body.dataset.performanceTier =
    performanceTier;

  if (
    performanceTier === "lite" ||
    performanceTier === "reduced"
  ) {
    root.style.setProperty(
      "--hud-grid-opacity",
      ".07"
    );

    root.style.setProperty(
      "--hud-atmosphere-opacity",
      ".68"
    );
  }

  function createLayer(
    className,
    parent = body
  ) {
    const existing =
      parent.querySelector(
        `:scope > .${className}`
      );

    if (existing) {
      return existing;
    }

    const element =
      doc.createElement("div");

    element.className =
      className;

    element.setAttribute(
      "aria-hidden",
      "true"
    );

    parent.appendChild(
      element
    );

    return element;
  }

  createLayer(
    "present-hud-environment"
  );

  createLayer(
    "present-hud-circuitry"
  );

  createLayer(
    "present-hud-scan"
  );

  createLayer(
    "present-grain"
  );

  createLayer(
    "present-vignette"
  );

  let systemState =
    doc.querySelector(
      ".present-system-state"
    );

  if (!systemState) {
    systemState =
      doc.createElement("div");

    systemState.className =
      "present-system-state";

    systemState.setAttribute(
      "aria-live",
      "polite"
    );

    body.appendChild(
      systemState
    );
  }

  function snapshot() {
    return (
      window.state &&
      window.state.data
    ) || null;
  }

  function updateSystemState() {
    const data =
      snapshot();

    const online =
      navigator.onLine;

    const hash =
      data &&
      data.snapshot_sha256
        ? String(
            data.snapshot_sha256
          ).slice(
            0,
            10
          )
        : "awaiting snapshot";

    const files =
      data &&
      data.metrics &&
      data.metrics.files != null
        ? Number(
            data.metrics.files
          ).toLocaleString()
        : "—";

    systemState.dataset.online =
      String(
        online
      );

    systemState.textContent =
      `${online ? "live" : "offline"} · ` +
      `${performanceTier} · ` +
      `${files} files · ` +
      `${hash}`;
  }

  updateSystemState();

  window.addEventListener(
    "online",
    updateSystemState
  );

  window.addEventListener(
    "offline",
    updateSystemState
  );

  function installCardLayers(
    card
  ) {
    if (
      card.dataset.presentHudLayers ===
      "1"
    ) {
      return;
    }

    card.dataset.presentHudLayers =
      "1";

    const frame =
      doc.createElement("span");

    frame.className =
      "present-hud-frame";

    frame.setAttribute(
      "aria-hidden",
      "true"
    );

    const glass =
      doc.createElement("span");

    glass.className =
      "present-hud-glass";

    glass.setAttribute(
      "aria-hidden",
      "true"
    );

    const energy =
      doc.createElement("span");

    energy.className =
      "present-hud-energy";

    energy.setAttribute(
      "aria-hidden",
      "true"
    );

    const telemetry =
      doc.createElement("span");

    telemetry.className =
      "present-hud-telemetry";

    telemetry.setAttribute(
      "aria-hidden",
      "true"
    );

    telemetry.innerHTML =
      "<i></i><i></i><i></i>";

    card.prepend(
      frame,
      glass,
      energy,
      telemetry
    );
  }

  function resetCardPerspective(
    card
  ) {
    card.style.setProperty(
      "--present-rx",
      "0deg"
    );

    card.style.setProperty(
      "--present-ry",
      "0deg"
    );

    card.style.setProperty(
      "--card-x",
      "50%"
    );

    card.style.setProperty(
      "--card-y",
      "50%"
    );
  }

  function installCardInteraction(
    card
  ) {
    if (
      card.dataset.presentInteraction ===
      "1"
    ) {
      return;
    }

    card.dataset.presentInteraction =
      "1";

    if (
      coarsePointer ||
      reducedMotion
    ) {
      return;
    }

    let frame = 0;
    let latestEvent = null;

    const render =
      () => {
        frame = 0;

        if (!latestEvent) {
          return;
        }

        const rect =
          card.getBoundingClientRect();

        if (
          rect.width <= 0 ||
          rect.height <= 0
        ) {
          return;
        }

        const px =
          Math.max(
            0,
            Math.min(
              1,
              (
                latestEvent.clientX -
                rect.left
              ) / rect.width
            )
          );

        const py =
          Math.max(
            0,
            Math.min(
              1,
              (
                latestEvent.clientY -
                rect.top
              ) / rect.height
            )
          );

        const ry =
          (px - .5) * 5.4;

        const rx =
          (.5 - py) * 4.1;

        card.style.setProperty(
          "--present-rx",
          `${rx.toFixed(2)}deg`
        );

        card.style.setProperty(
          "--present-ry",
          `${ry.toFixed(2)}deg`
        );

        card.style.setProperty(
          "--card-x",
          `${(px * 100).toFixed(1)}%`
        );

        card.style.setProperty(
          "--card-y",
          `${(py * 100).toFixed(1)}%`
        );
      };

    card.addEventListener(
      "pointermove",
      event => {
        latestEvent =
          event;

        if (!frame) {
          frame =
            requestAnimationFrame(
              render
            );
        }
      },
      {
        passive: true
      }
    );

    card.addEventListener(
      "pointerleave",
      () => {
        latestEvent =
          null;

        if (frame) {
          cancelAnimationFrame(
            frame
          );

          frame = 0;
        }

        resetCardPerspective(
          card
        );
      }
    );
  }

  function enhanceCards(
    scope = doc
  ) {
    const cards =
      [
        ...scope.querySelectorAll(
          ".card"
        )
      ];

    cards.forEach(
      (
        card,
        index
      ) => {
        installCardLayers(
          card
        );

        installCardInteraction(
          card
        );

        card.style.setProperty(
          "--present-order",
          String(
            index
          )
        );

        if (
          card.dataset.presentEnhanced !==
          "1"
        ) {
          card.dataset.presentEnhanced =
            "1";

          card.classList.add(
            "present-enter"
          );
        }
      }
    );
  }

  enhanceCards();

  let globalPointerFrame = 0;
  let globalPointerEvent = null;

  function updateGlobalPointer() {
    globalPointerFrame = 0;

    if (!globalPointerEvent) {
      return;
    }

    const x =
      globalPointerEvent.clientX;

    const y =
      globalPointerEvent.clientY;

    root.style.setProperty(
      "--present-mx",
      `${x}px`
    );

    root.style.setProperty(
      "--present-my",
      `${y}px`
    );

    const nx =
      (
        x /
        Math.max(
          window.innerWidth,
          1
        )
      ) - .5;

    const ny =
      (
        y /
        Math.max(
          window.innerHeight,
          1
        )
      ) - .5;

    root.style.setProperty(
      "--present-depth-x",
      nx.toFixed(4)
    );

    root.style.setProperty(
      "--present-depth-y",
      ny.toFixed(4)
    );
  }

  if (
    !coarsePointer &&
    !reducedMotion
  ) {
    doc.addEventListener(
      "pointermove",
      event => {
        globalPointerEvent =
          event;

        if (
          !globalPointerFrame
        ) {
          globalPointerFrame =
            requestAnimationFrame(
              updateGlobalPointer
            );
        }
      },
      {
        passive: true
      }
    );
  }

  const mutationObserver =
    new MutationObserver(
      mutations => {
        let changed = false;

        for (
          const mutation of mutations
        ) {
          if (
            mutation.addedNodes.length
          ) {
            changed = true;
            break;
          }
        }

        if (!changed) {
          return;
        }

        enhanceCards();
        updateSystemState();
        installDemoStatus();
      }
    );

  mutationObserver.observe(
    body,
    {
      childList: true,
      subtree: true
    }
  );

  let idleTimer = 0;

  function wake() {
    body.classList.remove(
      "present-idle"
    );

    window.clearTimeout(
      idleTimer
    );

    idleTimer =
      window.setTimeout(
        () => {
          if (
            !body.classList.contains(
              "demo-mode"
            )
          ) {
            body.classList.add(
              "present-idle"
            );
          }
        },
        6500
      );
  }

  [
    "pointermove",
    "pointerdown",
    "keydown",
    "touchstart"
  ].forEach(
    eventName => {
      doc.addEventListener(
        eventName,
        wake,
        {
          passive:
            eventName !==
            "keydown"
        }
      );
    }
  );

  wake();

  doc.addEventListener(
    "visibilitychange",
    () => {
      body.classList.toggle(
        "present-paused",
        doc.hidden
      );

      if (!doc.hidden) {
        updateSystemState();

        if (
          typeof window.savantToast ===
          "function"
        ) {
          window.savantToast(
            "observatory synchronized"
          );
        }
      }
    }
  );

  let focusMode = false;

  function setFocusMode(
    value
  ) {
    focusMode =
      Boolean(
        value
      );

    body.classList.toggle(
      "present-focus",
      focusMode
    );

    if (
      typeof window.savantToast ===
      "function"
    ) {
      window.savantToast(
        focusMode
          ? "focus mode"
          : "interface restored"
      );
    }
  }

  doc.addEventListener(
    "keydown",
    event => {
      const active =
        doc.activeElement;

      const tag =
        active &&
        active.tagName;

      const typing =
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        (
          active &&
          active.isContentEditable
        );

      if (typing) {
        return;
      }

      if (
        event.key.toLowerCase() ===
          "f" &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.altKey
      ) {
        event.preventDefault();

        setFocusMode(
          !focusMode
        );
      }
    }
  );

  function installDemoStatus() {
    const hud =
      doc.querySelector(
        "#demoHud"
      );

    if (
      !hud ||
      hud.querySelector(
        ".present-demo-status"
      )
    ) {
      return;
    }

    const status =
      doc.createElement("div");

    status.className =
      "present-demo-status";

    status.innerHTML =
      '<span class="present-demo-dot"></span>' +
      '<span id="presentDemoState">demonstration ready</span>';

    const target =
      hud.querySelector(
        "#demoMeta"
      );

    if (target) {
      target.insertAdjacentElement(
        "afterend",
        status
      );
    } else {
      hud.appendChild(
        status
      );
    }

    let started = 0;
    let lastVisible = false;

    function tick() {
      const visible =
        hud.classList.contains(
          "show"
        );

      if (
        visible &&
        !lastVisible
      ) {
        started =
          performance.now();
      }

      lastVisible =
        visible;

      const output =
        doc.querySelector(
          "#presentDemoState"
        );

      if (
        visible &&
        output
      ) {
        const seconds =
          Math.max(
            0,
            Math.floor(
              (
                performance.now() -
                started
              ) / 1000
            )
          );

        const minute =
          Math.floor(
            seconds / 60
          );

        const second =
          String(
            seconds % 60
          ).padStart(
            2,
            "0"
          );

        const title =
          doc.querySelector(
            "#demoKicker"
          );

        output.textContent =
          `${
            title
              ? title.textContent
              : "demonstration"
          } · ${minute}:${second}`;
      }

      if (
        !doc.hidden &&
        !reducedMotion
      ) {
        requestAnimationFrame(
          tick
        );
      } else {
        window.setTimeout(
          tick,
          1000
        );
      }
    }

    requestAnimationFrame(
      tick
    );
  }

  installDemoStatus();

  function enhanceNavigation() {
    const originalNavigate =
      window.navigate;

    if (
      typeof originalNavigate !==
        "function" ||
      originalNavigate.presentEnhanced
    ) {
      return;
    }

    const enhancedNavigate =
      function enhancedNavigate(
        name
      ) {
        const target =
          doc.querySelector(
            `.view[data-view="${name}"]`
          );

        if (
          doc.startViewTransition &&
          !reducedMotion &&
          target
        ) {
          doc.startViewTransition(
            () => {
              originalNavigate(
                name
              );
            }
          );
        } else {
          originalNavigate(
            name
          );
        }

        requestAnimationFrame(
          () => {
            const current =
              doc.querySelector(
                `.view[data-view="${name}"]`
              );

            if (current) {
              enhanceCards(
                current
              );
            }
          }
        );
      };

    enhancedNavigate.presentEnhanced =
      true;

    window.navigate =
      enhancedNavigate;
  }

  enhanceNavigation();

  function magneticControls() {
    if (
      coarsePointer ||
      reducedMotion
    ) {
      return;
    }

    const controls =
      doc.querySelectorAll(
        "#enter, #tourBtn, #searchBtn, #fullBtn"
      );

    controls.forEach(
      control => {
        if (
          control.dataset.presentMagnetic ===
          "1"
        ) {
          return;
        }

        control.dataset.presentMagnetic =
          "1";

        control.addEventListener(
          "pointermove",
          event => {
            const rect =
              control.getBoundingClientRect();

            const x =
              event.clientX -
              (
                rect.left +
                rect.width / 2
              );

            const y =
              event.clientY -
              (
                rect.top +
                rect.height / 2
              );

            control.style.transform =
              `translate3d(` +
              `${(x * .055).toFixed(2)}px,` +
              `${(y * .055).toFixed(2)}px,` +
              `8px)`;
          },
          {
            passive: true
          }
        );

        control.addEventListener(
          "pointerleave",
          () => {
            control.style.transform =
              "";
          }
        );
      }
    );
  }

  magneticControls();

  const visibilityObserver =
    "IntersectionObserver" in window
      ? new IntersectionObserver(
          entries => {
            entries.forEach(
              entry => {
                entry.target.dataset.hudVisible =
                  String(
                    entry.isIntersecting
                  );
              }
            );
          },
          {
            rootMargin:
              "120px 0px 120px 0px",
            threshold: .01
          }
        )
      : null;

  function observeCards() {
    if (!visibilityObserver) {
      return;
    }

    doc.querySelectorAll(
      ".card:not([data-hud-observed])"
    ).forEach(
      card => {
        card.dataset.hudObserved =
          "1";

        visibilityObserver.observe(
          card
        );
      }
    );
  }

  observeCards();

  const observerRefresh =
    new MutationObserver(
      () => {
        observeCards();
        magneticControls();
        enhanceNavigation();
      }
    );

  observerRefresh.observe(
    body,
    {
      childList: true,
      subtree: true
    }
  );

  function refreshAfterSnapshot() {
    const data =
      snapshot();

    if (!data) {
      return false;
    }

    updateSystemState();
    enhanceCards();
    observeCards();

    return true;
  }

  if (
    !refreshAfterSnapshot()
  ) {
    let attempts = 0;

    const timer =
      window.setInterval(
        () => {
          attempts += 1;

          if (
            refreshAfterSnapshot() ||
            attempts >= 40
          ) {
            clearInterval(
              timer
            );
          }
        },
        250
      );
  }

  window.addEventListener(
    "resize",
    () => {
      if (
        coarsePointer ||
        reducedMotion
      ) {
        doc.querySelectorAll(
          ".card"
        ).forEach(
          resetCardPerspective
        );
      }
    },
    {
      passive: true
    }
  );

  window.presentUltra = {
    version:
      "2.0.0",
    generation:
      "20260819-hud2",
    performanceTier,
    setFocusMode,
    refresh() {
      enhanceCards();
      observeCards();
      magneticControls();
      updateSystemState();
    }
  };
})();
