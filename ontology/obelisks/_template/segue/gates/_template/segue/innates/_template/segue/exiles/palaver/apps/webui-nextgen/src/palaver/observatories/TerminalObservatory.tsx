import {
  useCallback,
  useEffect,
  useRef,
  useState
} from "react"

import {
  Terminal as XTerm
} from "@xterm/xterm"

import {
  FitAddon
} from "@xterm/addon-fit"

import {
  SearchAddon
} from "@xterm/addon-search"

import {
  WebLinksAddon
} from "@xterm/addon-web-links"

import {
  Maximize2,
  MessageSquareText,
  Minimize2,
  Plus,
  RefreshCw,
  Search,
  Square,
  TerminalSquare
} from "lucide-react"

import {
  useWorkspaceStore
} from "../state/workspace-store"


type ApiPayload = {
  ok?: boolean
  error?: string
  [key: string]: any
}


async function decodeResponse(
  response: Response
): Promise<ApiPayload> {
  const text =
    await response.text()

  if (!text.trim()) {
    return {
      ok: response.ok
    }
  }

  try {
    const value =
      JSON.parse(
        text
      )

    if (
      value
      && typeof value
      === "object"
    ) {
      return value
    }

    return {
      ok: response.ok,
      value
    }
  } catch {
    return {
      ok: response.ok,
      error: text.trim()
    }
  }
}


async function api(
  path: string,
  options: RequestInit = {}
) {
  let response: Response

  try {
    response =
      await fetch(
        path,
        {
          cache: "no-store",
          ...options
        }
      )
  } catch (
    reason
  ) {
    throw new Error(
      reason instanceof Error
        ? reason.message
        : String(reason)
    )
  }

  const payload =
    await decodeResponse(
      response
    )

  if (
    !response.ok
    || payload.ok === false
  ) {
    throw new Error(
      payload.error
      || (
        `terminal request failed: `
        + response.status
      )
    )
  }

  return payload
}


