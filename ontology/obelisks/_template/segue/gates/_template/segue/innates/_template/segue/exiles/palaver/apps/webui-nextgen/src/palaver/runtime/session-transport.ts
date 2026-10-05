const schema =
  "savant.palaver.session-transport.v1"

const sessionStorageKey =
  "savant.palaver.server-session.v1"

const apiBase = (
  import.meta.env.VITE_PALAVER_API_BASE ||
  ""
).replace(/\/+$/, "")

const sessionHeader =
  "X-Palaver-Session-ID"

const requestHeader =
  "X-Palaver-Request-ID"

const maximumStoredEvents = 250

type JsonObject = Record<
  string,
  unknown
>

type SessionState = {
  schema: typeof schema
  sessionId: string | null
  latestSequence: number
  updatedAt: number
}

type SessionOpenResponse = {
  session_id?: unknown
  recovery?: {
    latest_sequence?: unknown
  }
}

type SessionRecoverResponse = {
  session_id?: unknown
  latest_sequence?: unknown
  recovery?: {
    latest_sequence?: unknown
  }
  events?: unknown
}

type SessionEvent = {
  sequence?: unknown
  request_id?: unknown
  event_type?: unknown
  payload?: unknown
}

type SessionRuntimeEvent = {
  schema: typeof schema
  sessionId: string
  event: SessionEvent
}

const originalFetch =
  globalThis.fetch.bind(
    globalThis,
  )

let installed = false

let opening:
  Promise<string | null> |
  null = null

let polling = false

let stopped = false

let activeSessionId:
  string | null = null

let latestSequence = 0

const activeRequests =
  new Map<
    string,
    AbortSignal | null
  >()

function finiteInteger(
  value: unknown,
): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    Number.isInteger(value) &&
    value >= 0
  )
}

function nonEmptyString(
  value: unknown,
): value is string {
  return (
    typeof value === "string" &&
    value.trim().length > 0
  )
}

function requestId() {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID ===
      "function"
  ) {
    return (
      "palreq_" +
      crypto
        .randomUUID()
        .replace(
          /-/g,
          "",
        )
    )
  }

  const random = Math.random()
    .toString(16)
    .slice(2)

  return (
    "palreq_" +
    Date.now()
      .toString(16) +
    random.padEnd(
      16,
      "0",
    ).slice(
      0,
      16,
    )
  )
}

function readState():
  SessionState {
  try {
    const raw =
      localStorage.getItem(
        sessionStorageKey,
      )

    if (!raw) {
      return {
        schema,
        sessionId: null,
        latestSequence: 0,
        updatedAt: 0,
      }
    }

    const parsed =
      JSON.parse(
        raw,
      ) as Partial<
        SessionState
      >

    if (
      parsed.schema !== schema
    ) {
      return {
        schema,
        sessionId: null,
        latestSequence: 0,
        updatedAt: 0,
      }
    }

    return {
      schema,
      sessionId:
        nonEmptyString(
          parsed.sessionId,
        )
          ? parsed.sessionId
          : null,
      latestSequence:
        finiteInteger(
          parsed.latestSequence,
        )
          ? parsed.latestSequence
          : 0,
      updatedAt:
        finiteInteger(
          parsed.updatedAt,
        )
          ? parsed.updatedAt
          : 0,
    }
  } catch {
    return {
      schema,
      sessionId: null,
      latestSequence: 0,
      updatedAt: 0,
    }
  }
}

function persistState() {
  try {
    localStorage.setItem(
      sessionStorageKey,
      JSON.stringify({
        schema,
        sessionId:
          activeSessionId,
        latestSequence,
        updatedAt:
          Date.now(),
      } satisfies SessionState),
    )
  } catch {
    /*
     * Browser state is only a
     * disposable projection of the
     * server-owned Palaver session.
     */
  }
}

function apiUrl(
  path: string,
) {
  return `${apiBase}${path}`
}

function normalizeUrl(
  input:
    RequestInfo | URL,
) {
  if (
    input instanceof URL
  ) {
    return input
  }

  if (
    typeof input === "string"
  ) {
    try {
      return new URL(
        input,
        window.location.href,
      )
    } catch {
      return null
    }
  }

  try {
    return new URL(
      input.url,
      window.location.href,
    )
  } catch {
    return null
  }
}

function isPalaverChat(
  input:
    RequestInfo | URL,
) {
  const url =
    normalizeUrl(input)

  return (
    url?.pathname ===
      "/api/chat"
  )
}

function dispatchSessionEvent(
  sessionId: string,
  event: SessionEvent,
) {
  window.dispatchEvent(
    new CustomEvent<
      SessionRuntimeEvent
    >(
      "palaver:session-event",
      {
        detail: {
          schema,
          sessionId,
          event,
        },
      },
    ),
  )
}

