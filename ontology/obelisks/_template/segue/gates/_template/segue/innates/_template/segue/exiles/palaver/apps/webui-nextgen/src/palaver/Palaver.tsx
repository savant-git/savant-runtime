import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  Activity,
  ArrowDown,
  Brain,
  ChevronRight,
  CircleStop,
  Command,
  FolderTree,
  GitBranch,
  LoaderCircle,
  MessageCircle,
  Mic,
  MicOff,
  Plus,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  X,
  Zap,
} from "lucide-react"
import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import PalaverBranches from "./PalaverBranches"
import PalaverConversationTools from "./PalaverConversationTools"
import PalaverFocusRail from "./PalaverFocusRail"
import PalaverLensView from "./PalaverLensView"
import PalaverMessage, {
  type PalaverMessageRecord,
} from "./PalaverMessage"
import { usePalaverConversation } from "./usePalaverConversation"
import { usePalaverVoice } from "./usePalaverVoice"

type LensId =
  | "runtime"
  | "files"
  | "graph"
  | "memory"
  | null

type LensDefinition = {
  id: Exclude<LensId, null>
  label: string
  eyebrow: string
  endpoint: string
  icon: typeof Activity
}

const apiBase = (
  import.meta.env.VITE_PALAVER_API_BASE || ""
).replace(/\/$/, "")

const draftKey =
  "savant.palaver.ui.draft.v5"

const historyKey =
  "savant.palaver.ui.prompt-history.v5"

const lenses: LensDefinition[] = [
  {
    id: "runtime",
    label: "Runtime",
    eyebrow: "what is alive",
    endpoint: "/api/runtime",
    icon: Activity,
  },
  {
    id: "files",
    label: "Files",
    eyebrow: "what exists",
    endpoint: "/api/repository/files",
    icon: FolderTree,
  },
  {
    id: "graph",
    label: "Graph",
    eyebrow: "what connects",
    endpoint: "/api/graph",
    icon: GitBranch,
  },
  {
    id: "memory",
    label: "Memory",
    eyebrow: "what persists",
    endpoint: "/api/memory/files",
    icon: Brain,
  },
]

const suggestions = [
  "What needs my attention?",
  "Show me what changed.",
  "Explain the current runtime.",
  "What should I work on next?",
]

function uid(prefix: string) {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return `${prefix}:${crypto.randomUUID()}`
  }

  return `${prefix}:${Date.now()}:${Math.random()
    .toString(36)
    .slice(2)}`
}

async function apiJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${apiBase}${path}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    },
  )

  if (!response.ok) {
    throw new Error(
      `${response.status} ${response.statusText}`.trim(),
    )
  }

  return response.json() as Promise<T>
}

function conversationText(
  messages: PalaverMessageRecord[],
) {
  return messages
    .map(
      (message) =>
        `${
          message.role === "user"
            ? "You"
            : "Palaver"
        }\n${message.body}`,
    )
    .join("\n\n")
}

