import {
  ChangeEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AlertTriangle,
  Check,
  ImagePlus,
  LoaderCircle,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Square,
  Upload,
  X,
} from "lucide-react";


type Capability = {
  id: string;
  group: string;
  status: string;
};


type UrgeConfig = {
  exile_id: string;
  name: string;
  designation: string;
  capabilities: Capability[];
  accent: {
    primary: string;
    secondary: string;
    signal: string;
  };
};


type UnknownRecord =
  Record<string, unknown>;


type Baseline = {
  kind: "image";
  name: string;
  media_type: string;
  source: string;
};


type PraxisIteration = {
  schema?: string;
  owner?: string;
  capability?: string;
  index: number;
  iterations: number;
  complete?: boolean;
  digest?: string;
  creative?: UnknownRecord;
  logo?: UnknownRecord;
  renderer?: UnknownRecord;
  workbench?: UnknownRecord;
  lineage?: UnknownRecord;
};


type PraxisState =
  | "ready"
  | "running"
  | "interval"
  | "paused"
  | "complete"
  | "stopped"
  | "fault";


type ExecutionEnvelope = {
  ok?: boolean;
  result?: PraxisIteration;
  error?: string;
  detail?: string;
};


const CAPABILITY =
  "exile:urge:praxis-step";

const MAX_ITERATIONS = 250;

const MAX_IMAGE_BYTES =
  20 * 1024 * 1024;


function record(
  value: unknown,
): UnknownRecord | null {
  if (
    value !== null
    && typeof value === "object"
    && !Array.isArray(value)
  ) {
    return value as UnknownRecord;
  }

  return null;
}


function text(
  value: unknown,
): string | null {
  if (
    typeof value === "string"
    && value.trim()
  ) {
    return value.trim();
  }

  return null;
}


function errorText(
  value: unknown,
): string {
  if (value instanceof Error) {
    return value.message;
  }

  if (typeof value === "string") {
    return value;
  }

  return "praxis execution failed";
}


function lines(
  value: string,
): string[] {
  const seen =
    new Set<string>();

  return value
    .split(/\r?\n/)
    .map(
      (item) =>
        item.trim(),
    )
    .filter(
      (item) => {
        if (
          !item
          || seen.has(item)
        ) {
          return false;
        }

        seen.add(item);
        return true;
      },
    );
}


function readImage(
  file: File,
): Promise<string> {
  return new Promise(
    (
      resolve,
      reject,
    ) => {
      const reader =
        new FileReader();

      reader.onerror =
        () => reject(
          new Error(
            "baseline image could not be read",
          ),
        );

      reader.onload =
        () => {
          if (
            typeof reader.result
            !== "string"
          ) {
            reject(
              new Error(
                "baseline image could not be encoded",
              ),
            );
            return;
          }

          resolve(
            reader.result,
          );
        };

      reader.readAsDataURL(
        file,
      );
    },
  );
}


function findImage(
  value: unknown,
  depth = 0,
): string | null {
  if (
    value === null
    || value === undefined
    || depth > 8
  ) {
    return null;
  }

  const direct =
    text(value);

  if (direct) {
    if (
      direct.startsWith(
        "data:image/",
      )
      || direct.startsWith(
        "blob:",
      )
      || direct.startsWith(
        "http://",
      )
      || direct.startsWith(
        "https://",
      )
    ) {
      return direct;
    }

    return null;
  }

  if (Array.isArray(value)) {
    for (
      const item of value
    ) {
      const found =
        findImage(
          item,
          depth + 1,
        );

      if (found) {
        return found;
      }
    }

    return null;
  }

  const source =
    record(value);

  if (!source) {
    return null;
  }

  const preferred = [
    "image",
    "image_url",
    "imageUrl",
    "preview",
    "preview_url",
    "previewUrl",
    "render",
    "render_url",
    "renderUrl",
    "artifact",
    "artifact_url",
    "artifactUrl",
    "output",
    "result",
    "source",
    "url",
    "uri",
    "data_url",
    "dataUrl",
  ];

  for (
    const key of preferred
  ) {
    if (key in source) {
      const found =
        findImage(
          source[key],
          depth + 1,
        );

      if (found) {
        return found;
      }
    }
  }

  for (
    const nested
    of Object.values(source)
  ) {
    const found =
      findImage(
        nested,
        depth + 1,
      );

    if (found) {
      return found;
    }
  }

  return null;
}