export default function TerminalObservatory() {
  const {
    terminalStage,
    clearTerminalStage,
    setActive,
    setComposerDraft,
    setLastActivity
  } = useWorkspaceStore()

  const mountRef =
    useRef<HTMLDivElement | null>(
      null
    )

  const terminalRef =
    useRef<XTerm | null>(
      null
    )

  const fitRef =
    useRef<FitAddon | null>(
      null
    )

  const searchRef =
    useRef<SearchAddon | null>(
      null
    )

  const sessionRef =
    useRef("")

  const cursorRef =
    useRef(0)

  const pollTimerRef =
    useRef<number | null>(
      null
    )

  const inputTimerRef =
    useRef<number | null>(
      null
    )

  const inputBufferRef =
    useRef("")

  const [
    status,
    setStatus
  ] = useState(
    "connecting"
  )

  const [
    cwd,
    setCwd
  ] = useState(
    "/root/savant-runtime"
  )

  const [
    pid,
    setPid
  ] = useState<
    number | null
  >(null)

  const [
    search,
    setSearch
  ] = useState("")

  const [
    fullscreen,
    setFullscreen
  ] = useState(false)


  const flushInput =
    useCallback(
      async () => {
        inputTimerRef.current =
          null

        const data =
          inputBufferRef.current

        inputBufferRef.current =
          ""

        const id =
          sessionRef.current

        if (
          !id
          || !data
        ) {
          return
        }

        try {
          await api(
            "/api/terminal/input",
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({
                  id,
                  data
                })
            }
          )
        } catch {
          setStatus(
            "disconnected"
          )
        }
      },
      []
    )


  const queueInput =
    useCallback(
      (
        data: string
      ) => {
        inputBufferRef.current +=
          data

        if (
          inputTimerRef.current
          !== null
        ) {
          return
        }

        inputTimerRef.current =
          window.setTimeout(
            flushInput,
            12
          )
      },
      [
        flushInput
      ]
    )


  const resizeRemote =
    useCallback(
      async () => {
        const terminal =
          terminalRef.current

        const fit =
          fitRef.current

        const id =
          sessionRef.current

        if (
          !terminal
          || !fit
        ) {
          return
        }

        try {
          fit.fit()
        } catch {
          return
        }

        if (!id) {
          return
        }

        try {
          await api(
            "/api/terminal/resize",
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({
                  id,

                  cols:
                    terminal.cols,

                  rows:
                    terminal.rows
                })
            }
          )
        } catch {
          setStatus(
            "disconnected"
          )
        }
      },
      []
    )


  const poll =
    useCallback(
      async () => {
        const id =
          sessionRef.current

        if (!id) {
          return
        }

        try {
          const payload =
            await api(
              (
                "/api/terminal/read"
                + `?id=${encodeURIComponent(id)}`
                + `&cursor=${cursorRef.current}`
              )
            )

          for (
            const chunk
            of payload.chunks
            || []
          ) {
            terminalRef.current
              ?.write(
                chunk.data
              )
          }

          cursorRef.current =
            payload.cursor
            || cursorRef.current

          if (
            typeof payload.cwd
            === "string"
          ) {
            setCwd(
              payload.cwd
            )
          }

          if (
            payload.closed
          ) {
            setStatus(
              payload.exit_code
              === null
                ? "closed"
                : (
                  `exited `
                  + payload.exit_code
                )
            )

            return
          }

          setStatus(
            "connected"
          )

          pollTimerRef.current =
            window.setTimeout(
              poll,
              70
            )
        } catch {
          setStatus(
            "disconnected"
          )

          pollTimerRef.current =
            window.setTimeout(
              poll,
              1000
            )
        }
      },
      []
    )


  const closeSession =
    useCallback(
      async () => {
        const id =
          sessionRef.current

        sessionRef.current =
          ""

        if (
          pollTimerRef.current
          !== null
        ) {
          window.clearTimeout(
            pollTimerRef.current
          )

          pollTimerRef.current =
            null
        }

        if (!id) {
          return
        }

        try {
          await api(
            "/api/terminal/close",
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({
                  id
                })
            }
          )
        } catch {
          // Session may already be absent.
        }

        setPid(
          null
        )

        setStatus(
          "closed"
        )
      },
      []
    )


  const createSession =
    useCallback(
      async () => {
        await closeSession()

        const terminal =
          terminalRef.current

        if (!terminal) {
          return
        }

        terminal.reset()

        terminal.writeln(
          (
            "\x1b[2mconnecting to "
            + "palaver terminal…"
            + "\x1b[0m"
          )
        )

        setStatus(
          "connecting"
        )

        cursorRef.current =
          0

        try {
          const payload =
            await api(
              "/api/terminal/session",
              {
                method:
                  "POST",

                headers: {
                  "Content-Type":
                    "application/json"
                },

                body:
                  JSON.stringify({
                    cwd:
                      "/root/savant-runtime",

                    cols:
                      terminal.cols,

                    rows:
                      terminal.rows
                  })
              }
            )

          if (
            typeof payload.id
            !== "string"
            || !payload.id
          ) {
            throw new Error(
              (
                "terminal backend returned "
                + "no session id"
              )
            )
          }

          sessionRef.current =
            payload.id

          setPid(
            typeof payload.pid
            === "number"
              ? payload.pid
              : null
          )

          if (
            typeof payload.cwd
            === "string"
          ) {
            setCwd(
              payload.cwd
            )
          }

          setStatus(
            "connected"
          )

          setLastActivity(
            "terminal session opened"
          )

          await resizeRemote()

          poll()
        } catch (
          error
        ) {
          terminal.writeln(
            (
              "\r\n\x1b[31m"
              + "terminal connection failed: "
              + (
                error
                instanceof Error
                  ? error.message
                  : String(error)
              )
              + "\x1b[0m"
            )
          )

          setStatus(
            "disconnected"
          )
        }
      },
      [
        closeSession,
        poll,
        resizeRemote,
        setLastActivity
      ]
    )


  useEffect(
    () => {
      const mount =
        mountRef.current

      if (!mount) {
        return
      }

      const terminal =
        new XTerm({
          cursorBlink:
            true,

          convertEol:
            false,

          scrollback:
            10000,

          fontSize:
            13,

          lineHeight:
            1.18,

          fontFamily:
            (
              '"JetBrains Mono",'
              + '"SFMono-Regular",'
              + 'Consolas,'
              + '"Liberation Mono",'
              + 'monospace'
            ),

          theme: {
            background:
              "#050608",

            foreground:
              "#d9dde5",

            cursor:
              "#f0c879",

            cursorAccent:
              "#050608",

            selectionBackground:
              "#4e7da955"
          }
        })

      const fit =
        new FitAddon()

      const searchAddon =
        new SearchAddon()

      const links =
        new WebLinksAddon()

      terminal.loadAddon(
        fit
      )

      terminal.loadAddon(
        searchAddon
      )

      terminal.loadAddon(
        links
      )

      terminal.open(
        mount
      )

      terminalRef.current =
        terminal

      fitRef.current =
        fit

      searchRef.current =
        searchAddon

      fit.fit()

      const disposable =
        terminal.onData(
          queueInput
        )

      const observer =
        new ResizeObserver(
          () =>
            window
              .requestAnimationFrame(
                resizeRemote
              )
        )

      observer.observe(
        mount
      )

      createSession()

      return () => {
        observer.disconnect()

        disposable.dispose()

        if (
          pollTimerRef.current
          !== null
        ) {
          window.clearTimeout(
            pollTimerRef.current
          )
        }

        if (
          inputTimerRef.current
          !== null
        ) {
          window.clearTimeout(
            inputTimerRef.current
          )
        }

        closeSession()

        terminal.dispose()

        terminalRef.current =
          null

        fitRef.current =
          null

        searchRef.current =
          null
      }
    },
    [
      closeSession,
      createSession,
      queueInput,
      resizeRemote
    ]
  )


  useEffect(
    () => {
      if (
        !terminalStage
        || !sessionRef.current
      ) {
        return
      }

      const value =
        terminalStage.text
          .replace(
            /\r?\n/g,
            " "
          )

      queueInput(
        value
      )

      terminalRef.current
        ?.focus()

      clearTerminalStage()

      setLastActivity(
        (
          "command staged; "
          + "awaiting human execution"
        )
      )
    },
    [
      terminalStage,
      clearTerminalStage,
      queueInput,
      setLastActivity
    ]
  )


  function runSearch() {
    if (
      !search.trim()
    ) {
      return
    }

    searchRef.current
      ?.findNext(
        search,
        {
          caseSensitive:
            false,

          incremental:
            true
        }
      )
  }


  function askPalaver() {
    const value =
      terminalRef.current
        ?.getSelection()
        .trim()

    if (!value) {
      return
    }

    setComposerDraft(
      (
        "Analyze this terminal output "
        + "and tell me the minimum "
        + "next action:\n\n"
        + value
      )
    )

    setActive(
      "chat"
    )

    setLastActivity(
      "terminal output attached to chat"
    )
  }


  return (
    <section
      className={
        fullscreen
          ? (
            "terminal-observatory "
            + "terminal-fullscreen"
          )
          : "terminal-observatory"
      }
    >
      <header
        className="terminal-toolbar"
      >
        <div
          className="terminal-identity"
        >
          <TerminalSquare
            size={16}
          />

          <div>
            <strong>
              terminal
            </strong>

            <span>
              human command authority
            </span>
          </div>
        </div>

        <div
          className="terminal-session-meta"
        >
          <span
            className={
              (
                "terminal-status "
                + "terminal-status-"
                + status.split(" ")[0]
              )
            }
          >
            {status}
          </span>

          {pid !== null && (
            <span>
              pid {pid}
            </span>
          )}

          <span
            className="terminal-cwd"
            title={cwd}
          >
            {cwd}
          </span>
        </div>

        <div
          className="terminal-actions"
        >
          <div
            className="terminal-search"
          >
            <Search
              size={13}
            />

            <input
              value={search}
              onChange={
                event =>
                  setSearch(
                    event.target.value
                  )
              }
              onKeyDown={
                event => {
                  if (
                    event.key
                    === "Enter"
                  ) {
                    runSearch()
                  }
                }
              }
              placeholder="find"
              aria-label={
                "Search terminal output"
              }
            />
          </div>

          <button
            type="button"
            onClick={askPalaver}
            title={
              "Ask Palaver about selected output"
            }
          >
            <MessageSquareText
              size={15}
            />
          </button>

          <button
            type="button"
            onClick={runSearch}
            title="Find next"
          >
            <Search
              size={15}
            />
          </button>

          <button
            type="button"
            onClick={createSession}
            title="New terminal session"
          >
            <Plus
              size={15}
            />
          </button>

          <button
            type="button"
            onClick={
              () => {
                if (
                  status
                  === "disconnected"
                ) {
                  createSession()
                } else {
                  resizeRemote()
                }
              }
            }
            title="Reconnect or refit"
          >
            <RefreshCw
              size={15}
            />
          </button>

          <button
            type="button"
            onClick={closeSession}
            title="Close terminal session"
          >
            <Square
              size={14}
            />
          </button>

          <button
            type="button"
            onClick={
              () =>
                setFullscreen(
                  value =>
                    !value
                )
            }
            title={
              fullscreen
                ? "Exit fullscreen"
                : "Fullscreen terminal"
            }
          >
            {fullscreen
              ? (
                <Minimize2
                  size={15}
                />
              )
              : (
                <Maximize2
                  size={15}
                />
              )}
          </button>
        </div>
      </header>

      <div
        className="terminal-host"
        ref={mountRef}
      />

      <footer
        className="terminal-footer"
      >
        <span>
          command authority · human
        </span>

        <span>
          surface owner · palaver
        </span>

        <span>
          durable savant mutation · coda
        </span>
      </footer>
    </section>
  )
}