export default function Palaver() {
  const reducedMotion = useReducedMotion()

  const {
    messages,
    setMessages,
    branches,
    activeBranchId,
    createBranch,
    selectBranch,
    clearCurrentPath,
    clearAll,
    exportConversation,
    importConversation,
  } = usePalaverConversation()

  const [draft, setDraft] = useState("")
  const [sending, setSending] = useState(false)
  const [online, setOnline] = useState(
    navigator.onLine,
  )
  const [healthy, setHealthy] =
    useState<boolean | null>(null)
  const [latency, setLatency] =
    useState<number | null>(null)

  const [toolsOpen, setToolsOpen] =
    useState(false)
  const [paletteOpen, setPaletteOpen] =
    useState(false)
  const [branchesOpen, setBranchesOpen] =
    useState(false)
  const [focusOpen, setFocusOpen] =
    useState(false)

  const [activeMessageId, setActiveMessageId] =
    useState<string | null>(null)

  const [lens, setLens] = useState<LensId>(null)
  const [lensData, setLensData] =
    useState<unknown>(null)
  const [lensLoading, setLensLoading] =
    useState(false)
  const [lensError, setLensError] =
    useState("")

  const [copied, setCopied] =
    useState<string | null>(null)
  const [showJump, setShowJump] =
    useState(false)

  const [history, setHistory] =
    useState<string[]>(() => {
      try {
        const raw =
          localStorage.getItem(historyKey)

        return raw
          ? JSON.parse(raw)
          : []
      } catch {
        return []
      }
    })

  const [historyIndex, setHistoryIndex] =
    useState(-1)

  const textareaRef =
    useRef<HTMLTextAreaElement>(null)

  const streamRef =
    useRef<HTMLDivElement>(null)

  const abortRef =
    useRef<AbortController | null>(null)

  const userScrolledRef =
    useRef(false)

  const activeLens = useMemo(
    () =>
      lenses.find(
        (candidate) =>
          candidate.id === lens,
      ) ?? null,
    [lens],
  )

  const focusComposer = useCallback(() => {
    requestAnimationFrame(() => {
      textareaRef.current?.focus()
    })
  }, [])

  const voice = usePalaverVoice(
    useCallback(
      (text: string) => {
        setDraft((current) =>
          current.trim()
            ? `${current.trim()} ${text}`
            : text,
        )

        focusComposer()
      },
      [focusComposer],
    ),
  )

  const scrollToLatest = useCallback(
    (
      behavior: ScrollBehavior = "smooth",
    ) => {
      const stream = streamRef.current

      if (!stream) {
        return
      }

      stream.scrollTo({
        top: stream.scrollHeight,
        behavior,
      })

      userScrolledRef.current = false
      setShowJump(false)

      if (messages.length) {
        setActiveMessageId(
          messages[messages.length - 1].id,
        )
      }
    },
    [messages],
  )

  const scrollToMessage = useCallback(
    (messageId: string) => {
      const element =
        document.querySelector(
          `[data-palaver-message-id="${CSS.escape(
            messageId,
          )}"]`,
        )

      if (!element) {
        return
      }

      element.scrollIntoView({
        behavior:
          reducedMotion
            ? "auto"
            : "smooth",
        block: "center",
      })

      setActiveMessageId(messageId)
    },
    [reducedMotion],
  )

  const moveMessageFocus = useCallback(
    (direction: -1 | 1) => {
      if (!messages.length) {
        return
      }

      const currentIndex =
        activeMessageId
          ? messages.findIndex(
              (message) =>
                message.id === activeMessageId,
            )
          : -1

      const fallback =
        direction > 0
          ? 0
          : messages.length - 1

      const nextIndex =
        currentIndex < 0
          ? fallback
          : Math.min(
              messages.length - 1,
              Math.max(
                0,
                currentIndex + direction,
              ),
            )

      scrollToMessage(
        messages[nextIndex].id,
      )
    },
    [
      activeMessageId,
      messages,
      scrollToMessage,
    ],
  )

  const checkHealth = useCallback(
    async () => {
      if (!navigator.onLine) {
        setOnline(false)
        setHealthy(false)
        setLatency(null)
        return
      }

      const started =
        performance.now()

      try {
        await apiJson("/api/health", {
          cache: "no-store",
        })

        setHealthy(true)

        setLatency(
          Math.round(
            performance.now() - started,
          ),
        )
      } catch {
        setHealthy(false)
        setLatency(null)
      }
    },
    [],
  )

  useEffect(() => {
    try {
      const saved =
        localStorage.getItem(draftKey)

      if (saved) {
        setDraft(saved)
      }
    } catch {
      /* disposable ui state */
    }

    checkHealth()

    const onFocus = () => {
      checkHealth()
    }

    const onVisibility = () => {
      if (
        document.visibilityState ===
        "visible"
      ) {
        checkHealth()
      }
    }

    window.addEventListener(
      "focus",
      onFocus,
    )

    document.addEventListener(
      "visibilitychange",
      onVisibility,
    )

    return () => {
      window.removeEventListener(
        "focus",
        onFocus,
      )

      document.removeEventListener(
        "visibilitychange",
        onVisibility,
      )
    }
  }, [checkHealth])

  useEffect(() => {
    try {
      localStorage.setItem(
        draftKey,
        draft,
      )
    } catch {
      /* disposable ui state */
    }
  }, [draft])

  useEffect(() => {
    try {
      localStorage.setItem(
        historyKey,
        JSON.stringify(
          history.slice(0, 40),
        ),
      )
    } catch {
      /* disposable ui state */
    }
  }, [history])

  useEffect(() => {
    const onOnline = () => {
      setOnline(true)
      checkHealth()
    }

    const onOffline = () => {
      setOnline(false)
      setHealthy(false)
      setLatency(null)
    }

    window.addEventListener(
      "online",
      onOnline,
    )

    window.addEventListener(
      "offline",
      onOffline,
    )

    return () => {
      window.removeEventListener(
        "online",
        onOnline,
      )

      window.removeEventListener(
        "offline",
        onOffline,
      )
    }
  }, [checkHealth])

  useEffect(() => {
    if (!messages.length) {
      setActiveMessageId(null)
      return
    }

    if (
      activeMessageId &&
      messages.some(
        (message) =>
          message.id === activeMessageId,
      )
    ) {
      return
    }

    setActiveMessageId(
      messages[messages.length - 1].id,
    )
  }, [
    activeMessageId,
    messages,
  ])

  useEffect(() => {
    if (
      messages.length &&
      !userScrolledRef.current
    ) {
      scrollToLatest(
        reducedMotion
          ? "auto"
          : "smooth",
      )
    }
  }, [
    messages,
    reducedMotion,
    scrollToLatest,
  ])

  useEffect(() => {
    const onPointerMove = (
      event: PointerEvent,
    ) => {
      document.documentElement.style.setProperty(
        "--palaver-x",
        `${event.clientX}px`,
      )

      document.documentElement.style.setProperty(
        "--palaver-y",
        `${event.clientY}px`,
      )
    }

    window.addEventListener(
      "pointermove",
      onPointerMove,
      {
        passive: true,
      },
    )

    return () => {
      window.removeEventListener(
        "pointermove",
        onPointerMove,
      )
    }
  }, [])

  useEffect(() => {
    const textarea =
      textareaRef.current

    if (!textarea) {
      return
    }

    textarea.style.height = "0px"

    textarea.style.height =
      `${Math.min(
        textarea.scrollHeight,
        220,
      )}px`
  }, [draft])

  const addHistory = useCallback(
    (value: string) => {
      setHistory((current) => [
        value,
        ...current.filter(
          (entry) =>
            entry !== value,
        ),
      ])

      setHistoryIndex(-1)
    },
    [],
  )

  const requestAssistant = useCallback(
    async (
      message: string,
      parentId: string | null,
    ) => {
      const controller =
        new AbortController()

      abortRef.current =
        controller

      const started =
        performance.now()

      try {
        const result =
          await apiJson<{
            answer?: string
            trace?: string
            error?: string
          }>(
            "/api/chat",
            {
              method: "POST",
              body:
                JSON.stringify({
                  message,
                }),
              signal:
                controller.signal,
            },
          )

        const response:
          PalaverMessageRecord =
          {
            id: uid("palaver"),
            role: "assistant",
            body:
              result.answer ||
              result.error ||
              "Palaver returned no answer.",
            trace: result.trace,
            parentId,
            createdAt:
              Date.now(),
          }

        setMessages(
          (current) => [
            ...current,
            response,
          ],
        )

        setActiveMessageId(
          response.id,
        )

        setLatency(
          Math.round(
            performance.now() - started,
          ),
        )

        setHealthy(true)
      } catch (caught) {
        const aborted =
          caught instanceof DOMException &&
          caught.name === "AbortError"

        const response:
          PalaverMessageRecord =
          {
            id: uid("palaver"),
            role: "assistant",
            body: aborted
              ? "Request stopped."
              : "Palaver could not reach the runtime. Your message remains visible here.",
            trace: aborted
              ? undefined
              : String(caught),
            parentId,
            createdAt:
              Date.now(),
          }

        setMessages(
          (current) => [
            ...current,
            response,
          ],
        )

        setActiveMessageId(
          response.id,
        )

        if (!aborted) {
          setHealthy(false)
        }
      } finally {
        abortRef.current = null
        setSending(false)
        focusComposer()
      }
    },
    [
      focusComposer,
      setMessages,
    ],
  )

  const sendMessage = useCallback(
    async (
      supplied?: string,
    ) => {
      const message = (
        supplied ?? draft
      ).trim()

      if (
        !message ||
        sending
      ) {
        return
      }

      voice.stop()

      const userMessage:
        PalaverMessageRecord =
        {
          id: uid("user"),
          role: "user",
          body: message,
          createdAt:
            Date.now(),
          parentId:
            messages.length
              ? messages[
                  messages.length - 1
                ].id
              : null,
        }

      setMessages(
        (current) => [
          ...current,
          userMessage,
        ],
      )

      setActiveMessageId(
        userMessage.id,
      )

      setDraft("")

      try {
        localStorage.removeItem(
          draftKey,
        )
      } catch {
        /* disposable ui state */
      }

      addHistory(message)

      setToolsOpen(false)
      setPaletteOpen(false)
      setFocusOpen(false)
      setSending(true)

      await requestAssistant(
        message,
        userMessage.id,
      )
    },
    [
      addHistory,
      draft,
      messages,
      requestAssistant,
      sending,
      setMessages,
      voice,
    ],
  )

  const retryAssistant =
    useCallback(
      async (
        assistant:
          PalaverMessageRecord,
      ) => {
        if (sending) {
          return
        }

        const index =
          messages.findIndex(
            (message) =>
              message.id ===
              assistant.id,
          )

        if (index < 1) {
          return
        }

        let source:
          PalaverMessageRecord | null =
          null

        for (
          let cursor = index - 1;
          cursor >= 0;
          cursor -= 1
        ) {
          if (
            messages[cursor].role ===
            "user"
          ) {
            source =
              messages[cursor]
            break
          }
        }

        if (!source) {
          return
        }

        setMessages(
          (current) =>
            current.filter(
              (message) =>
                message.id !==
                assistant.id,
            ),
        )

        setActiveMessageId(
          source.id,
        )

        setSending(true)

        await requestAssistant(
          source.body,
          source.id,
        )
      },
      [
        messages,
        requestAssistant,
        sending,
        setMessages,
      ],
    )

  const branchFromMessage =
    useCallback(
      (
        message:
          PalaverMessageRecord,
      ) => {
        const branchId =
          createBranch(message)

        if (!branchId) {
          return
        }

        setBranchesOpen(false)
        setFocusOpen(false)

        setDraft(
          message.role === "assistant"
            ? "Take this in a different direction: "
            : "",
        )

        focusComposer()
      },
      [
        createBranch,
        focusComposer,
      ],
    )

  const quoteMessage =
    useCallback(
      (
        message:
          PalaverMessageRecord,
      ) => {
        const quote =
          message.body
            .split("\n")
            .map(
              (line) =>
                `> ${line}`,
            )
            .join("\n")

        setDraft(
          (current) =>
            current.trim()
              ? `${current.trim()}\n\n${quote}\n\n`
              : `${quote}\n\n`,
        )

        focusComposer()
      },
      [focusComposer],
    )

  const openLens =
    useCallback(
      async (
        definition:
          LensDefinition,
      ) => {
        setLens(definition.id)
        setToolsOpen(false)
        setPaletteOpen(false)
        setFocusOpen(false)
        setLensLoading(true)
        setLensError("")
        setLensData(null)

        try {
          const data =
            await apiJson<unknown>(
              definition.endpoint,
              {
                cache: "no-store",
              },
            )

          setLensData(data)
        } catch (caught) {
          setLensError(
            caught instanceof Error
              ? caught.message
              : String(caught),
          )
        } finally {
          setLensLoading(false)
        }
      },
      [],
    )

  const copy = useCallback(
    async (
      id: string,
      text: string,
    ) => {
      await navigator.clipboard.writeText(
        text,
      )

      setCopied(id)

      window.setTimeout(
        () => {
          setCopied(
            (current) =>
              current === id
                ? null
                : current,
          )
        },
        1300,
      )
    },
    [],
  )

  const copyCurrentPath =
    useCallback(async () => {
      await navigator.clipboard.writeText(
        conversationText(
          messages,
        ),
      )
    }, [messages])

  const onComposerKeyDown = (
    event:
      KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault()
      sendMessage()
      return
    }

    if (
      !draft &&
      event.key === "ArrowUp" &&
      history.length
    ) {
      event.preventDefault()

      const next =
        Math.min(
          historyIndex + 1,
          history.length - 1,
        )

      setHistoryIndex(next)
      setDraft(history[next])
      return
    }

    if (
      event.key === "ArrowDown" &&
      historyIndex >= 0
    ) {
      event.preventDefault()

      const next =
        historyIndex - 1

      if (next < 0) {
        setHistoryIndex(-1)
        setDraft("")
      } else {
        setHistoryIndex(next)
        setDraft(history[next])
      }
    }
  }

  const onStreamScroll =
    useCallback(() => {
      const stream =
        streamRef.current

      if (!stream) {
        return
      }

      const distance =
        stream.scrollHeight -
        stream.scrollTop -
        stream.clientHeight

      userScrolledRef.current =
        distance > 120

      setShowJump(
        distance > 420,
      )
    }, [])

  useEffect(() => {
    const onKeyDown = (
      event:
        globalThis.KeyboardEvent,
    ) => {
      const modifier =
        event.metaKey ||
        event.ctrlKey

      if (
        modifier &&
        event.key.toLowerCase() ===
          "k"
      ) {
        event.preventDefault()
        setPaletteOpen(
          (current) =>
            !current,
        )
        return
      }

      if (
        modifier &&
        event.key.toLowerCase() ===
          "l"
      ) {
        event.preventDefault()
        focusComposer()
        return
      }

      if (
        modifier &&
        event.key.toLowerCase() ===
          "b"
      ) {
        event.preventDefault()
        setBranchesOpen(
          (current) =>
            !current,
        )
        return
      }

      if (
        modifier &&
        event.key.toLowerCase() ===
          "f"
      ) {
        event.preventDefault()
        setFocusOpen(
          (current) =>
            !current,
        )
        return
      }

      if (
        modifier &&
        event.key === "ArrowUp"
      ) {
        event.preventDefault()
        moveMessageFocus(-1)
        return
      }

      if (
        modifier &&
        event.key === "ArrowDown"
      ) {
        event.preventDefault()
        moveMessageFocus(1)
        return
      }

      if (
        event.key !== "Escape"
      ) {
        return
      }

      if (voice.listening) {
        voice.stop()
        return
      }

      if (paletteOpen) {
        setPaletteOpen(false)
        return
      }

      if (focusOpen) {
        setFocusOpen(false)
        return
      }

      if (branchesOpen) {
        setBranchesOpen(false)
        return
      }

      if (lens) {
        setLens(null)
        focusComposer()
        return
      }

      if (toolsOpen) {
        setToolsOpen(false)
      }
    }

    window.addEventListener(
      "keydown",
      onKeyDown,
    )

    return () => {
      window.removeEventListener(
        "keydown",
        onKeyDown,
      )
    }
  }, [
    branchesOpen,
    focusComposer,
    focusOpen,
    lens,
    moveMessageFocus,
    paletteOpen,
    toolsOpen,
    voice,
  ])

  const submit = (
    event: FormEvent,
  ) => {
    event.preventDefault()
    sendMessage()
  }

  return (
    <main
      className={[
        "palaver",
        sending
          ? "is-thinking"
          : "",
        lens
          ? "has-lens"
          : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div
        className="palaver-atmosphere"
        aria-hidden="true"
      >
        <div className="palaver-aura palaver-aura-a" />
        <div className="palaver-aura palaver-aura-b" />
        <div className="palaver-grid" />
        <div className="palaver-grain" />
      </div>

      <header className="palaver-head">
        <button
          type="button"
          className="palaver-mark"
          aria-label="Focus Palaver"
          onClick={focusComposer}
        >
          <span>P</span>
        </button>

        <div className="palaver-identity">
          <strong>palaver</strong>

          <span>
            {activeBranchId
              ? "alternate path"
              : "talk to savant"}
          </span>
        </div>

        <div className="palaver-head-actions">
          <button
            type="button"
            className="icon-action"
            aria-label="Open message navigator"
            onClick={() =>
              setFocusOpen(true)
            }
          >
            <Search size={17} />
            <span className="keycap">
              ⌘F
            </span>
          </button>

          <button
            type="button"
            className="icon-action"
            aria-label="Open conversation paths"
            onClick={() =>
              setBranchesOpen(true)
            }
          >
            <GitBranch size={17} />

            <span className="keycap">
              {branches.length}
            </span>
          </button>

          <button
            type="button"
            className="palaver-health"
            onClick={checkHealth}
          >
            <span
              className={[
                "health-dot",
                !online
                  ? "offline"
                  : healthy === true
                    ? "good"
                    : healthy === false
                      ? "bad"
                      : "",
              ]
                .filter(Boolean)
                .join(" ")}
            />

            <span className="health-copy">
              {!online
                ? "offline"
                : healthy === true
                  ? "ready"
                  : healthy === false
                    ? "unreachable"
                    : "checking"}

              {latency !== null &&
                ` · ${latency}ms`}
            </span>
          </button>

          <button
            type="button"
            className="icon-action"
            aria-label="Open command palette"
            onClick={() =>
              setPaletteOpen(true)
            }
          >
            <Command size={18} />
            <span className="keycap">
              ⌘K
            </span>
          </button>
        </div>
      </header>

      <section className="palaver-stage">
        <div
          ref={streamRef}
          className={[
            "conversation",
            messages.length
              ? ""
              : "conversation-empty",
          ]
            .filter(Boolean)
            .join(" ")}
          onScroll={onStreamScroll}
          aria-live="polite"
        >
          {!messages.length && (
            <motion.div
              className="arrival"
              initial={
                reducedMotion
                  ? false
                  : {
                      opacity: 0,
                      y: 18,
                    }
              }
              animate={{
                opacity: 1,
                y: 0,
              }}
            >
              <span className="arrival-kicker">
                palaver
              </span>

              <h1>
                What are we
                <br />
                doing?
              </h1>

              <p>
                Ask plainly. Palaver
                handles the machinery.
              </p>

              <div className="arrival-prompts">
                {suggestions.map(
                  (suggestion) => (
                    <button
                      type="button"
                      key={suggestion}
                      onClick={() =>
                        sendMessage(
                          suggestion,
                        )
                      }
                    >
                      <span>
                        {suggestion}
                      </span>

                      <ChevronRight
                        size={16}
                      />
                    </button>
                  ),
                )}
              </div>
            </motion.div>
          )}

          <div className="message-column">
            <AnimatePresence
              initial={false}
            >
              {messages.map(
                (message) => (
                  <div
                    key={message.id}
                    data-palaver-message-id={
                      message.id
                    }
                    className={
                      activeMessageId ===
                      message.id
                        ? "palaver-message-anchor active"
                        : "palaver-message-anchor"
                    }
                    onMouseEnter={() =>
                      setActiveMessageId(
                        message.id,
                      )
                    }
                  >
                    <PalaverMessage
                      message={message}
                      copied={
                        copied ===
                        message.id
                      }
                      onCopy={copy}
                      onBranch={
                        branchFromMessage
                      }
                      onRetry={
                        retryAssistant
                      }
                      onQuote={
                        quoteMessage
                      }
                    />
                  </div>
                ),
              )}
            </AnimatePresence>

            {sending && (
              <motion.div
                className="thinking"
                initial={{
                  opacity: 0,
                  y: 10,
                }}
                animate={{
                  opacity: 1,
                  y: 0,
                }}
              >
                <Sparkles size={15} />
                <span>
                  palaver is working
                </span>

                <span className="thinking-pulse">
                  <i />
                  <i />
                  <i />
                </span>
              </motion.div>
            )}
          </div>
        </div>

        <AnimatePresence>
          {showJump && (
            <motion.button
              type="button"
              className="jump-latest"
              initial={{
                opacity: 0,
                y: 10,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              exit={{
                opacity: 0,
                y: 10,
              }}
              onClick={() =>
                scrollToLatest()
              }
            >
              <ArrowDown size={16} />
              latest
            </motion.button>
          )}
        </AnimatePresence>

        <div className="composer-zone">
          <AnimatePresence>
            {toolsOpen && (
              <motion.div
                className="tool-bloom"
                initial={
                  reducedMotion
                    ? false
                    : {
                        opacity: 0,
                        y: 16,
                        scale: 0.97,
                      }
                }
                animate={{
                  opacity: 1,
                  y: 0,
                  scale: 1,
                }}
                exit={{
                  opacity: 0,
                  y: 10,
                  scale: 0.98,
                }}
              >
                <span className="tool-bloom-label">
                  look deeper
                </span>

                <div>
                  {lenses.map(
                    (item) => {
                      const Icon =
                        item.icon

                      return (
                        <button
                          type="button"
                          key={item.id}
                          onClick={() =>
                            openLens(
                              item,
                            )
                          }
                        >
                          <Icon
                            size={18}
                          />

                          <span>
                            <strong>
                              {item.label}
                            </strong>

                            <small>
                              {item.eyebrow}
                            </small>
                          </span>
                        </button>
                      )
                    },
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <form
            className="composer"
            onSubmit={submit}
          >
            <button
              type="button"
              className={[
                "composer-tool",
                toolsOpen
                  ? "active"
                  : "",
              ]
                .filter(Boolean)
                .join(" ")}
              aria-label="Open Palaver tools"
              aria-expanded={toolsOpen}
              onClick={() =>
                setToolsOpen(
                  (current) =>
                    !current,
                )
              }
            >
              {toolsOpen ? (
                <X size={20} />
              ) : (
                <Plus size={21} />
              )}
            </button>

            <div className="composer-input">
              {voice.listening &&
                voice.interim && (
                  <div className="palaver-voice-interim">
                    {voice.interim}
                  </div>
                )}

              <textarea
                ref={textareaRef}
                value={draft}
                rows={1}
                aria-label="Message Palaver"
                placeholder={
                  voice.listening
                    ? "Listening…"
                    : activeBranchId
                      ? "Continue this path…"
                      : "Tell Palaver what you want…"
                }
                onChange={(event) =>
                  setDraft(
                    event.target.value,
                  )
                }
                onKeyDown={
                  onComposerKeyDown
                }
              />

              <div className="composer-meta">
                <span>
                  enter to send
                </span>
                <span>
                  ⌘f to navigate
                </span>
              </div>
            </div>

            {voice.supported &&
              !sending && (
                <button
                  type="button"
                  className={[
                    "composer-voice",
                    voice.listening
                      ? "active"
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  aria-label={
                    voice.listening
                      ? "Stop listening"
                      : "Use voice input"
                  }
                  onClick={
                    voice.toggle
                  }
                >
                  {voice.listening ? (
                    <span className="palaver-voice-wave">
                      <i />
                      <i />
                      <i />
                      <i />
                    </span>
                  ) : (
                    <Mic size={18} />
                  )}
                </button>
              )}

            {sending ? (
              <button
                type="button"
                className="composer-send stop"
                aria-label="Stop request"
                onClick={() =>
                  abortRef.current?.abort()
                }
              >
                <CircleStop
                  size={20}
                />
              </button>
            ) : (
              <button
                type="submit"
                className="composer-send"
                aria-label="Send message"
                disabled={
                  !draft.trim()
                }
              >
                <Send size={19} />
              </button>
            )}
          </form>

          {voice.error && (
            <button
              type="button"
              className="palaver-voice-error"
              onClick={
                voice.clearError
              }
            >
              <MicOff size={13} />
              {voice.error}
              <X size={12} />
            </button>
          )}

          <PalaverConversationTools
            messageCount={
              messages.length
            }
            branchCount={
              branches.length
            }
            onCopy={
              copyCurrentPath
            }
            onExport={
              exportConversation
            }
            onImport={
              importConversation
            }
            onClearCurrent={() => {
              clearCurrentPath()
              setActiveMessageId(null)
            }}
            onClearAll={() => {
              clearAll()
              setActiveMessageId(null)
              setBranchesOpen(false)
              setFocusOpen(false)
            }}
          />
        </div>
      </section>

      <PalaverBranches
        open={branchesOpen}
        branches={branches}
        activeBranchId={
          activeBranchId
        }
        onClose={() =>
          setBranchesOpen(false)
        }
        onSelect={(branchId) => {
          selectBranch(branchId)
          setBranchesOpen(false)

          requestAnimationFrame(
            () => {
              scrollToLatest("auto")
              focusComposer()
            },
          )
        }}
      />

      <PalaverFocusRail
        open={focusOpen}
        messages={messages}
        activeMessageId={
          activeMessageId
        }
        branchCount={
          branches.length
        }
        onClose={() =>
          setFocusOpen(false)
        }
        onSelect={(messageId) => {
          scrollToMessage(messageId)
          setFocusOpen(false)
        }}
        onPrevious={() =>
          moveMessageFocus(-1)
        }
        onNext={() =>
          moveMessageFocus(1)
        }
        onOpenBranches={() => {
          setFocusOpen(false)
          setBranchesOpen(true)
        }}
      />

      <AnimatePresence>
        {activeLens && (
          <>
            <motion.button
              type="button"
              className="lens-backdrop"
              aria-label="Close lens"
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              exit={{
                opacity: 0,
              }}
              onClick={() => {
                setLens(null)
                focusComposer()
              }}
            />

            <motion.aside
              className="lens"
              initial={
                reducedMotion
                  ? false
                  : {
                      opacity: 0,
                      x: 60,
                      scale: 0.98,
                    }
              }
              animate={{
                opacity: 1,
                x: 0,
                scale: 1,
              }}
              exit={{
                opacity: 0,
                x: 40,
                scale: 0.985,
              }}
              transition={{
                type: "spring",
                stiffness: 330,
                damping: 34,
              }}
            >
              <header className="lens-head">
                <div>
                  <span>
                    {activeLens.eyebrow}
                  </span>
                  <h2>
                    {activeLens.label}
                  </h2>
                </div>

                <div>
                  <button
                    type="button"
                    aria-label="Refresh lens"
                    onClick={() =>
                      openLens(
                        activeLens,
                      )
                    }
                  >
                    <RefreshCw
                      size={17}
                    />
                  </button>

                  <button
                    type="button"
                    aria-label="Close lens"
                    onClick={() => {
                      setLens(null)
                      focusComposer()
                    }}
                  >
                    <X size={18} />
                  </button>
                </div>
              </header>

              <div className="lens-content">
                {lensLoading && (
                  <div className="lens-state">
                    <LoaderCircle
                      className="spin"
                      size={24}
                    />
                    <span>
                      reading{" "}
                      {activeLens.label.toLowerCase()}
                    </span>
                  </div>
                )}

                {lensError && (
                  <div className="lens-state lens-error">
                    <Zap size={23} />
                    <span>
                      {lensError}
                    </span>

                    <button
                      type="button"
                      onClick={() =>
                        openLens(
                          activeLens,
                        )
                      }
                    >
                      retry
                    </button>
                  </div>
                )}

                {!lensLoading &&
                  !lensError && (
                    <PalaverLensView
                      lens={
                        activeLens.id
                      }
                      data={lensData}
                      onAsk={(prompt) => {
                        setLens(null)
                        setDraft(prompt)
                        focusComposer()
                      }}
                    />
                  )}
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {paletteOpen && (
          <motion.div
            className="palette-backdrop"
            initial={{
              opacity: 0,
            }}
            animate={{
              opacity: 1,
            }}
            exit={{
              opacity: 0,
            }}
            onMouseDown={(event) => {
              if (
                event.target ===
                event.currentTarget
              ) {
                setPaletteOpen(false)
              }
            }}
          >
            <motion.div
              className="palette"
              role="dialog"
              aria-modal="true"
              aria-label="Palaver commands"
              initial={
                reducedMotion
                  ? false
                  : {
                      opacity: 0,
                      y: -18,
                      scale: 0.97,
                    }
              }
              animate={{
                opacity: 1,
                y: 0,
                scale: 1,
              }}
              exit={{
                opacity: 0,
                y: -10,
                scale: 0.98,
              }}
            >
              <header>
                <Search size={20} />
                <span>
                  jump anywhere
                </span>
                <span className="keycap">
                  esc
                </span>
              </header>

              <div className="palette-list">
                <button
                  type="button"
                  onClick={() => {
                    setPaletteOpen(false)
                    focusComposer()
                  }}
                >
                  <MessageCircle
                    size={19}
                  />

                  <span>
                    <strong>
                      Conversation
                    </strong>
                    <small>
                      return to composer
                    </small>
                  </span>

                  <ChevronRight
                    size={16}
                  />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setPaletteOpen(false)
                    setFocusOpen(true)
                  }}
                >
                  <Search size={19} />

                  <span>
                    <strong>
                      Find message
                    </strong>
                    <small>
                      search this path
                    </small>
                  </span>

                  <ChevronRight
                    size={16}
                  />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setPaletteOpen(false)
                    setBranchesOpen(true)
                  }}
                >
                  <GitBranch
                    size={19}
                  />

                  <span>
                    <strong>
                      Conversation paths
                    </strong>
                    <small>
                      switch branches
                    </small>
                  </span>

                  <ChevronRight
                    size={16}
                  />
                </button>

                {lenses.map(
                  (item) => {
                    const Icon =
                      item.icon

                    return (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() =>
                          openLens(
                            item,
                          )
                        }
                      >
                        <Icon size={19} />

                        <span>
                          <strong>
                            {item.label}
                          </strong>
                          <small>
                            {item.eyebrow}
                          </small>
                        </span>

                        <ChevronRight
                          size={16}
                        />
                      </button>
                    )
                  },
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div
        className="sr-only"
        aria-live="assertive"
      >
        {sending
          ? "Palaver is working."
          : voice.listening
            ? "Palaver is listening."
            : activeBranchId
              ? "Alternate conversation path active."
              : healthy === false
                ? "Palaver runtime is unavailable."
                : ""}
      </div>
    </main>
  )
}