function findDirection(
  iteration:
    PraxisIteration | null,
): string {
  if (!iteration) {
    return "";
  }

  const sources = [
    iteration.logo,
    iteration.creative,
    iteration.workbench,
  ];

  const keys = [
    "concept",
    "concept_name",
    "title",
    "name",
    "direction",
    "summary",
    "rationale",
    "description",
    "mechanism",
  ];

  for (
    const candidate of sources
  ) {
    const source =
      record(candidate);

    if (!source) {
      continue;
    }

    for (
      const key of keys
    ) {
      const found =
        text(source[key]);

      if (found) {
        return found;
      }
    }
  }

  return (
    `iteration ${iteration.index}`
  );
}


function previousProjection(
  iteration: PraxisIteration,
): UnknownRecord {
  return {
    index:
      iteration.index,
    digest:
      iteration.digest,
    workbench: {
      digest:
        record(
          iteration.workbench,
        )?.digest,
    },
  };
}


function sleep(
  milliseconds: number,
  signal: AbortSignal,
): Promise<void> {
  return new Promise(
    (
      resolve,
      reject,
    ) => {
      if (
        milliseconds <= 0
      ) {
        resolve();
        return;
      }

      const timer =
        window.setTimeout(
          resolve,
          milliseconds,
        );

      signal.addEventListener(
        "abort",
        () => {
          window.clearTimeout(
            timer,
          );

          reject(
            new DOMException(
              "praxis stopped",
              "AbortError",
            ),
          );
        },
        {
          once: true,
        },
      );
    },
  );
}


