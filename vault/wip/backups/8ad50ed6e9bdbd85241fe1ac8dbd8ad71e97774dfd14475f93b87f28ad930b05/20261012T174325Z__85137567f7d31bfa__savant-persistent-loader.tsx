import React, { useEffect, useLayoutEffect, useRef, useState } from "react"
import SavantMark from "./savant-mark"
import "./savant-persistent-loader.css"

type Frame = { left: number; top: number; width: number; height: number }
type Props = {
  ready: boolean
  children: React.ReactNode
  headerTargetId?: string
  minimumLoadingMs?: number
  className?: string
  onDocked?: () => void
}

const TRANSITION_MS = 1850
const centerFrame = (targetSize = 62): Frame => {
  const size = Math.min(targetSize * 2, window.innerWidth - 32, window.innerHeight - 32)
  return { left: (window.innerWidth - size) / 2, top: (window.innerHeight - size) / 2, width: size, height: size }
}
const sameFrame = (a: Frame | null, b: Frame) => !!a && Math.abs(a.left - b.left) < 0.5 && Math.abs(a.top - b.top) < 0.5 && Math.abs(a.width - b.width) < 0.5 && Math.abs(a.height - b.height) < 0.5

/** One persistent WebGL mark travels from the loading screen to the real header slot. */
export default function SavantPersistentLoader({
  ready, children, headerTargetId = "savant-header-logo-slot",
  minimumLoadingMs = 10000, className = "", onDocked,
}: Props) {
  const started = useRef(typeof performance !== "undefined" ? performance.now() : Date.now())
  const [elapsed, setElapsed] = useState(false)
  const [target, setTarget] = useState<HTMLElement | null>(null)
  const [frame, setFrame] = useState<Frame | null>(null)
  const [reduced, setReduced] = useState(false)
  const [docked, setDocked] = useState(false)
  const [entered, setEntered] = useState(false)
  const notified = useRef(false)
  const completed = ready && elapsed
  const moving = entered && !!target

  useEffect(() => {
    const timeout = window.setTimeout(() => setElapsed(true), Math.max(0, minimumLoadingMs - ((typeof performance !== "undefined" ? performance.now() : Date.now()) - started.current)))
    return () => window.clearTimeout(timeout)
  }, [minimumLoadingMs])

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setReduced(query.matches)
    update()
    query.addEventListener?.("change", update)
    return () => query.removeEventListener?.("change", update)
  }, [])

  useLayoutEffect(() => {
    let current: HTMLElement | null = null
    let resizeObserver: ResizeObserver | null = null
    let raf = 0
    const measure = () => {
      const element = document.getElementById(headerTargetId)
      if (element !== current) {
        resizeObserver?.disconnect()
        current = element
        setTarget(element)
        if (element && typeof ResizeObserver !== "undefined") {
          resizeObserver = new ResizeObserver(() => requestAnimationFrame(measure))
          resizeObserver.observe(element)
        }
      }
      const rect = element?.getBoundingClientRect()
      const destination = entered && rect && rect.width > 0 && rect.height > 0
        ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height }
        : centerFrame()
      setFrame(previous => sameFrame(previous, destination) ? previous : destination)
    }
    const schedule = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(measure) }
    measure()
    const mutations = new MutationObserver(schedule)
    mutations.observe(document.body, { childList: true, subtree: true })
    window.addEventListener("resize", schedule)
    window.addEventListener("scroll", schedule, true)
    return () => {
      cancelAnimationFrame(raf)
      resizeObserver?.disconnect()
      mutations.disconnect()
      window.removeEventListener("resize", schedule)
      window.removeEventListener("scroll", schedule, true)
    }
  }, [entered, headerTargetId])

  useEffect(() => {
    if (!moving) { setDocked(false); notified.current = false; return }
    const timer = window.setTimeout(() => setDocked(true), reduced ? 0 : TRANSITION_MS)
    return () => window.clearTimeout(timer)
  }, [moving, reduced])

  useEffect(() => {
    if (docked && !notified.current) { notified.current = true; onDocked?.() }
  }, [docked, onDocked])

  return (
    <div className={`savant-persistent-shell ${className}`} data-loaded={completed} data-entered={entered} data-docked={docked}>
      <div className="savant-persistent-content" aria-hidden={!docked} inert={!docked}>
        {children}
      </div>
      <div className="savant-persistent-veil" aria-hidden="true" />
      <div
        className="savant-persistent-mark"
        data-moving={moving}
        style={frame ? { left: frame.left, top: frame.top, width: frame.width, height: frame.height } : undefined}
      >
        <SavantMark mode="header" state={completed ? "idle" : "thinking"} label="savant" />
      </div>
      {!entered && (
        <div className="savant-persistent-gate" role="status" aria-live="polite">
          {completed ? (
            <button className="savant-persistent-enter" type="button" onClick={() => setEntered(true)}>Enter palaver</button>
          ) : (
            <span className="savant-persistent-status">Loading palaver</span>
          )}
        </div>
      )}
    </div>
  )
}
