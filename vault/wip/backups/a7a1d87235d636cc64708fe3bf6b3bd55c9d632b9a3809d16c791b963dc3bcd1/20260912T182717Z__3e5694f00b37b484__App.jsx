import { useEffect, useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import EditorWorkspace from "./workspace/EditorWorkspace.jsx"
import DiffViewer from "./workspace/DiffViewer.jsx"
import "./style.css"

const API = "http://127.0.0.1:8787"

async function request(path, options = {}) {
  const res = await fetch(API + path, options)
  return await res.json()
}

async function getJsonSafe(path) {
  try {
    const res = await fetch(API + path)
    return await res.json()
  } catch (e) {
    return { ok: false, error: String(e), path }
  }
}

const spring = {
  type: "spring",
  stiffness: 260,
  damping: 28,
  mass: 0.9,
}

const soft = {
  initial: { opacity: 0, y: 18, scale: 0.985 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: 12, scale: 0.985 },
  transition: spring,
}

function AmbientField() {
  const particles = useMemo(
    () =>
      Array.from({ length: 58 }).map((_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        s: 0.35 + Math.random() * 1.6,
        d: 10 + Math.random() * 18,
      })),
    [],
  )

  return (
    <div className="ambient" aria-hidden="true">
      <div className="aurora a1" />
      <div className="aurora a2" />
      <div className="aurora a3" />
      <svg className="topology" viewBox="0 0 1000 1000" preserveAspectRatio="none">
        <motion.path
          d="M-20 580 C140 480 220 700 380 590 C560 465 635 245 820 340 C930 395 960 515 1040 455"
          animate={{ pathLength: [0.45, 0.85, 0.45], opacity: [0.11, 0.23, 0.11] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.path
          d="M-40 290 C150 205 255 350 420 270 C590 188 650 86 835 145 C920 172 990 240 1040 198"
          animate={{ pathLength: [0.22, 0.76, 0.22], opacity: [0.07, 0.18, 0.07] }}
          transition={{ duration: 13, repeat: Infinity, ease: "easeInOut" }}
        />
      </svg>
      {particles.map((p) => (
        <motion.span
          className="particle"
          key={p.id}
          style={{ left: `${p.x}%`, top: `${p.y}%`, width: p.s, height: p.s }}
          animate={{ y: [-6, 9, -6], x: [-3, 4, -3], opacity: [0.1, 0.55, 0.1] }}
          transition={{ duration: p.d, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </div>
  )
}





function NeuralSearchOverlay({ open, close, send, openView }) {
  const [query, setQuery] = useState("")
  const [scope, setScope] = useState("all")

  const scopes = ["all", "runtime", "repository", "memory", "graph", "authority"]

  const results = useMemo(() => {
    const base = [
      ["Open repository explorer", "repository", "Browse source, vault projections, and active files.", () => openView("files")],
      ["Open graph field", "graph", "Inspect relationship topology and dependency structure.", () => openView("graph")],
      ["Open timeline", "runtime", "Review recent execution and activity history.", () => openView("timeline")],
      ["Run health probe", "runtime", "Verify backend, routes, runtime, and current state.", () => send("health")],
      ["Read repository report", "repository", "Summarize repository state and source inventory.", () => send("repository report")],
      ["Query memory", "memory", "Search memory and message registry projections.", () => send("memory")],
      ["Inspect authority", "authority", "Inspect contracts, lineage, restore, and authority state.", () => send("authority")],
      ["Patch review", "runtime", "Open patch/recovery workflow context.", () => send("patches")],
    ]

    const q = query.toLowerCase().trim()

    return base.filter(([title, kind, detail]) => {
      const scopeMatch = scope === "all" || kind === scope
      const qMatch = !q || `${title} ${kind} ${detail}`.toLowerCase().includes(q)
      return scopeMatch && qMatch
    })
  }, [query, scope])

  function activate(action) {
    close()
    action()
    setQuery("")
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="neural-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={close}
        >
          <motion.div
            className="neural-search"
            initial={{ opacity: 0, y: 42, scale: .96, rotateX: -10 }}
            animate={{ opacity: 1, y: 0, scale: 1, rotateX: 0 }}
            exit={{ opacity: 0, y: 28, scale: .96, rotateX: -8 }}
            transition={spring}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="neural-head">
              <div>
                <span>Neural Command Surface</span>
                <strong>Search every operational layer.</strong>
              </div>
              <button onClick={close}>Esc</button>
            </div>

            <div className="neural-input-shell">
              <span>⌕</span>
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search runtime, repository, memory, graph, authority..."
                onKeyDown={(e) => {
                  if (e.key === "Escape") close()
                  if (e.key === "Enter" && results[0]) activate(results[0][3])
                }}
              />
            </div>

            <div className="scope-tabs">
              {scopes.map((x) => (
                <button key={x} className={scope === x ? "on" : ""} onClick={() => setScope(x)}>
                  {x}
                </button>
              ))}
            </div>

            <div className="neural-results">
              {results.map(([title, kind, detail, action], i) => (
                <motion.button
                  key={title}
                  onClick={() => activate(action)}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * .025, ...spring }}
                  whileHover={{ x: 4 }}
                >
                  <div>
                    <b>{title}</b>
                    <p>{detail}</p>
                  </div>
                  <small>{kind}</small>
                </motion.button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function AuthorityPreviewStack() {
  const items = [
    ["Authority", "contracts / lineage / ownership"],
    ["Recovery", "quarantine / restore / acceptance"],
    ["Repository", "source / imports / dependency"],
    ["Memory", "sessions / registry / retrieval"],
  ]

  return (
    <div className="authority-preview-stack">
      {items.map(([title, detail], i) => (
        <motion.div
          key={title}
          className="authority-preview"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * .045, ...spring }}
          whileHover={{ y: -4, scale: 1.012 }}
        >
          <span>{String(i + 1).padStart(2, "0")}</span>
          <div>
            <b>{title}</b>
            <small>{detail}</small>
          </div>
        </motion.div>
      ))}
    </div>
  )
}

function SystemMarquee() {
  const words = [
    "repository",
    "memory",
    "graph",
    "runtime",
    "authority",
    "lineage",
    "workspace",
    "recovery",
  ]

  return (
    <div className="system-marquee" aria-hidden="true">
      <motion.div
        animate={{ x: ["0%", "-50%"] }}
        transition={{ duration: 22, repeat: Infinity, ease: "linear" }}
      >
        {[...words, ...words, ...words, ...words].map((w, i) => (
          <span key={i}>{w}</span>
        ))}
      </motion.div>
    </div>
  )
}

function SpatialDock({ mode, setMode, loadTree, loadGraph, loadTimeline, send, setPalette }) {
  const items = [
    ["command", "⌘", "Command"],
    ["explorer", "⌁", "Explorer"],
    ["graph", "◎", "Graph"],
    ["observatory", "◈", "Observatory"],
    ["personality", "✦", "Persona"],
  ]

  function activate(id) {
    setMode(id)
    if (id === "explorer") loadTree()
    if (id === "graph") loadGraph()
    if (id === "observatory") send("health")
  }

  return (
    <motion.div
      className="spatial-dock"
      initial={{ opacity: 0, x: -28, scale: .96 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      transition={spring}
    >
      {items.map(([id, glyph, label]) => (
        <motion.button
          key={id}
          className={mode === id ? "active" : ""}
          onClick={() => activate(id)}
          whileHover={{ x: 4, scale: 1.04 }}
          whileTap={{ scale: .98 }}
        >
          <span>{glyph}</span>
          <small>{label}</small>
        </motion.button>
      ))}

      <div className="dock-separator" />

      <motion.button onClick={() => setPalette(true)} whileHover={{ x: 4, scale: 1.04 }}>
        <span>⌕</span>
        <small>Search</small>
      </motion.button>

      <motion.button onClick={loadTimeline} whileHover={{ x: 4, scale: 1.04 }}>
        <span>≋</span>
        <small>Time</small>
      </motion.button>
    </motion.div>
  )
}

function RouteConstellation({ openView, send }) {
  const routes = [
    ["/api/tree", "Explorer", () => openView("files")],
    ["/api/graph", "Graph", () => openView("graph")],
    ["/api/timeline", "Timeline", () => openView("timeline")],
    ["/api/runtime", "Runtime", () => send("health")],
    ["/api/repository/files", "Repository", () => send("repository report")],
    ["/api/memory/files", "Memory", () => send("memory")],
  ]

  return (
    <div className="route-constellation">
      <div className="route-title">
        <span>Route Constellation</span>
        <small>live interface surface</small>
      </div>

      <div className="route-grid">
        {routes.map(([route, label, action], i) => (
          <motion.button
            key={route}
            onClick={action}
            initial={{ opacity: 0, y: 10, scale: .98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: i * .035, ...spring }}
            whileHover={{ y: -3, scale: 1.018 }}
          >
            <b>{label}</b>
            <code>{route}</code>
          </motion.button>
        ))}
      </div>
    </div>
  )
}

function LayeredBackdropCard() {
  return (
    <div className="layered-backdrop-card" aria-hidden="true">
      <motion.div
        className="orbital-ring r1"
        animate={{ rotate: 360 }}
        transition={{ duration: 38, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="orbital-ring r2"
        animate={{ rotate: -360 }}
        transition={{ duration: 52, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="orbital-core"
        animate={{ scale: [1, 1.06, 1], opacity: [.65, .95, .65] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  )
}

function IntelligenceRibbon({ status, tree, graph, timeline, activeFile }) {
  const signals = [
    {
      label: "Runtime",
      value: status === "online" ? "online" : status,
      tone: status === "online" ? "good" : "warn",
    },
    {
      label: "Explorer",
      value: tree ? "indexed" : "idle",
      tone: tree ? "good" : "dim",
    },
    {
      label: "Graph",
      value: graph ? `${graph.node_count || graph.nodes?.length || 0}` : "idle",
      tone: graph ? "good" : "dim",
    },
    {
      label: "Timeline",
      value: timeline ? timeline.length : "idle",
      tone: timeline ? "good" : "dim",
    },
    {
      label: "Focus",
      value: activeFile ? "file" : "workspace",
      tone: activeFile ? "good" : "dim",
    },
  ]

  return (
    <motion.div className="intelligence-ribbon" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
      {signals.map((signal, i) => (
        <motion.div
          className={"signal " + signal.tone}
          key={signal.label}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.035, ...spring }}
        >
          <span>{signal.label}</span>
          <b>{signal.value}</b>
        </motion.div>
      ))}
    </motion.div>
  )
}

function CinematicDivider() {
  return (
    <div className="cinematic-divider" aria-hidden="true">
      <motion.span
        animate={{ x: ["-100%", "120%"] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  )
}

function QuickLens({ send, openView }) {
  const lenses = [
    ["Repository", "Inspect source structure", () => openView("files")],
    ["Graph", "Traverse relationships", () => openView("graph")],
    ["Timeline", "Read activity stream", () => openView("timeline")],
    ["Health", "Probe runtime", () => send("health")],
  ]

  return (
    <div className="quick-lens">
      {lenses.map(([title, detail, action], i) => (
        <motion.button
          key={title}
          onClick={action}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04, ...spring }}
          whileHover={{ y: -3, scale: 1.015 }}
        >
          <span>{title}</span>
          <small>{detail}</small>
        </motion.button>
      ))}
    </div>
  )
}

function FocusStrip({ activeFile, graph, timeline }) {
  let title = "No object selected"
  let detail = "Open a source file, graph, timeline, or command sequence."

  if (activeFile) {
    title = activeFile.path
    detail = `${activeFile.size || activeFile.content?.length || 0} chars`
  } else if (graph) {
    title = "Graph projection"
    detail = `${graph.node_count || graph.nodes?.length || 0} nodes / ${graph.edge_count || graph.edges?.length || 0} edges`
  } else if (timeline) {
    title = "Timeline projection"
    detail = `${timeline.length} events`
  }

  return (
    <motion.div className="focus-strip" layout>
      <div>
        <small>Current focus</small>
        <strong>{title}</strong>
      </div>
      <span>{detail}</span>
    </motion.div>
  )
}

function ModeSwitch({ mode, setMode }) {
  const modes = [
    ["command", "Command"],
    ["explorer", "Explorer"],
    ["graph", "Graph"],
    ["observatory", "Observatory"],
    ["personality", "Persona"],
  ]

  return (
    <div className="mode-switch">
      {modes.map(([id, label]) => (
        <motion.button
          key={id}
          className={mode === id ? "on" : ""}
          onClick={() => setMode(id)}
          layout
        >
          {mode === id && <motion.span className="mode-glow" layoutId="mode-glow" />}
          <span>{label}</span>
        </motion.button>
      ))}
    </div>
  )
}



function PersonalityGraphField({ graph }) {
  const nodes = graph?.nodes || []
  const edges = graph?.edges || []

  const shown = nodes.slice(0, 90)

  const points = shown.map((node, i) => {
    const ring = 1 + (i % 4)
    const radius = 13 + ring * 8
    const angle = (i / Math.max(shown.length, 1)) * Math.PI * 2 * (1 + (i % 3) * 0.13)

    return {
      id: node.id,
      label: node.label,
      kind: node.kind,
      x: 50 + Math.cos(angle) * radius,
      y: 50 + Math.sin(angle) * radius,
    }
  })

  function pointFor(id, fallback) {
    return points.find((p) => p.id === id) || points[fallback % Math.max(points.length, 1)]
  }

  return (
    <div className="personality-graph-field">
      <div className="personality-graph-head">
        <div>
          <b>Personality Graph</b>
          <small>{graph?.node_count || nodes.length} nodes / {graph?.edge_count || edges.length} edges</small>
        </div>
        <span>projection</span>
      </div>

      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <radialGradient id="personalityNodeGlow">
            <stop offset="0%" stopColor="rgba(255,255,255,.95)" />
            <stop offset="100%" stopColor="rgba(233,221,196,.12)" />
          </radialGradient>
        </defs>

        {edges.slice(0, 180).map((edge, i) => {
          const a = pointFor(edge.source, i)
          const b = pointFor(edge.target, i + 3)
          if (!a || !b) return null

          return (
            <motion.line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              initial={{ opacity: 0, pathLength: 0 }}
              animate={{ opacity: .18, pathLength: 1 }}
              transition={{ delay: i * .002, duration: .7 }}
            />
          )
        })}

        {points.map((node, i) => (
          <motion.g key={node.id || i}>
            {(node.kind === "kernel" || node.kind === "tier") && (
              <motion.circle
                className="personality-node-halo"
                cx={node.x}
                cy={node.y}
                r={node.kind === "kernel" ? 5.2 : 3.6}
                animate={{ opacity: [.08, .22, .08], scale: [1, 1.22, 1] }}
                transition={{ duration: 4.2, repeat: Infinity, delay: i * .04 }}
              />
            )}

            <motion.circle
              cx={node.x}
              cy={node.y}
              r={node.kind === "kernel" ? 1.7 : node.kind === "tier" ? 1.18 : .72}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: .95 }}
              transition={{ delay: i * .006, ...spring }}
            />
          </motion.g>
        ))}
      </svg>
    </div>
  )
}

function PersonalityEvolutionStream({ evolution, eventsText }) {
  const rows = evolution?.recent_events || []

  return (
    <div className="personality-evolution-stream">
      <div className="personality-card-head">
        <b>Evolution Stream</b>
        <small>{evolution?.event_count ?? 0} events</small>
      </div>

      <div className="evolution-rows">
        {rows.length === 0 && <p>No evolution events loaded.</p>}

        {rows.slice().reverse().map((row, i) => (
          <motion.div
            className="evolution-row"
            key={row.id || i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * .018, ...spring }}
          >
            <span>{row.kind}</span>
            <p>{row.text}</p>
            <small>{row.tags?.join(" / ")} · {row.intensity}</small>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function PersonalityPanel() {
  const [summary, setSummary] = useState(null)
  const [runtimePrompt, setRuntimePrompt] = useState(null)
  const [personalityGraph, setPersonalityGraph] = useState(null)
  const [evolution, setEvolution] = useState(null)
  const [eventsText, setEventsText] = useState(null)
  const [loading, setLoading] = useState(false)

  async function refresh() {
    setLoading(true)
    const data = await getJsonSafe("/api/personality/summary")
    const prompt = await getJsonSafe("/api/personality/runtime-prompt")
    const graphData = await getJsonSafe("/api/personality/graph")
    const evolutionData = await getJsonSafe("/api/personality/evolution")
    const eventData = await getJsonSafe("/api/personality/events")
    setSummary(data)
    setRuntimePrompt(prompt)
    setPersonalityGraph(graphData?.json || null)
    setEvolution(evolutionData?.json || null)
    setEventsText(eventData?.text || "")
    setLoading(false)
  }

  useEffect(() => {
    refresh()
  }, [])

  const projection = summary?.projection?.json || {}
  const genome = summary?.genome?.json?.traits || {}
  const physics = summary?.physics?.json || {}
  const identity = summary?.identity?.json || {}
  const council = projection?.activated_council || []

  const genomeRows = Object.entries(genome).slice(0, 14)

  return (
    <motion.div className="personality-panel" {...soft}>
      <div className="personality-hero">
        <div>
          <span>Personality Foundry</span>
          <h2>Synthetic identity kernel.</h2>
          <p>Trait genome, council activation, physics state, identity memory, and runtime prompt projection.</p>
        </div>

        <button onClick={refresh}>{loading ? "Refreshing" : "Refresh"}</button>
      </div>

      <div className="personality-grid">
        <div className="personality-card wide graph-personality-card">
          <PersonalityGraphField graph={personalityGraph} />
        </div>

        <div className="personality-card wide">
          <PersonalityEvolutionStream evolution={evolution} eventsText={eventsText} />
        </div>
        <div className="personality-card wide">
          <div className="personality-card-head">
            <b>Active Council</b>
            <small>{projection?.dominant_mode || "unknown"}</small>
          </div>

          <div className="council-stack">
            {council.length === 0 && <p>No active projection loaded.</p>}

            {council.map((member, i) => (
              <motion.div
                className="council-row"
                key={member.id || i}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * .035, ...spring }}
              >
                <span>{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <b>{member.id}</b>
                  <small>{member.purpose}</small>
                </div>
                <em>{member.score}</em>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="personality-card">
          <div className="personality-card-head">
            <b>Identity</b>
            <small>continuity</small>
          </div>
          <div className="identity-metrics">
            <strong>{identity?.memory_count ?? "—"}</strong>
            <span>identity memories</span>
          </div>
          <pre>{JSON.stringify(identity?.kind_counts || {}, null, 2)}</pre>
        </div>

        <div className="personality-card">
          <div className="personality-card-head">
            <b>Physics</b>
            <small>dynamic state</small>
          </div>
          <pre>{JSON.stringify(physics?.meta || physics, null, 2)}</pre>
        </div>

        <div className="personality-card wide">
          <div className="personality-card-head">
            <b>Genome</b>
            <small>stable bias weights</small>
          </div>

          <div className="genome-bars">
            {genomeRows.map(([key, value], i) => (
              <motion.div
                className="genome-bar"
                key={key}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * .025, ...spring }}
              >
                <div>
                  <span>{key.replaceAll("_", " ")}</span>
                  <small>{value}</small>
                </div>
                <div className="bar-track">
                  <motion.i initial={{ width: 0 }} animate={{ width: `${Number(value) * 100}%` }} transition={{ delay: .12 + i * .025, ...spring }} />
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="personality-card prompt-card wide">
          <div className="personality-card-head">
            <b>Runtime Prompt</b>
            <small>compiled projection</small>
          </div>
          <pre>{runtimePrompt?.text || "No runtime prompt loaded."}</pre>
        </div>
      </div>
    </motion.div>
  )
}

function ObservatoryPanel({ status, trace, graph, tree, timeline }) {
  const cards = [
    ["Backend", status === "online" ? "Stable" : "Active", status],
    ["Repository", tree ? "Loaded" : "Standby", tree ? "tree online" : "waiting"],
    ["Graph", graph ? "Mapped" : "Standby", graph ? `${graph.node_count || 0} nodes` : "waiting"],
    ["Timeline", timeline ? "Open" : "Standby", timeline ? `${timeline.length} rows` : "waiting"],
  ]

  return (
    <motion.div className="observatory" {...soft}>
      <div className="observatory-hero">
        <span>Runtime Observatory</span>
        <h2>System state at operational depth.</h2>
        <p>Inspect health, activity, graph density, workspace context, and active execution trace without leaving the workspace.</p>
      </div>

      <div className="observatory-grid">
        {cards.map(([k, v, m], i) => (
          <motion.div
            className="observer-card"
            key={k}
            initial={{ opacity: 0, y: 18, scale: .98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: i * .05, ...spring }}
          >
            <small>{k}</small>
            <strong>{v}</strong>
            <span>{m}</span>
          </motion.div>
        ))}
      </div>

      <div className="observer-trace">
        <b>Execution Trace</b>
        <pre>{trace}</pre>
      </div>
    </motion.div>
  )
}

function WorkspaceChrome({ children, title, subtitle }) {
  return (
    <motion.div className="workspace-chrome" {...soft}>
      <div className="workspace-chrome-head">
        <div>
          <strong>{title}</strong>
          <small>{subtitle}</small>
        </div>
        <div className="chrome-dots">
          <span />
          <span />
          <span />
        </div>
      </div>
      <div className="workspace-chrome-body">
        {children}
      </div>
    </motion.div>
  )
}

function StatusPill({ status }) {
  return (
    <motion.div className="status-pill" layout>
      <span className={"pulse " + status} />
      <span>{status}</span>
    </motion.div>
  )
}

function Message({ role, children }) {
  return (
    <motion.div {...soft} layout className={"message " + role}>
      <div className="message-meta">
        <span>{role === "user" ? "YOU" : "PALAVER"}</span>
        <small>{role === "user" ? "command" : "response"}</small>
      </div>
      <div className="message-body">{children}</div>
    </motion.div>
  )
}

function Palette({ open, close, send, openView }) {
  const [value, setValue] = useState("")

  const commands = [
    { label: "Health", value: "health", kind: "runtime" },
    { label: "Diagnostics", value: "diag", kind: "runtime" },
    { label: "Files", value: "files", kind: "repository" },
    { label: "Graph", value: "graph", kind: "graph" },
    { label: "Patches", value: "patches", kind: "patch" },
    { label: "Repository Report", value: "repository report", kind: "repository" },
    { label: "Read Core", value: "file read runtime/core.py", kind: "file" },
  ]

  function run(v = value) {
    if (!v.trim()) return
    close()
    send(v.trim())
    setValue("")
  }

  function visible() {
    const q = value.toLowerCase().trim()
    if (!q) return commands
    return commands.filter((x) => (x.label + " " + x.value + " " + x.kind).toLowerCase().includes(q))
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="palette-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={close}>
          <motion.div
            className="palette"
            initial={{ opacity: 0, y: 34, scale: 0.965, rotateX: -8 }}
            animate={{ opacity: 1, y: 0, scale: 1, rotateX: 0 }}
            exit={{ opacity: 0, y: 24, scale: 0.97, rotateX: -5 }}
            transition={spring}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="palette-header">
              <strong>Command Center</strong>
              <span>⌘ K</span>
            </div>
            <input
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") run()
                if (e.key === "Escape") close()
              }}
              placeholder="Search commands, routes, files, graph, memory..."
            />
            <div className="palette-results">
              {visible().map((cmd, i) => (
                <motion.button
                  key={cmd.value}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.025 }}
                  onClick={() => run(cmd.value)}
                >
                  <span>{cmd.label}</span>
                  <small>{cmd.kind}</small>
                </motion.button>
              ))}
            </div>
            <div className="palette-actions">
              <button onClick={() => openView("files")}>Explorer</button>
              <button onClick={() => openView("graph")}>Graph</button>
              <button onClick={() => openView("timeline")}>Timeline</button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}


function RepositoryIntelligencePanel({ tree }) {
  function walk(node, acc = { files: 0, dirs: 0 }) {
    if (!node) return acc
    if (node.type === "directory") acc.dirs += 1
    else acc.files += 1
    for (const child of node.children || []) walk(child, acc)
    return acc
  }

  const stats = walk(tree)
  const cards = [
    ["Files", stats.files],
    ["Folders", stats.dirs],
    ["State", tree ? "live" : "idle"],
  ]

  return (
    <div className="repo-intelligence">
      {cards.map(([label, value], i) => (
        <motion.div
          key={label}
          className="repo-intel-card"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * .035, ...spring }}
        >
          <span>{label}</span>
          <b>{value}</b>
        </motion.div>
      ))}
    </div>
  )
}

function RepositoryFocusBoard({ tree, openFile }) {
  const files = []

  function collect(node) {
    if (!node || files.length >= 18) return
    if (node.type !== "directory") files.push(node)
    for (const child of node.children || []) collect(child)
  }

  collect(tree)

  return (
    <div className="repo-focus-board">
      <div className="repo-focus-head">
        <div>
          <span>Repository Surface</span>
          <strong>High-density source navigation.</strong>
        </div>
        <small>{files.length} visible files</small>
      </div>

      <div className="repo-focus-grid">
        {files.map((file, i) => (
          <motion.button
            key={file.path || i}
            onClick={() => openFile(file.path)}
            initial={{ opacity: 0, y: 12, scale: .985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: i * .018, ...spring }}
            whileHover={{ y: -4, scale: 1.012 }}
          >
            <span>{String(i + 1).padStart(2, "0")}</span>
            <b>{file.name}</b>
            <small>{file.path}</small>
          </motion.button>
        ))}
      </div>
    </div>
  )
}

function FileTree({ tree, openFile }) {
  if (!tree) {
    return (
      <div className="empty-card">
        <span>Repository Explorer</span>
        <p>Open the file system to inspect source, state, and lineage.</p>
      </div>
    )
  }

  function Node({ node, depth = 0 }) {
    const isDir = node.type === "directory"
    const [open, setOpen] = useState(depth < 1)

    return (
      <div>
        <motion.div
          className={"tree-item " + (isDir ? "dir" : "file")}
          style={{ paddingLeft: 10 + depth * 14 }}
          onClick={() => (isDir ? setOpen(!open) : openFile(node.path))}
          whileHover={{ x: 3 }}
          transition={spring}
        >
          <span className="tree-icon">{isDir ? (open ? "▾" : "▸") : "•"}</span>
          <span className="tree-name">{node.name}</span>
          <small>{isDir ? "dir" : "src"}</small>
        </motion.div>
        <AnimatePresence initial={false}>
          {isDir && open && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={spring}>
              {node.children?.map((child, i) => <Node key={child.path || child.name + i} node={child} depth={depth + 1} />)}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    )
  }

  return (
    <div className="subtool">
      <RepositoryIntelligencePanel tree={tree} />
      <RepositoryFocusBoard tree={tree} openFile={openFile} />

      <div className="subtool-title">
        <span>Repository Tree</span>
        <small>live edifice</small>
      </div>
      <div className="tree-shell">
        <Node node={tree} />
      </div>
    </div>
  )
}


function GraphIntelligencePanel({ graph }) {
  const nodes = graph?.nodes || []
  const edges = graph?.edges || []

  const density = nodes.length ? Math.min(100, Math.round((edges.length / nodes.length) * 10)) : 0

  const rows = [
    ["Nodes", nodes.length || graph?.node_count || 0],
    ["Edges", edges.length || graph?.edge_count || 0],
    ["Density", density + "%"],
    ["Mode", "Force"],
  ]

  return (
    <div className="graph-intelligence">
      {rows.map(([label, value], i) => (
        <motion.div
          key={label}
          className="graph-intel-card"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * .035, ...spring }}
        >
          <span>{label}</span>
          <b>{value}</b>
        </motion.div>
      ))}
    </div>
  )
}

function GraphInspectorRail({ graph }) {
  const sampleNodes = (graph?.nodes || []).slice(0, 9)

  return (
    <div className="graph-inspector-rail">
      <div className="graph-inspector-title">
        <span>Inspector</span>
        <small>semantic sample</small>
      </div>

      <div className="graph-node-list">
        {sampleNodes.length === 0 && <p>No graph nodes loaded.</p>}

        {sampleNodes.map((node, i) => (
          <motion.div
            className="graph-node-row"
            key={node.id || i}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * .025, ...spring }}
          >
            <span>{String(i + 1).padStart(2, "0")}</span>
            <b>{node.label || node.id || "node"}</b>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function GraphView({ graph }) {
  const nodes = (graph.nodes || []).slice(0, 120)
  const edges = (graph.edges || []).slice(0, 280)

  const points = nodes.map((n, i) => {
    const ring = i % 3
    const radius = 20 + ring * 12
    const a = (i / Math.max(nodes.length, 1)) * Math.PI * 2 * (ring + 1)
    return {
      id: n.id,
      label: n.label || n.id,
      x: 50 + Math.cos(a) * radius,
      y: 50 + Math.sin(a) * radius,
    }
  })

  return (
    <motion.div {...soft} className="graph-wrap graph-flagship">
      <div className="graph-toolbar">
        <div>
          <strong>Relationship Field</strong>
          <small>repository graph projection</small>
        </div>
        <div className="graph-stats">
          <span>{graph.node_count || nodes.length} nodes</span>
          <span>{graph.edge_count || edges.length} edges</span>
        </div>
      </div>

      <div className="graph-stage">
        <div className="graph-canvas-shell">
          <svg viewBox="0 0 100 100">
            <defs>
              <radialGradient id="nodeGlow">
                <stop offset="0%" stopColor="rgba(255,255,255,.95)" />
                <stop offset="100%" stopColor="rgba(255,255,255,.08)" />
              </radialGradient>

              <filter id="softGlow">
                <feGaussianBlur stdDeviation="1.2" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <motion.g
              initial={{ opacity: 0, scale: .92, rotate: -2 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              transition={spring}
              style={{ transformOrigin: "center" }}
            >
              {edges.map((e, i) => {
                const a = points[i % Math.max(points.length, 1)]
                const b = points[(i * 7) % Math.max(points.length, 1)]
                if (!a || !b) return null
                return (
                  <motion.line
                    key={i}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    initial={{ opacity: 0, pathLength: 0 }}
                    animate={{ opacity: 0.2, pathLength: 1 }}
                    transition={{ delay: i * 0.0015, duration: .7 }}
                  />
                )
              })}

              {points.map((p, i) => (
                <motion.g key={p.id || i}>
                  {i % 11 === 0 && (
                    <motion.circle
                      cx={p.x}
                      cy={p.y}
                      r="3.4"
                      className="node-halo"
                      animate={{ scale: [1, 1.45, 1], opacity: [.08, .2, .08] }}
                      transition={{ duration: 3.6, repeat: Infinity, delay: i * .05 }}
                    />
                  )}

                  <motion.circle
                    cx={p.x}
                    cy={p.y}
                    r={i % 9 === 0 ? "1.28" : "0.72"}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 0.95 }}
                    transition={{ delay: i * 0.004, ...spring }}
                  />
                </motion.g>
              ))}
            </motion.g>
          </svg>
        </div>

        <div className="graph-sidecar">
          <GraphIntelligencePanel graph={graph} />
          <GraphInspectorRail graph={graph} />
        </div>
      </div>
    </motion.div>
  )
}

function Timeline({ rows }) {
  return (
    <motion.div {...soft} className="timeline">
      {rows.slice().reverse().slice(0, 80).map((row, i) => (
        <motion.div className="timeline-row" key={i} initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.012 }}>
          <small>{row.timestamp}</small>
          <p>{row.summary}</p>
        </motion.div>
      ))}
    </motion.div>
  )
}

function MetricDeck({ status }) {
  const cards = [
    ["Mode", "AI", "operational"],
    ["Vault", "ON", "persistent"],
    ["Patch", "SAFE", "reviewable"],
    ["Graph", "LIVE", "linked"],
    ["Runtime", status.toUpperCase(), "backend"],
  ]

  return (
    <div className="metric-deck">
      {cards.map(([k, v, m], i) => (
        <motion.div key={k} className="metric" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 + i * 0.04 }}>
          <small>{k}</small>
          <strong>{v}</strong>
          <span>{m}</span>
        </motion.div>
      ))}
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([{ role: "assistant", text: "Palaver online. Use Ctrl+K for the command center." }])
  const [input, setInput] = useState("")
  const [trace, setTrace] = useState("ready")
  const [status, setStatus] = useState("online")
  const [palette, setPalette] = useState(false)
  const [mode, setMode] = useState("command")
  const [neuralSearch, setNeuralSearch] = useState(false)

  const [tree, setTree] = useState(null)
  const [activeFile, setActiveFile] = useState(null)
  const [graph, setGraph] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [diff, setDiff] = useState("")

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setNeuralSearch(true)
      }
      if (e.key === "Escape") setPalette(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  async function send(text) {
    if (!text) return

    setMessages((m) => [...m, { role: "user", text }])
    setStatus("thinking")
    setTrace("running")

    try {
      const data = await request("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      })

      setMessages((m) => [...m, { role: "assistant", text: data.answer || "(empty response)" }])
      setTrace(data.trace || "")
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "Browser/API error: " + e }])
      setTrace(String(e))
    }

    setStatus("online")
  }

  async function submit() {
    const text = input.trim()
    if (!text) return
    setInput("")
    await send(text)
  }

  async function loadTree() {
    const data = await request("/api/tree")
    setTree(data.tree)
    setGraph(null)
    setTimeline(null)
    setDiff("")
  }

  async function openFile(path) {
    const data = await request("/api/file?path=" + encodeURIComponent(path))

    if (data.ok) {
      setActiveFile(data.file)
      setDiff("")
      setGraph(null)
      setTimeline(null)
    } else {
      setTrace(data.error || "file failed")
    }
  }

  async function saveFile(path, content) {
    const data = await request("/api/file/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    })

    setTrace(JSON.stringify(data, null, 2))
    setMessages((m) => [...m, { role: "assistant", text: data.ok ? `Saved ${path}` : `Save failed: ${data.error || "unknown"}` }])
  }

  async function diffFile(path, content) {
    const data = await request("/api/file/diff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    })

    if (data.ok) {
      setDiff(data.diff.diff || "")
      setGraph(null)
      setTimeline(null)
    }

    setTrace(JSON.stringify(data, null, 2))
  }

  async function loadGraph() {
    const data = await request("/api/graph")
    setGraph(data.graph)
    setActiveFile(null)
    setTimeline(null)
    setDiff("")
  }

  async function loadTimeline() {
    const data = await request("/api/timeline")
    setTimeline(data.timeline || [])
    setActiveFile(null)
    setGraph(null)
    setDiff("")
  }

  function openView(view) {
    setPalette(false)
    if (view === "files") loadTree()
    if (view === "graph") loadGraph()
    if (view === "timeline") loadTimeline()
  }

  return (
    <>
      <AmbientField />
      <Palette open={palette} close={() => setPalette(false)} send={send} openView={openView} />
      <NeuralSearchOverlay
        open={neuralSearch}
        close={() => setNeuralSearch(false)}
        send={send}
        openView={openView}
      />

      <div className="app">
        <SpatialDock
          mode={mode}
          setMode={setMode}
          loadTree={loadTree}
          loadGraph={loadGraph}
          loadTimeline={loadTimeline}
          send={send}
          setPalette={setPalette}
        />

        <motion.header className="top" initial={{ opacity: 0, y: -18 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
          <div className="brand">
            <motion.div className="logo" whileHover={{ rotate: 12, scale: 1.06 }} transition={spring}>
              P
            </motion.div>
            <div>
              <h1>Palaver</h1>
              <p>knowledge cockpit / graph workspace / runtime observatory</p>
            </div>
          </div>

          <nav>
            <button className="active" onClick={() => send("health")}>Health</button>
            <button onClick={loadTree}>Explorer</button>
            <button onClick={loadGraph}>Graph</button>
            <button onClick={loadTimeline}>Timeline</button>
            <button onClick={() => send("patches")}>Patches</button>
            <button className="accent" onClick={() => setNeuralSearch(true)}>Command</button>
          </nav>

          <ModeSwitch mode={mode} setMode={setMode} />
          <StatusPill status={status} />
        </motion.header>

        <IntelligenceRibbon
          status={status}
          tree={tree}
          graph={graph}
          timeline={timeline}
          activeFile={activeFile}
        />

        <main className="shell">
          <motion.section className="panel command-rail" {...soft}>
            <div className="panel-head">
              <b>Command Rail</b>
              <span>runtime</span>
            </div>
            <div className="panel-body">
              <p className="kicker">Operational knowledge environment</p>
              <h2 className="manifesto">Navigate memory, source, graph, runtime, and authority from one living workspace.</h2>

              <CinematicDivider />

              <SystemMarquee />

              <QuickLens send={send} openView={openView} />

              <div className="button-grid">
                <button className="primary" onClick={() => send("health")}>Health</button>
                <button onClick={() => send("diag")}>Diagnostics</button>
                <button onClick={() => send("files")}>Files</button>
                <button onClick={() => send("graph")}>Graph</button>
                <button onClick={() => send("patches")}>Patches</button>
                <button onClick={() => send("rebuild")}>Rebuild</button>
                <button onClick={() => send("repository report")}>Repository</button>
                <button onClick={() => send("file read runtime/core.py")}>Read Core</button>
                <button onClick={loadTree}>Explorer</button>
                <button onClick={loadGraph}>Graph Field</button>
                <button onClick={loadTimeline}>Timeline</button>
                <button className="accent" onClick={() => setNeuralSearch(true)}>Command Center</button>
              </div>

              <MetricDeck status={status} />

              <RouteConstellation openView={openView} send={send} />

              <AuthorityPreviewStack />

              <FileTree tree={tree} openFile={openFile} />
            </div>
          </motion.section>

          <motion.section className="panel chat" {...soft} transition={{ ...spring, delay: 0.06 }}>
            <div className="panel-head">
              <b>Conversation</b>
              <span>persistent</span>
            </div>
            <div className="chat-scroll">
              <AnimatePresence initial={false}>
                {messages.map((m, i) => <Message key={i} role={m.role}>{m.text}</Message>)}
              </AnimatePresence>
            </div>

            <div className="composer">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    submit()
                  }
                }}
                placeholder="Ask Palaver anything..."
              />
              <button onClick={() => setNeuralSearch(true)}>⌘</button>
              <button className="accent" onClick={submit}>➜</button>
            </div>
          </motion.section>

          <motion.aside className="panel right" {...soft} transition={{ ...spring, delay: 0.12 }}>
            <div className="panel-head">
              <b>Workspace</b>
              <span>live</span>
            </div>
            <div className="panel-body workspace-body">
              <FocusStrip activeFile={activeFile} graph={graph} timeline={timeline} />

              <AnimatePresence mode="wait">
                {mode === "observatory" && (
                  <ObservatoryPanel
                    key="observatory"
                    status={status}
                    trace={trace}
                    graph={graph}
                    tree={tree}
                    timeline={timeline}
                  />
                )}

                {mode === "personality" && (
                  <PersonalityPanel key="personality" />
                )}

                {mode !== "observatory" && mode !== "personality" && activeFile && !diff && (
                  <WorkspaceChrome key="editor" title={activeFile.path} subtitle="source editor">
                    <EditorWorkspace path={activeFile.path} content={activeFile.content} onSave={saveFile} onDiff={diffFile} />
                  </WorkspaceChrome>
                )}

                {mode !== "observatory" && mode !== "personality" && diff && (
                  <WorkspaceChrome key="diff" title="Patch Diff" subtitle="review projection">
                    <DiffViewer diff={diff} />
                  </WorkspaceChrome>
                )}

                {mode !== "observatory" && mode !== "personality" && graph && <GraphView key="graph" graph={graph} />}
                {mode !== "observatory" && mode !== "personality" && timeline && <Timeline key="timeline" rows={timeline} />}

                {mode !== "observatory" && mode !== "personality" && !activeFile && !diff && !graph && !timeline && (
                  <motion.div className="empty-state" key="empty" {...soft}>
                    <span>Workspace</span>
                    <h1>Intelligence cockpit</h1>
                    <p>Open a file, traverse the graph, inspect the timeline, or work through the command center.</p>
                    <LayeredBackdropCard />
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="trace">
                <b>TRACE</b>
                <pre>{trace}</pre>
              </div>
            </div>
          </motion.aside>
        </main>
      </div>
    </>
  )
}