async function dispatchStep(
  payload: UnknownRecord,
  signal: AbortSignal,
): Promise<PraxisIteration> {
  const response =
    await fetch(
      "/api/execution/dispatch",
      {
        method: "POST",
        headers: {
          Accept:
            "application/json",
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify({
          capability:
            CAPABILITY,
          payload,
        }),
        signal,
      },
    );

  let envelope:
    ExecutionEnvelope;

  try {
    envelope =
      await response.json();
  } catch {
    throw new Error(
      "execution bridge returned invalid json",
    );
  }

  if (
    !response.ok
    || envelope.ok === false
  ) {
    throw new Error(
      envelope.detail
      || envelope.error
      || (
        "execution failed with status "
        + response.status
      ),
    );
  }

  if (!envelope.result) {
    throw new Error(
      "execution returned no praxis result",
    );
  }

  return envelope.result;
}


export function UrgeWorkbench({
  config,
}: {
  config: UrgeConfig;
}) {
  const [
    logoName,
    setLogoName,
  ] = useState(
    config.name || "savant",
  );

  const [
    objective,
    setObjective,
  ] = useState(
    "Create a distinctive logo identity whose intelligence comes from a proprietary visual mechanism rather than fashionable styling.",
  );

  const [
    iterations,
    setIterations,
  ] = useState(8);

  const [
    intervalSeconds,
    setIntervalSeconds,
  ] = useState(2);

  const [
    constraints,
    setConstraints,
  ] = useState(
    "remain legible at small scale\nwork in monochrome",
  );

  const [
    invariants,
    setInvariants,
  ] = useState("");

  const [
    cliches,
    setCliches,
  ] = useState(
    "generic neural network\nsparkle icon\ngeneric infinity symbol",
  );

  const [
    baseline,
    setBaseline,
  ] = useState<
    Baseline | null
  >(null);

  const [
    baselinePreview,
    setBaselinePreview,
  ] = useState<
    string | null
  >(null);

  const [
    results,
    setResults,
  ] = useState<
    PraxisIteration[]
  >([]);

  const [
    selected,
    setSelected,
  ] = useState(0);

  const [
    state,
    setState,
  ] = useState<PraxisState>(
    "ready",
  );

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    remainingMs,
    setRemainingMs,
  ] = useState(0);

  const abortRef =
    useRef<
      AbortController | null
    >(null);

  const pauseRef =
    useRef(false);

  const countdownRef =
    useRef<
      number | null
    >(null);

  const running =
    state === "running"
    || state === "interval"
    || state === "paused";

  const selectedResult =
    results[selected]
    ?? (
      results.length
        ? results[
            results.length - 1
          ]
        : null
    );

  const latest =
    results.length
      ? results[
          results.length - 1
        ]
      : null;

  const resultImage =
    findImage(
      selectedResult,
    );

  const previewImage =
    resultImage
    || (
      results.length === 0
        ? baselinePreview
        : null
    );

  const boundedIterations =
    Math.min(
      MAX_ITERATIONS,
      Math.max(
        1,
        Math.trunc(
          iterations || 1,
        ),
      ),
    );

  const intervalMs =
    Math.max(
      0,
      Math.round(
        intervalSeconds
        * 1000,
      ),
    );

  const progress =
    Math.min(
      100,
      (
        results.length
        / boundedIterations
      ) * 100,
    );

  const canRun =
    !running
    && Boolean(
      logoName.trim()
      && objective.trim(),
    );

  const stateLabel =
    useMemo(
      () => {
        if (
          state === "interval"
        ) {
          return (
            remainingMs > 0
              ? (
                "next iteration in "
                + (
                  remainingMs
                  / 1000
                ).toFixed(1)
                + "s"
              )
              : "next iteration"
          );
        }

        if (
          state === "running"
        ) {
          return (
            "generating iteration "
            + Math.min(
              results.length + 1,
              boundedIterations,
            )
          );
        }

        return state;
      },
      [
        state,
        remainingMs,
        results.length,
        boundedIterations,
      ],
    );

  useEffect(
    () => {
      return () => {
        abortRef.current
          ?.abort();

        if (
          countdownRef.current
          !== null
        ) {
          window.clearInterval(
            countdownRef.current,
          );
        }
      };
    },
    [],
  );

  async function
  selectBaseline(
    event:
      ChangeEvent<
        HTMLInputElement
      >,
  ) {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    setError(null);

    if (
      !file.type.startsWith(
        "image/",
      )
    ) {
      setError(
        "baseline must be an image",
      );
      return;
    }

    if (
      file.size
      > MAX_IMAGE_BYTES
    ) {
      setError(
        "baseline image must be 20 MB or smaller",
      );
      return;
    }

    try {
      const source =
        await readImage(file);

      setBaseline({
        kind: "image",
        name: file.name,
        media_type:
          file.type
          || "image/*",
        source,
      });

      setBaselinePreview(
        source,
      );
    } catch (
      cause
    ) {
      setError(
        errorText(cause),
      );
    }
  }


  async function
  waitForInterval(
    milliseconds: number,
    controller:
      AbortController,
  ) {
    if (
      milliseconds <= 0
    ) {
      return;
    }

    setState("interval");
    setRemainingMs(
      milliseconds,
    );

    let remaining =
      milliseconds;

    let previous =
      performance.now();

    countdownRef.current =
      window.setInterval(
        () => {
          const now =
            performance.now();

          if (!pauseRef.current) {
            remaining =
              Math.max(
                0,
                remaining
                - (
                  now
                  - previous
                ),
              );

            setRemainingMs(
              remaining,
            );
          }

          previous = now;
        },
        100,
      );

    try {
      while (
        remaining > 0
      ) {
        if (
          controller.signal
            .aborted
        ) {
          throw new DOMException(
            "praxis stopped",
            "AbortError",
          );
        }

        if (
          pauseRef.current
        ) {
          setState("paused");

          await sleep(
            100,
            controller.signal,
          );

          previous =
            performance.now();

          continue;
        }

        setState("interval");

        const slice =
          Math.min(
            100,
            remaining,
          );

        await sleep(
          slice,
          controller.signal,
        );
      }
    } finally {
      if (
        countdownRef.current
        !== null
      ) {
        window.clearInterval(
          countdownRef.current,
        );

        countdownRef.current =
          null;
      }

      setRemainingMs(0);
    }
  }


  async function runPraxis() {
    if (!canRun) {
      return;
    }

    const controller =
      new AbortController();

    abortRef.current =
      controller;

    pauseRef.current =
      false;

    setResults([]);
    setSelected(0);
    setError(null);
    setRemainingMs(0);
    setState("running");

    const parameters = {
      objective:
        objective.trim(),
      name:
        logoName.trim(),
      iterations:
        boundedIterations,
      interval_ms:
        intervalMs,
      baseline,
      constraints:
        lines(
          constraints,
        ),
      invariants:
        lines(
          invariants,
        ),
      cliches:
        lines(
          cliches,
        ),
      context: {
        surface:
          "splyce",
        interface:
          "urge-workbench",
        instance:
          config.exile_id,
        mode:
          "logo",
      },
      creative_policy: {},
    };

    let previous:
      PraxisIteration | null =
        null;

    try {
      for (
        let index = 1;
        index
          <= boundedIterations;
        index += 1
      ) {
        if (
          controller.signal
            .aborted
        ) {
          throw new DOMException(
            "praxis stopped",
            "AbortError",
          );
        }

        while (
          pauseRef.current
        ) {
          setState("paused");

          await sleep(
            100,
            controller.signal,
          );
        }

        setState("running");

        const payload:
          UnknownRecord = {
            parameters,
            index,
          };

        if (previous) {
          payload.previous =
            previousProjection(
              previous,
            );
        }

        const result =
          await dispatchStep(
            payload,
            controller.signal,
          );

        previous = result;

        setResults(
          (current) => {
            const next = [
              ...current,
              result,
            ];

            setSelected(
              next.length - 1,
            );

            return next;
          },
        );

        if (
          index
          < boundedIterations
        ) {
          await waitForInterval(
            intervalMs,
            controller,
          );
        }
      }

      setState("complete");
    } catch (
      cause
    ) {
      if (
        cause
        instanceof DOMException
        && cause.name
          === "AbortError"
      ) {
        setState("stopped");
      } else {
        setError(
          errorText(cause),
        );
        setState("fault");
      }
    } finally {
      abortRef.current =
        null;

      pauseRef.current =
        false;

      setRemainingMs(0);
    }
  }


  function stopPraxis() {
    abortRef.current
      ?.abort();

    pauseRef.current =
      false;

    setState("stopped");
  }


  function togglePause() {
    if (!running) {
      return;
    }

    pauseRef.current =
      !pauseRef.current;

    setState(
      pauseRef.current
        ? "paused"
        : (
            remainingMs > 0
              ? "interval"
              : "running"
          ),
    );
  }


  function resetPraxis() {
    if (running) {
      return;
    }

    setResults([]);
    setSelected(0);
    setError(null);
    setRemainingMs(0);
    setState("ready");
  }


  return (
    <section
      className="urge-praxis"
      aria-label="Urge logo praxis"
    >
      <header className="urge-praxis-hero">
        <div>
          <span className="urge-praxis-kicker">
            <Sparkles size={13} />
            urge / praxis
          </span>

          <h1>
            evolve
            <em>the mark</em>
          </h1>

          <p>
            Define the identity,
            seed it with an existing
            image or begin from zero,
            then watch every iteration
            arrive live.
          </p>
        </div>

        <div
          className="urge-praxis-state"
          data-state={state}
        >
          <i />

          <div>
            <small>
              praxis state
            </small>

            <strong>
              {stateLabel}
            </strong>
          </div>
        </div>
      </header>

      <div className="urge-praxis-shell">
        <aside className="urge-praxis-controls">
          <section>
            <div className="urge-praxis-section-title">
              <span>01</span>
              <div>
                <strong>
                  identity
                </strong>
                <small>
                  tell urge what
                  should exist
                </small>
              </div>
            </div>

            <label>
              <span>
                name
              </span>

              <input
                value={logoName}
                disabled={running}
                onChange={
                  (event) =>
                    setLogoName(
                      event.target
                        .value,
                    )
                }
                placeholder="savant"
              />
            </label>

            <label>
              <span>
                objective
              </span>

              <textarea
                value={objective}
                disabled={running}
                rows={5}
                onChange={
                  (event) =>
                    setObjective(
                      event.target
                        .value,
                    )
                }
              />
            </label>
          </section>

          <section>
            <div className="urge-praxis-section-title">
              <span>02</span>
              <div>
                <strong>
                  origin
                </strong>
                <small>
                  image baseline
                  or clean slate
                </small>
              </div>
            </div>

            <div
              className="urge-praxis-baseline"
              data-loaded={
                Boolean(baseline)
              }
            >
              {baselinePreview ? (
                <img
                  src={
                    baselinePreview
                  }
                  alt="Praxis baseline"
                />
              ) : (
                <div className="urge-praxis-scratch">
                  <ImagePlus
                    size={25}
                  />

                  <strong>
                    start from
                    scratch
                  </strong>

                  <small>
                    no inherited
                    visual form
                  </small>
                </div>
              )}

              <div>
                <label className="urge-praxis-upload">
                  <Upload size={13} />

                  {baseline
                    ? "replace"
                    : "add baseline"}

                  <input
                    type="file"
                    accept="image/*"
                    disabled={running}
                    onChange={
                      selectBaseline
                    }
                  />
                </label>

                {baseline ? (
                  <button
                    type="button"
                    disabled={running}
                    onClick={() => {
                      setBaseline(
                        null,
                      );
                      setBaselinePreview(
                        null,
                      );
                    }}
                  >
                    <X size={13} />
                    scratch
                  </button>
                ) : null}
              </div>
            </div>
          </section>

          <section>
            <div className="urge-praxis-section-title">
              <span>03</span>
              <div>
                <strong>
                  cadence
                </strong>
                <small>
                  how far and
                  how fast
                </small>
              </div>
            </div>

            <div className="urge-praxis-pair">
              <label>
                <span>
                  iterations
                </span>

                <input
                  type="number"
                  min={1}
                  max={
                    MAX_ITERATIONS
                  }
                  disabled={running}
                  value={iterations}
                  onChange={
                    (event) =>
                      setIterations(
                        Number(
                          event.target
                            .value,
                        ),
                      )
                  }
                />
              </label>

              <label>
                <span>
                  interval / sec
                </span>

                <input
                  type="number"
                  min={0}
                  step={0.25}
                  disabled={running}
                  value={
                    intervalSeconds
                  }
                  onChange={
                    (event) =>
                      setIntervalSeconds(
                        Math.max(
                          0,
                          Number(
                            event.target
                              .value,
                          ),
                        ),
                      )
                  }
                />
              </label>
            </div>

            <div className="urge-praxis-cadence">
              <strong>
                {boundedIterations}
              </strong>
              <span>
                iterations
              </span>
              <i />
              <strong>
                {intervalSeconds}
              </strong>
              <span>
                seconds apart
              </span>
            </div>
          </section>

          <details className="urge-praxis-advanced">
            <summary>
              creative boundaries
            </summary>

            <label>
              <span>
                constraints
              </span>

              <textarea
                rows={3}
                disabled={running}
                value={constraints}
                onChange={
                  (event) =>
                    setConstraints(
                      event.target
                        .value,
                    )
                }
              />
            </label>

            <label>
              <span>
                invariants
              </span>

              <textarea
                rows={3}
                disabled={running}
                value={invariants}
                placeholder="one protected property per line"
                onChange={
                  (event) =>
                    setInvariants(
                      event.target
                        .value,
                    )
                }
              />
            </label>

            <label>
              <span>
                reject clichés
              </span>

              <textarea
                rows={3}
                disabled={running}
                value={cliches}
                onChange={
                  (event) =>
                    setCliches(
                      event.target
                        .value,
                    )
                }
              />
            </label>
          </details>

          {error ? (
            <div
              className="urge-praxis-error"
              role="alert"
            >
              <AlertTriangle
                size={14}
              />

              <span>
                {error}
              </span>
            </div>
          ) : null}

          <div className="urge-praxis-actions">
            {!running ? (
              <button
                type="button"
                className="urge-praxis-run"
                disabled={!canRun}
                onClick={() => {
                  void runPraxis();
                }}
              >
                <Play size={15} />

                <span>
                  run praxis
                </span>

                <small>
                  {boundedIterations}
                  ×
                </small>
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="urge-praxis-pause"
                  onClick={
                    togglePause
                  }
                >
                  {state
                  === "paused" ? (
                    <Play size={14} />
                  ) : (
                    <Pause size={14} />
                  )}

                  {state
                  === "paused"
                    ? "resume"
                    : "pause"}
                </button>

                <button
                  type="button"
                  className="urge-praxis-stop"
                  onClick={
                    stopPraxis
                  }
                >
                  <Square size={13} />
                  stop
                </button>
              </>
            )}

            {!running
            && results.length > 0 ? (
              <button
                type="button"
                className="urge-praxis-reset"
                onClick={
                  resetPraxis
                }
              >
                <RotateCcw
                  size={13}
                />
                reset
              </button>
            ) : null}
          </div>
        </aside>

        <main className="urge-praxis-preview">
          <header>
            <div>
              <small>
                live projection
              </small>

              <strong>
                {selectedResult
                  ? (
                    "iteration "
                    + selectedResult
                      .index
                  )
                  : "waiting for praxis"}
              </strong>
            </div>

            <div className="urge-praxis-count">
              <b>
                {results.length}
              </b>
              <span>
                /
                {boundedIterations}
              </span>
            </div>
          </header>

          <div className="urge-praxis-progress">
            <span
              style={{
                width:
                  `${progress}%`,
              }}
            />
          </div>

          <div
            className="urge-praxis-canvas"
            data-image={
              Boolean(
                previewImage,
              )
            }
          >
            {previewImage ? (
              <img
                src={previewImage}
                alt={
                  selectedResult
                    ? (
                      "Logo iteration "
                      + selectedResult
                        .index
                    )
                    : "Logo baseline"
                }
              />
            ) : (
              <div className="urge-praxis-empty">
                <span>
                  ur
                </span>

                <strong>
                  {running
                    ? "building the next form"
                    : "live iterations appear here"}
                </strong>

                <p>
                  Every completed
                  iteration is preserved
                  below so you can move
                  backward through the
                  entire praxis without
                  losing the newest result.
                </p>
              </div>
            )}

            {state
            === "running" ? (
              <div className="urge-praxis-working">
                <LoaderCircle
                  size={17}
                />
                opus + urge
              </div>
            ) : null}
          </div>

          <div className="urge-praxis-direction">
            <span>
              current direction
            </span>

            <strong>
              {findDirection(
                selectedResult,
              )
              || (
                baseline
                  ? "baseline"
                  : "uncommitted"
              )}
            </strong>
          </div>

          <div className="urge-praxis-timeline">
            {results.length ? (
              results.map(
                (
                  result,
                  index,
                ) => {
                  const image =
                    findImage(
                      result,
                    );

                  return (
                    <button
                      type="button"
                      key={
                        result.digest
                        || result.index
                      }
                      data-active={
                        selected
                        === index
                      }
                      onClick={() =>
                        setSelected(
                          index,
                        )
                      }
                    >
                      <div>
                        {image ? (
                          <img
                            src={image}
                            alt=""
                          />
                        ) : (
                          <span>
                            {
                              result
                                .index
                            }
                          </span>
                        )}

                        {result.complete ? (
                          <i>
                            <Check
                              size={10}
                            />
                          </i>
                        ) : null}
                      </div>

                      <small>
                        iteration
                      </small>

                      <strong>
                        {
                          result
                            .index
                        }
                      </strong>
                    </button>
                  );
                },
              )
            ) : (
              <div className="urge-praxis-no-history">
                praxis history
                will accumulate here
              </div>
            )}
          </div>

          {latest ? (
            <footer className="urge-praxis-evidence">
              <span>
                lineage
              </span>

              <strong>
                {latest.digest
                  ? latest.digest.slice(
                      0,
                      14,
                    )
                  : "projected"}
              </strong>

              <span>
                provider owner
              </span>

              <strong>
                opus
              </strong>

              <span>
                iteration owner
              </span>

              <strong>
                urge
              </strong>
            </footer>
          ) : null}
        </main>
      </div>
    </section>
  );
}
