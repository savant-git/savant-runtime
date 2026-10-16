(() => {
  "use strict";

  const SCHEMA =
    "savant.niche.living-pulse.v1";

  const runtime = {
    initialized: false,
    open: false,
    generation: 0,
    controller: null,
    previousFocus: null,
    sequence: null,
    hash: null,
    surfaces: new Map(),
    changes: [],
    available: "unknown"
  };

  const represented = value =>
    value !== null &&
    value !== undefined &&
    value !== "";

  const valueText = (
    value,
    fallback = "unknown"
  ) => {
    if (!represented(value)) {
      return fallback;
    }

    if (typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch {
        return fallback;
      }
    }

    return String(value);
  };

  const escapeHtml = value =>
    valueText(value, "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const first = (
    object,
    keys
  ) => {
    for (const key of keys) {
      if (
        object &&
        Object.prototype
          .hasOwnProperty.call(
            object,
            key
          ) &&
        represented(object[key])
      ) {
        return object[key];
      }
    }

    return null;
  };

  const normalizeSurface = (
    value,
    fallbackId = null
  ) => {
    if (
      typeof value === "string"
    ) {
      return {
        id: value,
        name: value,
        signature: value
      };
    }

    if (
      !value ||
      typeof value !== "object"
    ) {
      return null;
    }

    const id =
      first(
        value,
        [
          "surface_id",
          "id",
          "name",
          "path",
          "key"
        ]
      ) ||
      fallbackId;

    if (!represented(id)) {
      return null;
    }

    const name =
      first(
        value,
        [
          "label",
          "name",
          "surface_id",
          "id",
          "path"
        ]
      ) ||
      id;

    let signature;

    try {
      signature =
        JSON.stringify(
          value,
          Object.keys(value).sort()
        );
    } catch {
      signature =
        valueText(value);
    }

    return {
      id: String(id),
      name: String(name),
      signature
    };
  };

  const surfaceMap = payload => {
    const candidates = [
      payload?.surfaces,
      payload?.fabric?.surfaces,
      payload?.catalog?.surfaces,
      payload?.current?.surfaces
    ];

    const result =
      new Map();

    for (const candidate of candidates) {
      if (Array.isArray(candidate)) {
        candidate.forEach(
          (value, index) => {
            const surface =
              normalizeSurface(
                value,
                `surface-${index}`
              );

            if (surface) {
              result.set(
                surface.id,
                surface
              );
            }
          }
        );

        if (result.size) {
          return result;
        }
      }

      if (
        candidate &&
        typeof candidate === "object"
      ) {
        Object.entries(candidate)
          .forEach(
            ([key, value]) => {
              const surface =
                normalizeSurface(
                  value,
                  key
                );

              if (surface) {
                result.set(
                  surface.id,
                  surface
                );
              }
            }
          );

        if (result.size) {
          return result;
        }
      }
    }

    return result;
  };

  const diffSurfaces = (
    previous,
    next
  ) => {
    const changes = [];

    for (
      const [id, surface]
      of next.entries()
    ) {
      const prior =
        previous.get(id);

      if (!prior) {
        changes.push({
          id,
          name: surface.name,
          state: "appeared"
        });
        continue;
      }

      if (
        prior.signature !==
        surface.signature
      ) {
        changes.push({
          id,
          name: surface.name,
          state: "changed"
        });
      }
    }

    for (
      const [id, surface]
      of previous.entries()
    ) {
      if (!next.has(id)) {
        changes.push({
          id,
          name: surface.name,
          state: "no-longer-represented"
        });
      }
    }

    return changes;
  };

  const fetchFabric = async () => {
    runtime.generation += 1;

    const generation =
      runtime.generation;

    runtime.controller?.abort();

    const controller =
      new AbortController();

    runtime.controller =
      controller;

    try {
      const response =
        await fetch(
          "/api/living/fabric",
          {
            signal: controller.signal,
            cache: "no-store",
            headers: {
              Accept: "application/json"
            }
          }
        );

      if (
        generation !==
          runtime.generation ||
        !response.ok
      ) {
        return null;
      }

      const payload =
        await response.json();

      if (
        generation !==
        runtime.generation
      ) {
        return null;
      }

      return payload;
    } catch (error) {
      if (
        error?.name === "AbortError"
      ) {
        return null;
      }

      return null;
    } finally {
      if (
        runtime.controller ===
        controller
      ) {
        runtime.controller = null;
      }
    }
  };

  const render = () => {
    const body =
      document.getElementById(
        "niche-pulse-body"
      );

    if (!body) {
      return;
    }

    const changes =
      runtime.changes;

    body.innerHTML = `
      <div class="niche-pulse-summary">
        <span class="niche-pulse-chip">
          availability:${
            escapeHtml(runtime.available)
          }
        </span>

        <span class="niche-pulse-chip">
          sequence:${
            escapeHtml(runtime.sequence)
          }
        </span>

        <span class="niche-pulse-chip">
          surfaces:${
            runtime.surfaces.size
          }
        </span>

        <span class="niche-pulse-chip">
          changed:${changes.length}
        </span>
      </div>

      ${
        changes.length
          ? `
            <ol class="niche-pulse-list">
              ${changes.map(
                change => `
                  <li
                    class="
                      niche-pulse-surface
                      niche-pulse-flash
                    "
                  >
                    <span
                      class="
                        niche-pulse-surface-name
                      "
                    >
                      ${escapeHtml(
                        change.name
                      )}
                    </span>

                    <span
                      class="
                        niche-pulse-surface-state
                      "
                    >
                      ${escapeHtml(
                        change.state
                      )}
                    </span>
                  </li>
                `
              ).join("")}
            </ol>
          `
          : `
            <div class="niche-pulse-empty">
              No changed surfaces are
              represented by the current
              comparison.
            </div>
          `
      }

      <div class="niche-pulse-boundary">
        Living Pulse displays only observed
        differences between successive
        Living Fabric projections. It does
        not infer semantic importance,
        authority, causation, or priority
        from a changed surface.
      </div>
    `;
  };

  const refresh = async () => {
    const payload =
      await fetchFabric();

    if (!payload) {
      runtime.available =
        "unavailable";

      render();
      return;
    }

    const next =
      surfaceMap(payload);

    const sequence =
      first(
        payload,
        [
          "sequence",
          "fabric_sequence"
        ]
      ) ??
      first(
        payload?.metadata,
        ["sequence"]
      ) ??
      first(
        payload?.current,
        ["sequence"]
      );

    const hash =
      first(
        payload,
        [
          "hash",
          "fabric_hash"
        ]
      ) ??
      first(
        payload?.metadata,
        ["hash"]
      ) ??
      first(
        payload?.current,
        ["hash"]
      );

    const hadBaseline =
      runtime.surfaces.size > 0 ||
      runtime.sequence !== null ||
      runtime.hash !== null;

    const changes =
      hadBaseline
        ? diffSurfaces(
            runtime.surfaces,
            next
          )
        : [];

    const sequenceChanged =
      hadBaseline &&
      represented(sequence) &&
      sequence !== runtime.sequence;

    const hashChanged =
      hadBaseline &&
      represented(hash) &&
      hash !== runtime.hash;

    runtime.available =
      "available";

    runtime.sequence =
      sequence;

    runtime.hash =
      hash;

    runtime.surfaces =
      next;

    runtime.changes =
      changes;

    render();

    if (
      changes.length ||
      sequenceChanged ||
      hashChanged
    ) {
      window.dispatchEvent(
        new CustomEvent(
          "niche:living-pulse",
          {
            detail: {
              schema: SCHEMA,
              sequence,
              hash,
              changedSurfaces:
                changes.map(
                  change => ({
                    ...change
                  })
                ),
              authorityEffect: "none",
              projectionOnly: true
            }
          }
        )
      );
    }
  };

  const ensureShell = () => {
    if (
      document.getElementById(
        "niche-living-pulse"
      )
    ) {
      return;
    }

    const shell =
      document.createElement("aside");

    shell.id =
      "niche-living-pulse";

    shell.className =
      "niche-living-pulse";

    shell.hidden = true;

    shell.setAttribute(
      "aria-label",
      "Living Pulse"
    );

    shell.innerHTML = `
      <header class="niche-pulse-head">
        <div>
          <p class="niche-pulse-kicker">
            living fabric / observed change
          </p>

          <h2 class="niche-pulse-title">
            LIVING PULSE
          </h2>
        </div>

        <button
          type="button"
          class="niche-pulse-close"
          aria-label="Close Living Pulse"
        >
          ×
        </button>
      </header>

      <div
        class="niche-pulse-body"
        id="niche-pulse-body"
      ></div>
    `;

    document.body.append(shell);

    shell
      .querySelector(
        ".niche-pulse-close"
      )
      ?.addEventListener(
        "click",
        close
      );
  };

  const open = async () => {
    ensureShell();

    const shell =
      document.getElementById(
        "niche-living-pulse"
      );

    if (!shell) {
      return;
    }

    runtime.previousFocus =
      document.activeElement;

    runtime.open = true;
    shell.hidden = false;

    await refresh();

    shell
      .querySelector(
        ".niche-pulse-close"
      )
      ?.focus();
  };

  const close = () => {
    runtime.open = false;
    runtime.controller?.abort();

    const shell =
      document.getElementById(
        "niche-living-pulse"
      );

    if (shell) {
      shell.hidden = true;
    }

    if (
      runtime.previousFocus &&
      document.contains(
        runtime.previousFocus
      )
    ) {
      runtime.previousFocus.focus();
    }
  };

  const bindTriggers = () => {
    document.addEventListener(
      "click",
      event => {
        const trigger =
          event.target.closest(
            [
              "[data-action='living-pulse']",
              "[data-command='living-pulse']",
              "[data-living-pulse]"
            ].join(",")
          );

        if (trigger) {
          void open();
        }
      },
      true
    );
  };

  const bindRuntime = () => {
    window.addEventListener(
      "niche:semantic-runtime-update",
      event => {
        if (
          event.detail?.changed ||
          runtime.open
        ) {
          void refresh();
        }
      }
    );
  };

  const bindKeyboard = () => {
    document.addEventListener(
      "keydown",
      event => {
        const target =
          event.target;

        const editing =
          target instanceof
            HTMLInputElement ||
          target instanceof
            HTMLTextAreaElement ||
          target?.isContentEditable;

        if (
          event.key === "Escape" &&
          runtime.open
        ) {
          event.preventDefault();
          close();
          return;
        }

        if (
          editing ||
          runtime.open
        ) {
          return;
        }

        if (
          event.altKey &&
          event.shiftKey &&
          event.key.toLowerCase() === "l"
        ) {
          event.preventDefault();
          void open();
        }
      }
    );
  };

  const initialize = () => {
    if (runtime.initialized) {
      return;
    }

    runtime.initialized = true;

    ensureShell();
    bindTriggers();
    bindRuntime();
    bindKeyboard();

    document.documentElement.dataset
      .nicheLivingPulse =
      "ready";

    void refresh();

    window.dispatchEvent(
      new CustomEvent(
        "niche:living-pulse-ready",
        {
          detail: {
            schema: SCHEMA,
            authorityEffect: "none",
            projectionOnly: true
          }
        }
      )
    );
  };

  window.NicheLivingPulse =
    Object.freeze({
      open,
      close,
      refresh,

      state: () => ({
        schema: SCHEMA,
        open: runtime.open,
        availability:
          runtime.available,
        sequence:
          runtime.sequence,
        surfaceCount:
          runtime.surfaces.size,
        changedSurfaceCount:
          runtime.changes.length,
        authorityEffect: "none",
        projectionOnly: true
      })
    });

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      initialize,
      { once: true }
    );
  } else {
    initialize();
  }
})();
