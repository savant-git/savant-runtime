import React, { useEffect, useLayoutEffect, useRef, useState } from "react"
import SavantMark from "./savant-mark"
import "./savant-persistent-loader.css"

type Props = {
  ready: boolean
  children: React.ReactNode
  headerTargetId?: string
  minimumLoadingMs?: number
  className?: string
}

type Frame = { left: number; top: number; width: number; height: number }
const centered = (): Frame => {
  const width = Math.min(Math.max(window.innerWidth * 0.54, 180), 360, window.innerWidth - 32)
  const height = width
  return { left: (window.innerWidth - width) / 2, top: (window.innerHeight - height) / 2, width, height }
}

/** Keep one WebGL scene mounted while its containing frame moves into the header. */
export default function SavantPersistentLoader({
  ready, children, headerTargetId = "savant-header-logo-slot",
  minimumLoadingMs = 9500, className = "",
}: Props) {
  const [elapsed, setElapsed] = useState(minimumLoadingMs <= 0)
  const [settled, setSettled] = useState(false)
  const [frame, setFrame] = useState<Frame | null>(null)
  const [motionReduced, setMotionReduced] = useState(false)
  const initial = useRef<number>(Date.now())
  const frameRef = useRef<HTMLDivElement>(null)
  const targetRef = useRef<HTMLElement | null>(null)
  const completed = ready && elapsed

  useEffect(() => {
    const remaining = Math.max(0, minimumLoadingMs - (Date.now() - initial.current))
    const timeout = window.setTimeout(() => setElapsed(true), remaining)
    return () => window.clearTimeout(timeout)
  }, [minimumLoadingMs])

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setMotionReduced(media.matches)
    update()
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [])

  useLayoutEffect(() => {
    const target = document.getElementById(headerTargetId)
    targetRef.current = target
    const measure = () => {
      const element = targetRef.current
      if (completed && element) {
        const rect = element.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          setFrame({ left: rect.left, top: rect.top, width: rect.width, height: rect.height })
          return
        }
      }
      setFrame(centered())
    }
    measure()
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure)
    if (target) observer?.observe(target)
    window.addEventListener("resize", measure)
    window.addEventListener("scroll", measure, true)
    return () => {
      observer?.disconnect()
      window.removeEventListener("resize", measure)
      window.removeEventListener("scroll", measure, true)
    }
  }, [completed, headerTargetId])

  useEffect(() => {
    if (!completed) { setSettled(false); return }
    if (motionReduced) { setSettled(true); return }
    const timer = window.setTimeout(() => setSettled(true), 950)
    return () => window.clearTimeout(timer)
  }, [completed, motionReduced])

  return (
    <div className={`savant-persistent-shell ${className}`} data-loaded={completed}>
      <div className="savant-persistent-content" aria-hidden={!completed} inert={!completed}>
        {children}
      </div>
      {!settled && <div className="savant-persistent-veil" aria-hidden="true" />}
      <div
        ref={frameRef}
        className="savant-persistent-mark"
        data-docked={completed}
        style={frame ? {
          left: frame.left, top: frame.top, width: frame.width, height: frame.height,
        } : undefined}
      >
        <SavantMark mode="header" state={completed ? "idle" : "thinking"} label="savant" />
      </div>
      {!completed && <div className="savant-persistent-status" role="status" aria-live="polite">Loading palaver</div>}
    </div>
  )
}
