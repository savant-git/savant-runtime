import {
  ChangeEvent,
  FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import "./urge-praxis.css";


type JsonObject = Record<
  string,
  unknown
>;

type Baseline = {
  kind: "image";
  name: string;
  media_type: string;
  source: string;
  digest?: string;
};

type PraxisParameters = {
  objective: string;
  name: string;
  iterations: number;
  interval_ms: number;
  baseline: Baseline | null;
  constraints: string[];
  invariants: string[];
  cliches: string[];
  context: JsonObject;
  creative_policy: JsonObject;
};

type PraxisIteration = {
  schema?: string;
  owner?: string;
  capability?: string;
  index: number;
  iterations: number;
  complete?: boolean;
  digest?: string;
  creative?: JsonObject;
  logo?: JsonObject;
  renderer?: JsonObject;
  workbench?: JsonObject;
  lineage?: JsonObject;
};

type PraxisStatus =
  | "idle"
  | "running"
  | "waiting"
  | "complete"
  | "stopped"
  | "error";

type BridgeEnvelope = {
  ok?: boolean;
  result?: unknown;
  error?: unknown;
  detail?: unknown;
};


const PRAXIS_CAPABILITY =
  "exile:urge:praxis-step";

const DEFAULT_ITERATIONS = 8;
const DEFAULT_INTERVAL_MS = 1500;

const MIN_ITERATIONS = 1;
const MAX_ITERATIONS = 250;

const MAX_IMAGE_BYTES =
  20 * 1024 * 1024;


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
              "Praxis stopped",
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


function errorText(
  value: unknown,
): string {
  if (
    value
    instanceof Error
  ) {
    return value.message;
  }

  if (
    typeof value
    === "string"
  ) {
    return value;
  }

  if (
    value
    && typeof value
      === "object"
  ) {
    try {
      return JSON.stringify(
        value,
      );
    } catch {
      return (
        "Unknown praxis error"
      );
    }
  }

  return "Unknown praxis error";
}


function unwrapResult(
  value: unknown,
): PraxisIteration {
  if (
    !value
    || typeof value
      !== "object"
  ) {
    throw new Error(
      "Savant returned an invalid "
      + "praxis response.",
    );
  }

  const envelope =
    value as BridgeEnvelope;

  if (
    envelope.ok === false
  ) {
    throw new Error(
      errorText(
        envelope.error
        ?? envelope.detail
        ?? "Praxis execution failed.",
      ),
    );
  }

  const candidate =
    envelope.result
    ?? value;

  if (
    !candidate
    || typeof candidate
      !== "object"
  ) {
    throw new Error(
      "Praxis result is missing.",
    );
  }

  const iteration =
    candidate
    as PraxisIteration;

  if (
    !Number.isInteger(
      iteration.index,
    )
  ) {
    throw new Error(
      "Praxis iteration index "
      + "is missing.",
    );
  }

  return iteration;
}


function firstString(
  value: unknown,
): string | null {
  if (
    typeof value
      === "string"
    && value.trim()
  ) {
    return value.trim();
  }

  return null;
}


function findImage(
  value: unknown,
  depth = 0,
): string | null {
  if (
    depth > 7
    || value === null
    || value === undefined
  ) {
    return null;
  }

  const direct =
    firstString(value);

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

  if (
    Array.isArray(value)
  ) {
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

  if (
    typeof value
      !== "object"
  ) {
    return null;
  }

  const object =
    value as JsonObject;

  const preferredKeys = [
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
    const key
    of preferredKeys
  ) {
    if (
      key in object
    ) {
      const found =
        findImage(
          object[key],
          depth + 1,
        );

      if (found) {
        return found;
      }
    }
  }

  for (
    const nested
    of Object.values(
      object,
    )
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


function findConcept(
  iteration:
    PraxisIteration | null,
): string {
  if (!iteration) {
    return "";
  }

  const candidates: unknown[] = [
    iteration.logo,
    iteration.creative,
    iteration.workbench,
  ];

  const keys = [
    "concept",
    "concept_name",
    "name",
    "title",
    "summary",
    "rationale",
    "direction",
    "description",
  ];

  for (
    const candidate
    of candidates
  ) {
    if (
      !candidate
      || typeof candidate
        !== "object"
    ) {
      continue;
    }

    const object =
      candidate
      as JsonObject;

    for (
      const key
      of keys
    ) {
      const text =
        firstString(
          object[key],
        );

      if (text) {
        return text;
      }
    }
  }

  return (
    "Iteration "
    + iteration.index
  );
}


function readFile(
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
        () => {
          reject(
            new Error(
              "Could not read "
              + "baseline image.",
            ),
          );
        };

      reader.onload =
        () => {
          if (
            typeof reader.result
              !== "string"
          ) {
            reject(
              new Error(
                "Baseline image "
                + "could not be "
                + "encoded.",
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


async function dispatch(
  capability: string,
  payload: JsonObject,
  signal: AbortSignal,
): Promise<PraxisIteration> {
  const response =
    await fetch(
      "/api/execute",
      {
        method: "POST",
        headers: {
          "content-type":
            "application/json",
        },
        body: JSON.stringify({
          capability,
          payload,
        }),
        signal,
      },
    );

  const text =
    await response.text();

  let decoded:
    unknown = null;

  if (text) {
    try {
      decoded =
        JSON.parse(text);
    } catch {
      decoded = text;
    }
  }

  if (!response.ok) {
    throw new Error(
      "Savant execution bridge "
      + "returned "
      + response.status
      + ": "
      + errorText(decoded),
    );
  }

  return unwrapResult(
    decoded,
  );
}


function formatInterval(
  milliseconds: number,
): string {
  if (
    milliseconds < 1000
  ) {
    return (
      milliseconds
      + " ms"
    );
  }

  if (
    milliseconds
      % 60000
      === 0
  ) {
    return (
      milliseconds
      / 60000
      + " min"
    );
  }

  return (
    milliseconds
    / 1000
  ).toLocaleString(
    undefined,
    {
      maximumFractionDigits:
        2,
    },
  ) + " sec";
}


export default function UrgePraxis() {
  const [
    name,
    setName,
  ] = useState("");

  const [
    objective,
    setObjective,
  ] = useState("");

  const [
    iterations,
    setIterations,
  ] = useState(
    DEFAULT_ITERATIONS,
  );

  const [
    intervalMs,
    setIntervalMs,
  ] = useState(
    DEFAULT_INTERVAL_MS,
  );

  const [
    constraints,
    setConstraints,
  ] = useState("");

  const [
    invariants,
    setInvariants,
  ] = useState("");

  const [
    cliches,
    setCliches,
  ] = useState("");

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
    status,
    setStatus,
  ] = useState<PraxisStatus>(
    "idle",
  );

  const [
    results,
    setResults,
  ] = useState<
    PraxisIteration[]
  >([]);

  const [
    selectedIndex,
    setSelectedIndex,
  ] = useState(0);

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    countdown,
    setCountdown,
  ] = useState<
    number | null
  >(null);

  const abortRef =
    useRef<
      AbortController | null
    >(null);

  const countdownRef =
    useRef<
      number | null
    >(null);

  const running =
    status === "running"
    || status === "waiting";

  const selected =
    results[
      selectedIndex
    ] ?? null;

  const latest =
    results.length
      ? results[
          results.length - 1
        ]
      : null;

  const previewSource =
    findImage(
      selected
      ?? latest,
    )
    ?? (
      results.length === 0
        ? baselinePreview
        : null
    );

  const progress =
    iterations > 0
      ? Math.min(
          100,
          (
            results.length
            / iterations
          ) * 100,
        )
      : 0;

  const canRun =
    Boolean(
      name.trim()
      && objective.trim(),
    )
    && !running;

  const statusLabel =
    useMemo(
      () => {
        switch (status) {
          case "running":
            return "iterating";
          case "waiting":
            return (
              countdown === null
                ? "interval"
                : "next in "
                  + Math.ceil(
                    countdown
                    / 1000,
                  )
                  + "s"
            );
          case "complete":
            return "complete";
          case "stopped":
            return "stopped";
          case "error":
            return "fault";
          default:
            return "ready";
        }
      },
      [
        status,
        countdown,
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
  onBaselineChange(
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
        "Baseline must be "
        + "an image.",
      );
      event.target.value = "";
      return;
    }

    if (
      file.size
      > MAX_IMAGE_BYTES
    ) {
      setError(
        "Baseline image exceeds "
        + "20 MB.",
      );
      event.target.value = "";
      return;
    }

    try {
      const source =
        await readFile(file);

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
      value
    ) {
      setError(
        errorText(value),
      );
    }
  }

  function clearBaseline() {
    if (running) {
      return;
    }

    setBaseline(null);
    setBaselinePreview(null);
  }

  function stopPraxis() {
    abortRef.current
      ?.abort();

    abortRef.current =
      null;

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

    setCountdown(null);
    setStatus("stopped");
  }

  async function waitInterval(
    milliseconds: number,
    controller:
      AbortController,
  ) {
    if (
      milliseconds <= 0
    ) {
      return;
    }

    setStatus("waiting");
    setCountdown(
      milliseconds,
    );

    const started =
      performance.now();

    countdownRef.current =
      window.setInterval(
        () => {
          const elapsed =
            performance.now()
            - started;

          setCountdown(
            Math.max(
              0,
              milliseconds
              - elapsed,
            ),
          );
        },
        100,
      );

    try {
      await sleep(
        milliseconds,
        controller.signal,
      );
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

      setCountdown(null);
    }
  }

  async function runPraxis(
    event:
      FormEvent<
        HTMLFormElement
      >,
  ) {
    event.preventDefault();

    if (!canRun) {
      return;
    }

    const boundedIterations =
      Math.min(
        MAX_ITERATIONS,
        Math.max(
          MIN_ITERATIONS,
          Math.trunc(
            iterations,
          ),
        ),
      );

    const boundedInterval =
      Math.max(
        0,
        Math.trunc(
          intervalMs,
        ),
      );

    const parameters:
      PraxisParameters = {
        objective:
          objective.trim(),
        name:
          name.trim(),
        iterations:
          boundedIterations,
        interval_ms:
          boundedInterval,
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
            "urge-praxis",
          mode:
            "logo",
        },
        creative_policy: {},
      };

    const controller =
      new AbortController();

    abortRef.current =
      controller;

    setResults([]);
    setSelectedIndex(0);
    setError(null);
    setCountdown(null);
    setStatus("running");

    let previous:
      PraxisIteration
      | null = null;

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
            "Praxis stopped",
            "AbortError",
          );
        }

        setStatus("running");

        const payload:
          JsonObject = {
            parameters,
            index,
          };

        if (previous) {
          payload.previous = {
            index:
              previous.index,
            digest:
              previous.digest,
            workbench: {
              digest:
                previous
                  .workbench
                  ?.digest,
            },
          };
        }

        const result =
          await dispatch(
            PRAXIS_CAPABILITY,
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

            setSelectedIndex(
              next.length - 1,
            );

            return next;
          },
        );

        if (
          index
          < boundedIterations
        ) {
          await waitInterval(
            boundedInterval,
            controller,
          );
        }
      }

      setStatus("complete");
    } catch (
      value
    ) {
      if (
        value
        instanceof DOMException
        && value.name
          === "AbortError"
      ) {
        setStatus("stopped");
      } else {
        setError(
          errorText(value),
        );
        setStatus("error");
      }
    } finally {
      abortRef.current =
        null;

      setCountdown(null);
    }
  }

  return (
    <main
      className="urge-praxis"
    >
      <header
        className=
          "urge-praxis__masthead"
      >
        <div>
          <p
            className=
              "urge-praxis__eyebrow"
          >
            urge / logo praxis
          </p>

          <h1>
            Iterate with intent.
          </h1>

          <p
            className=
              "urge-praxis__lede"
          >
            Start from an image
            or empty space. Set
            the pressure, cadence,
            and finish line. Urge
            evolves the identity
            one visible iteration
            at a time.
          </p>
        </div>

        <div
          className={
            "urge-praxis__state "
            + "urge-praxis__state--"
            + status
          }
        >
          <span
            aria-hidden="true"
            className=
              "urge-praxis__pulse"
          />

          {statusLabel}
        </div>
      </header>

      <section
        className=
          "urge-praxis__layout"
      >
        <form
          className=
            "urge-praxis__controls"
          onSubmit={runPraxis}
        >
          <div
            className=
              "urge-praxis__section-head"
          >
            <span>01</span>
            <div>
              <strong>
                define
              </strong>
              <small>
                What are we
                evolving?
              </small>
            </div>
          </div>

          <label
            className=
              "urge-praxis__field"
          >
            <span>
              identity name
            </span>

            <input
              disabled={running}
              onChange={
                (event) =>
                  setName(
                    event.target
                      .value,
                  )
              }
              placeholder="savant"
              type="text"
              value={name}
            />
          </label>

          <label
            className=
              "urge-praxis__field"
          >
            <span>
              creative objective
            </span>

            <textarea
              disabled={running}
              onChange={
                (event) =>
                  setObjective(
                    event.target
                      .value,
                  )
              }
              placeholder={
                "Describe what the "
                + "logo should become, "
                + "what it should mean, "
                + "and what it must not "
                + "feel like."
              }
              rows={6}
              value={objective}
            />
          </label>

          <div
            className=
              "urge-praxis__section-head"
          >
            <span>02</span>
            <div>
              <strong>
                seed
              </strong>
              <small>
                Begin from scratch
                or provide a visual
                baseline.
              </small>
            </div>
          </div>

          <div
            className={
              "urge-praxis__baseline "
              + (
                baseline
                  ? "is-loaded"
                  : ""
              )
            }
          >
            {baselinePreview ? (
              <img
                alt={
                  "Praxis baseline "
                  + baseline?.name
                }
                src={
                  baselinePreview
                }
              />
            ) : (
              <div
                className=
                  "urge-praxis__scratch"
              >
                <span>
                  ∅
                </span>
                <strong>
                  start from
                  scratch
                </strong>
                <small>
                  no inherited
                  visual decisions
                </small>
              </div>
            )}

            <div
              className=
                "urge-praxis__baseline-actions"
            >
              <label
                className=
                  "urge-praxis__upload"
              >
                <input
                  accept="image/*"
                  disabled={running}
                  onChange={
                    onBaselineChange
                  }
                  type="file"
                />

                {baseline
                  ? "replace image"
                  : "add baseline"}
              </label>

              {baseline && (
                <button
                  disabled={running}
                  onClick={
                    clearBaseline
                  }
                  type="button"
                >
                  start from scratch
                </button>
              )}
            </div>
          </div>

          <div
            className=
              "urge-praxis__section-head"
          >
            <span>03</span>
            <div>
              <strong>
                cadence
              </strong>
              <small>
                Choose the length
                and breathing room.
              </small>
            </div>
          </div>

          <div
            className=
              "urge-praxis__pair"
          >
            <label
              className=
                "urge-praxis__field"
            >
              <span>
                iterations
              </span>

              <input
                disabled={running}
                max={
                  MAX_ITERATIONS
                }
                min={
                  MIN_ITERATIONS
                }
                onChange={
                  (event) =>
                    setIterations(
                      Number(
                        event.target
                          .value,
                      ),
                    )
                }
                type="number"
                value={iterations}
              />
            </label>

            <label
              className=
                "urge-praxis__field"
            >
              <span>
                interval
              </span>

              <div
                className=
                  "urge-praxis__unit-input"
              >
                <input
                  disabled={running}
                  min={0}
                  onChange={
                    (event) =>
                      setIntervalMs(
                        Math.round(
                          Number(
                            event
                              .target
                              .value,
                          )
                          * 1000,
                        ),
                      )
                  }
                  step="0.25"
                  type="number"
                  value={
                    intervalMs
                    / 1000
                  }
                />
                <em>
                  sec
                </em>
              </div>
            </label>
          </div>

          <div
            className=
              "urge-praxis__summary"
          >
            <span>
              {iterations}
              {" "}
              iterations
            </span>
            <i />
            <span>
              {formatInterval(
                intervalMs,
              )}
              {" "}
              apart
            </span>
            <i />
            <span>
              {baseline
                ? "baseline seeded"
                : "scratch seeded"}
            </span>
          </div>

          <details
            className=
              "urge-praxis__advanced"
          >
            <summary>
              creative boundaries
            </summary>

            <label
              className=
                "urge-praxis__field"
            >
              <span>
                constraints
              </span>
              <textarea
                disabled={running}
                onChange={
                  (event) =>
                    setConstraints(
                      event.target
                        .value,
                    )
                }
                placeholder={
                  "One constraint "
                  + "per line"
                }
                rows={3}
                value={constraints}
              />
            </label>

            <label
              className=
                "urge-praxis__field"
            >
              <span>
                protected
                invariants
              </span>
              <textarea
                disabled={running}
                onChange={
                  (event) =>
                    setInvariants(
                      event.target
                        .value,
                    )
                }
                placeholder={
                  "What must survive "
                  + "every iteration?"
                }
                rows={3}
                value={invariants}
              />
            </label>

            <label
              className=
                "urge-praxis__field"
            >
              <span>
                clichés to reject
              </span>
              <textarea
                disabled={running}
                onChange={
                  (event) =>
                    setCliches(
                      event.target
                        .value,
                    )
                }
                placeholder={
                  "Generic ideas "
                  + "Urge should avoid"
                }
                rows={3}
                value={cliches}
              />
            </label>
          </details>

          {error && (
            <div
              className=
                "urge-praxis__error"
              role="alert"
            >
              <strong>
                praxis fault
              </strong>
              <span>
                {error}
              </span>
            </div>
          )}

          <div
            className=
              "urge-praxis__runbar"
          >
            {!running ? (
              <button
                className=
                  "urge-praxis__run"
                disabled={!canRun}
                type="submit"
              >
                <span>
                  run praxis
                </span>
                <small>
                  {iterations}
                  {" "}
                  iterations
                </small>
              </button>
            ) : (
              <button
                className=
                  "urge-praxis__stop"
                onClick={
                  stopPraxis
                }
                type="button"
              >
                stop praxis
              </button>
            )}
          </div>
        </form>

        <section
          className=
            "urge-praxis__stage"
        >
          <div
            className=
              "urge-praxis__stage-head"
          >
            <div>
              <span>
                live projection
              </span>

              <strong>
                {selected
                  ? (
                    "iteration "
                    + selected.index
                  )
                  : "waiting"}
              </strong>
            </div>

            <div
              className=
                "urge-praxis__counter"
            >
              <b>
                {results.length}
              </b>
              <span>
                /
                {iterations}
              </span>
            </div>
          </div>

          <div
            className=
              "urge-praxis__progress"
            aria-label={
              "Praxis progress "
              + Math.round(
                progress,
              )
              + "%"
            }
          >
            <span
              style={{
                width:
                  progress
                  + "%",
              }}
            />
          </div>

          <div
            className={
              "urge-praxis__canvas "
              + (
                previewSource
                  ? "has-image"
                  : ""
              )
            }
          >
            {previewSource ? (
              <img
                alt={
                  selected
                    ? (
                      "Logo iteration "
                      + selected.index
                    )
                    : "Logo baseline"
                }
                src={
                  previewSource
                }
              />
            ) : (
              <div
                className=
                  "urge-praxis__empty"
              >
                <div
                  className=
                    "urge-praxis__mark"
                >
                  ur
                </div>

                <strong>
                  {running
                    ? "thinking through the next form"
                    : "your iterations will appear here"}
                </strong>

                <p>
                  Each completed
                  iteration becomes
                  selectable below
                  the moment Savant
                  returns it.
                </p>
              </div>
            )}

            {running && (
              <div
                className=
                  "urge-praxis__working"
              >
                <span />
                <span />
                <span />
              </div>
            )}
          </div>

          <div
            className=
              "urge-praxis__concept"
          >
            <span>
              current direction
            </span>

            <strong>
              {findConcept(
                selected
                ?? latest,
              )
              || (
                baseline
                  ? "baseline"
                  : "uncommitted"
              )}
            </strong>
          </div>

          <div
            className=
              "urge-praxis__timeline"
          >
            {results.length === 0 ? (
              <div
                className=
                  "urge-praxis__timeline-empty"
              >
                No iterations yet.
              </div>
            ) : (
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
                      className={
                        "urge-praxis__iteration "
                        + (
                          selectedIndex
                          === index
                            ? "is-selected"
                            : ""
                        )
                      }
                      key={
                        result.digest
                        ?? result.index
                      }
                      onClick={
                        () =>
                          setSelectedIndex(
                            index,
                          )
                      }
                      type="button"
                    >
                      <div>
                        {image ? (
                          <img
                            alt=""
                            src={
                              image
                            }
                          />
                        ) : (
                          <span>
                            {
                              result
                                .index
                            }
                          </span>
                        )}
                      </div>

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
            )}
          </div>

          {selected && (
            <details
              className=
                "urge-praxis__evidence"
            >
              <summary>
                iteration evidence
              </summary>

              <pre>
                {JSON.stringify(
                  {
                    index:
                      selected.index,
                    digest:
                      selected.digest,
                    lineage:
                      selected.lineage,
                    renderer:
                      selected.renderer,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          )}
        </section>
      </section>
    </main>
  );
}