function updateSequence(
  event: SessionEvent,
) {
  if (
    finiteInteger(
      event.sequence,
    ) &&
    event.sequence >
      latestSequence
  ) {
    latestSequence =
      event.sequence

    persistState()
  }
}

function normalizeEvents(
  value: unknown,
): SessionEvent[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .filter(
      (
        candidate,
      ): candidate is SessionEvent =>
        Boolean(
          candidate &&
          typeof candidate ===
            "object",
        ),
    )
    .slice(
      -maximumStoredEvents,
    )
}

async function readJson(
  response: Response,
): Promise<
  JsonObject | null
> {
  try {
    const value =
      await response.json()

    if (
      !value ||
      typeof value !==
        "object" ||
      Array.isArray(value)
    ) {
      return null
    }

    return value as JsonObject
  } catch {
    return null
  }
}

async function openSession():
  Promise<
    string | null
  > {
  if (
    activeSessionId
  ) {
    return activeSessionId
  }

  if (opening) {
    return opening
  }

  opening = (
    async () => {
      const state =
        readState()

      const body =
        state.sessionId
          ? {
              session_id:
                state.sessionId,
            }
          : {}

      try {
        const response =
          await originalFetch(
            apiUrl(
              "/api/session/open",
            ),
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body:
                JSON.stringify(
                  body,
                ),
              cache:
                "no-store",
            },
          )

        if (!response.ok) {
          if (
            state.sessionId
          ) {
            const fresh =
              await originalFetch(
                apiUrl(
                  "/api/session/open",
                ),
                {
                  method:
                    "POST",
                  headers: {
                    "Content-Type":
                      "application/json",
                  },
                  body:
                    "{}",
                  cache:
                    "no-store",
                },
              )

            if (!fresh.ok) {
              return null
            }

            const freshData =
              await readJson(
                fresh,
              ) as
                | SessionOpenResponse
                | null

            if (
              !freshData ||
              !nonEmptyString(
                freshData.session_id,
              )
            ) {
              return null
            }

            activeSessionId =
              freshData.session_id

            latestSequence = 0

            persistState()

            return (
              activeSessionId
            )
          }

          return null
        }

        const data =
          await readJson(
            response,
          ) as
            | SessionOpenResponse
            | null

        if (
          !data ||
          !nonEmptyString(
            data.session_id,
          )
        ) {
          return null
        }

        activeSessionId =
          data.session_id

        const recovered =
          data.recovery
            ?.latest_sequence

        if (
          finiteInteger(
            recovered,
          )
        ) {
          latestSequence =
            Math.max(
              state.latestSequence,
              recovered,
            )
        } else {
          latestSequence =
            state.latestSequence
        }

        persistState()

        return (
          activeSessionId
        )
      } catch {
        return null
      }
    }
  )()

  try {
    return await opening
  } finally {
    opening = null
  }
}

async function recoverSession() {
  const sessionId =
    await openSession()

  if (!sessionId) {
    return
  }

  try {
    const response =
      await originalFetch(
        apiUrl(
          "/api/session/recover" +
          `?session_id=${encodeURIComponent(
            sessionId,
          )}`,
        ),
        {
          cache:
            "no-store",
        },
      )

    if (!response.ok) {
      return
    }

    const data =
      await readJson(
        response,
      ) as
        | SessionRecoverResponse
        | null

    if (!data) {
      return
    }

    const events =
      normalizeEvents(
        data.events,
      )

    for (
      const event of events
    ) {
      updateSequence(
        event,
      )

      dispatchSessionEvent(
        sessionId,
        event,
      )
    }

    const recoveredLatest =
      data.latest_sequence ??
      data.recovery
        ?.latest_sequence

    if (
      finiteInteger(
        recoveredLatest,
      ) &&
      recoveredLatest >
        latestSequence
    ) {
      latestSequence =
        recoveredLatest

      persistState()
    }

    window.dispatchEvent(
      new CustomEvent(
        "palaver:session-recovered",
        {
          detail: {
            schema,
            sessionId,
            latestSequence,
          },
        },
      ),
    )
  } catch {
    /*
     * Recovery is opportunistic.
     * Local conversation projection
     * remains usable offline.
     */
  }
}

