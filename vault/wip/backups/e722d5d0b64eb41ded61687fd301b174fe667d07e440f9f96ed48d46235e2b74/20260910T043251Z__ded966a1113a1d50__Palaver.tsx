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
  Network,
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
  PalaverMessageRecord,
} from "./PalaverMessage"
import {
  usePalaverConversation,
} from "./usePalaverConversation"
import {
  usePalaverVoice,
} from "./usePalaverVoice"

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

const API = (
  import.meta.env.VITE_PALAVER_API_BASE ||
  ""
).replace(/\/$/, "")

const DRAFT_KEY =
  "savant.palaver.ui.draft.v4"

const HISTORY_KEY =
  "savant.palaver.ui.prompt-history.v4"

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

function uid(
  prefix: string,
) {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID ===
      "function"
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
  const response =
    await fetch(
      `${API}${path}`,
      {
        ...init,
        headers: {
          "Content-Type":
            "application/json",
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
  const reducedMotion =
    useReducedMotion()

  const conversation =
    usePalaverConversation()

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
  } = conversation

  const [draft, setDraft] =
    useState("")

  const [sending, setSending] =
    useState(false)

  const [online, setOnline] =
    useState(
      navigator.onLine,
    )

  const [healthy, setHealthy] =
    useState<boolean | null>(
      null,
    )

  const [latency, setLatency] =
    useState<number | null>(
      null,
    )

  const [toolsOpen, setToolsOpen] =
    useState(false)

  const [
    paletteOpen,
    setPaletteOpen,
  ] = useState(false)

  const [
    branchesOpen,
    setBranchesOpen,
  ] = useState(false)

  const [
    focusOpen,
    setFocusOpen,
  ] = useState(false)

  const [
    activeMessageId,
    setActiveMessageId,
  ] = useState<
    string | null
  >(null)

  const [lens, setLens] =
    useState<LensId>(null)

  const [lensData, setLensData] =
    useState<unknown>(null)

  const [
    lensLoading,
    setLensLoading,
  ] = useState(false)

  const [
    lensError,
    setLensError,
  ] = useState("")

  const [copied, setCopied] =
    useState<string | null>(
      null,
    )

  const [
    showJump,
    setShowJump,
  ] = useState(false)

  const [history, setHistory] =
    useState<string[]>(
      () => {
        try {
          const raw =
            localStorage.getItem(
              HISTORY_KEY,
            )

          return raw
            ? JSON.parse(raw)
            : []
        } catch {
          return []
        }
      },
    )

  const [
    historyIndex,
    setHistoryIndex,
  ] = useState(-1)

  const textareaRef =
    useRef<HTMLTextAreaElement>(
      null,
    )

  const streamRef =
    useRef<HTMLDivElement>(
      null,
    )

  const abortRef =
    useRef<AbortController | null>(
      null,
    )

  const userScrolledRef =
    useRef(false)

  const activeLens =
    useMemo(
      () =>
        lenses.find(
          (candidate) =>
            candidate.id === lens,
        ) ?? null,
      [lens],
    )

  const focusComposer =
    useCallback(() => {
      requestAnimationFrame(
        () =>
          textareaRef.current?.focus(),
      )
    }, [])

  const voice =
    usePalaverVoice(
      useCallback(
        (text: string) => {
          setDraft(
            (current) =>
              current.trim()
                ? `${current.trim()} ${text}`
                : text,
          )

          focusComposer()
        },
        [focusComposer],
      ),
    )

  const scrollToLatest =
    useCallback(
      (
        behavior: ScrollBehavior =
          "smooth",
      ) => {
        const stream =
          streamRef.current

        if (!stream) {
          return
        }

        stream.scrollTo({
          top: stream.scrollHeight,
          behavior,
        })

        userScrolledRef.current =
          false

        setShowJump(false)

        if (messages.length) {
          setActiveMessageId(
            messages[
              messages.length - 1
            ].id,
          )
        }
      },
      [messages],
    )

  const scrollToMessage =
    useCallback(
      (
        messageId: string,
      ) => {
        const selector =
          `[data-palaver-message-id="${CSS.escape(
            messageId,
          )}"]`

        const element =
          document.querySelector(
            selector,
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

        setActiveMessageId(
          messageId,
        )
      },
      [reducedMotion],
    )

  const moveMessageFocus =
    useCallback(
      (
        direction: -1 | 1,
      ) => {
        if (!messages.length) {
          return
        }

        const currentIndex =
          activeMessageId
            ? messages.findIndex(
                (message) =>
                  message.id ===
                  activeMessageId,
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
                  currentIndex +
                    direction,
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

  const checkHealth =
    useCallback(
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
          await apiJson(
            "/api/health",
            {
              cache: "no-store",
            },
          )

          setHealthy(true)

          setLatency(
            Math.round(
              performance.now() -
                started,
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
    const saved =
      localStorage.getItem(
        DRAFT_KEY,
      )

    if (saved) {
      setDraft(saved)
    }

    checkHealth()

    const onFocus =
      () => checkHealth()

    const onVisibility =
      () => {
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
    localStorage.setItem(
      DRAFT_KEY,
      draft,
    )
  }, [draft])

  useEffect(() => {
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify(
        history.slice(
          0,
          40,
        ),
      ),
    )
  }, [history])

  useEffect(() => {
    const onlineHandler =
      () => {
        setOnline(true)
        checkHealth()
      }

    const offlineHandler =
      () => {
        setOnline(false)
        setHealthy(false)
      }

    window.addEventListener(
      "online",
      onlineHandler,
    )

    window.addEventListener(
      "offline",
      offlineHandler,
    )

    return () => {
      window.removeEventListener(
        "online",
        onlineHandler,
      )

      window.removeEventListener(
        "offline",
        offlineHandler,
      )
    }
 