async function pollEvents() {
  if (
    polling ||
    stopped
  ) {
    return
  }

  polling = true

  try {
    while (!stopped) {
      const sessionId =
        await openSession()

      if (!sessionId) {
        await new Promise(
          (resolve) =>
            window.setTimeout(
              resolve,
              2000,
            ),
        )

        continue
      }

      try {
        const query =
          new URLSearchParams({
            session_id:
              sessionId,
            after:
              String(
                latestSequence,
              ),
            wait:
              "20",
            limit:
              "100",
          })

        const response =
          await originalFetch(
            apiUrl(
              "/api/session/events" +
              `?${query.toString()}`,
            ),
            {
              cache:
                "no-store",
            },
          )

        if (!response.ok) {
          await new Promise(
            (resolve) =>
              window.setTimeout(
                resolve,
                1500,
              ),
          )

          continue
        }

        const data =
          await readJson(
            response,
          )

        const events =
          normalizeEvents(
            data?.events,
          )

        for (
          const event of events
        ) {
          updateSequence(
            event,
          )

          dispatchSessionEvent(
            sessionId,
            event,
          )
        }
      } catch {
        await new Promise(
          (resolve) =>
            window.setTimeout(
              resolve,
              1500,
            ),
        )
      }
    }
  } finally {
    polling = false
  }
}

async function cancelRequest(
  sessionId: string,
  request: string,
) {
  try {
    await originalFetch(
      apiUrl(
        "/api/session/cancel",
      ),
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body:
          JSON.stringify({
            session_id:
              sessionId,
            request_id:
              request,
            reason:
              "client_abort",
          }),
        cache:
          "no-store",
        keepalive:
          true,
      },
    )
  } catch {
    /*
     * The browser AbortController
     * remains the immediate local
     * cancellation mechanism.
     */
  }
}

function mergeHeaders(
  input:
    RequestInfo | URL,
  init:
    RequestInit | undefined,
  additions:
    Record<
      string,
      string
    >,
) {
  const headers =
    new Headers(
      input instanceof Request
        ? input.headers
        : undefined,
    )

  if (init?.headers) {
    const supplied =
      new Headers(
        init.headers,
      )

    supplied.forEach(
      (value, key) => {
        headers.set(
          key,
          value,
        )
      },
    )
  }

  for (
    const [
      key,
      value,
    ] of Object.entries(
      additions,
    )
  ) {
    headers.set(
      key,
      value,
    )
  }

  return headers
}

async function palaverFetch(
  input:
    RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  if (
    !isPalaverChat(
      input,
    )
  ) {
    return originalFetch(
      input,
      init,
    )
  }

  const sessionId =
    await openSession()

  if (!sessionId) {
    return originalFetch(
      input,
      init,
    )
  }

  const request =
    requestId()

  const signal =
    init?.signal ??
    (
      input instanceof Request
        ? input.signal
        : null
    )

  const headers =
    mergeHeaders(
      input,
      init,
      {
        [sessionHeader]:
          sessionId,
        [requestHeader]:
          request,
      },
    )

  activeRequests.set(
    request,
    signal,
  )

  let aborted = false

  const onAbort = () => {
    if (aborted) {
      return
    }

    aborted = true

    void cancelRequest(
      sessionId,
      request,
    )
  }

  if (signal) {
    if (signal.aborted) {
      onAbort()
    } else {
      signal.addEventListener(
        "abort",
        onAbort,
        {
          once: true,
        },
      )
    }
  }

  try {
    const response =
      await originalFetch(
        input,
        {
          ...init,
          headers,
        },
      )

    const responseSession =
      response.headers.get(
        sessionHeader,
      )

    const responseRequest =
      response.headers.get(
        requestHeader,
      )

    if (
      responseSession &&
      responseSession !==
        activeSessionId
    ) {
      activeSessionId =
        responseSession

      persistState()
    }

    window.dispatchEvent(
      new CustomEvent(
        "palaver:request-completed",
        {
          detail: {
            schema,
            sessionId:
              responseSession ??
              sessionId,
            requestId:
              responseRequest ??
              request,
            status:
              response.status,
          },
        },
      ),
    )

    return response
  } finally {
    activeRequests.delete(
      request,
    )

    signal?.removeEventListener(
      "abort",
      onAbort,
    )
  }
}

export function installPalaverSessionTransport() {
  if (installed) {
    return
  }

  installed = true
  stopped = false

  const state =
    readState()

  activeSessionId =
    state.sessionId

  latestSequence =
    state.latestSequence

  globalThis.fetch =
    palaverFetch

  void recoverSession()
  void pollEvents()

  window.addEventListener(
    "online",
    recoverSession,
  )

  window.addEventListener(
    "pagehide",
    () => {
      persistState()
    },
  )
}

export function palaverSessionProjection() {
  return {
    schema,
    sessionId:
      activeSessionId,
    latestSequence,
    activeRequestCount:
      activeRequests.size,
    persistentServerSession:
      true,
    browserStorageAuthoritative:
      false,
    conversationOwner:
      "palaver",
    authorityEffect:
      "none",
  }
}
