import React,{Suspense,useRef,useState} from "react"
import {Canvas} from "@react-three/fiber"
import {useGLTF} from "@react-three/drei"
import {ACESFilmicToneMapping,MathUtils} from "three"
import {palaverHybrid} from "./savant-surfaces"
import {MarkScene} from "./savant-scene"
import {SavantMarkBoundary} from "./savant-fallback"
import {useAnimationVisibility,useReducedMotion} from "./savant-visibility"
import type {Interaction,SavantMarkProps} from "./savant-mark-types"
export type {SavantMarkMode,SavantMarkState} from "./savant-mark-types"
import "./savant-mark.css"
import "./savant-hud.css"
import "./savant-studio.css"
const assetUrl="/cinematic/savant_logo.glb",fullTurn=Math.PI*2
export default function SavantMark({
  mode = "header",
  state = "idle",
  className = "",
  label = "savant",
  progress,
  active = true,
  framingScale = 1,
}: SavantMarkProps) {
  const reducedMotion = useReducedMotion()
  const root = useRef<HTMLDivElement>(null)
  const gleamRef = useRef<HTMLDivElement>(null)
  const visible = useAnimationVisibility(root)
  const animationActive = active && visible
  const preset = palaverHybrid
  const interaction = useRef<Interaction>({ yaw: 0, pitch: 0, dragging: false })
  const pointer = useRef<{ id: number; x: number; y: number } | null>(null)
  const [revision, setRevision] = useState(0)
  const requestFrame=useRef<(()=>void)|null>(null)
  const release = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (pointer.current?.id !== event.pointerId) return
    pointer.current = null
    interaction.current.dragging = false
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    setRevision(value => value + 1)
  }
  const progressValue =
    typeof progress ===
      "number"
      ? MathUtils.clamp(
          progress,
          0,
          1,
        )
      : undefined

  return (
    <div
      ref={root}
      className={[
        "savant-mark",
        `savant-mark--${mode}`,
        `savant-mark--${state}`,
        animationActive
          ? "is-active"
          : "is-resting",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      data-savant-state={
        state
      }
      role={mode === "preloader" ? "status" : "group"}
      aria-label={
        mode ===
        "preloader"
          ? `${label} loading`
          : label
      }
    >


      <div ref={gleamRef} aria-hidden="true" style={{display:"none"}} />
      <button type="button" className="savant-mark__drag" style={{touchAction:"none"}}
        aria-label="Rotate savant logo. Drag or use arrow keys; release to resume rotation."
        title="Drag to rotate · arrow keys to turn · Home to reset"
        onPointerDown={event => {
          if (event.button !== 0 || pointer.current) return
          event.stopPropagation()
          pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY }
          interaction.current.dragging = true
          event.currentTarget.setPointerCapture(event.pointerId)
          setRevision(value => value + 1)
        }}
        onPointerMove={event => {
          const last = pointer.current
          if (!last || last.id !== event.pointerId) return
          const scale = fullTurn / Math.max(event.currentTarget.clientWidth * 2, 1)
          interaction.current.yaw += (event.clientX - last.x) * scale
          interaction.current.pitch = MathUtils.clamp(interaction.current.pitch +
            (event.clientY - last.y) * scale, -.65, .65)
          last.x = event.clientX; last.y = event.clientY
          requestFrame.current?.()
        }}
        onPointerUp={release} onPointerCancel={release} onLostPointerCapture={release}
        onKeyDown={event => {
          const changes: Record<string, [number, number]> = {
            ArrowLeft: [-.15, 0], ArrowRight: [.15, 0],
            ArrowUp: [0, -.12], ArrowDown: [0, .12],
          }
          if (event.key === "Home") {
            interaction.current.yaw = 0; interaction.current.pitch = 0
          } else if (changes[event.key]) {
            interaction.current.yaw += changes[event.key][0]
            interaction.current.pitch = MathUtils.clamp(interaction.current.pitch +
              changes[event.key][1], -.65, .65)
          } else return
          event.preventDefault()
          setRevision(value => value + 1)
        }} />


      <div
        className="savant-mark__viewport"
      >
        <SavantMarkBoundary
          mode={mode}
        >
          <Canvas
            frameloop="demand"
            shadows={false}
            dpr={[1, 2]}
            gl={{
              alpha: true,
              antialias: true,
              powerPreference:
                "high-performance",
            }}
            camera={{
              position: [
                0,
                0,
                3.15,
              ],
              fov: 31,
              near: 0.1,
              far: 20,
            }}
            onCreated={({
              gl,
            }) => {
              gl.setClearColor(0x000000, 0)
              gl.toneMapping = ACESFilmicToneMapping
              gl.toneMappingExposure = .95
            }}
          >
            <Suspense
              fallback={null}
            >
              <MarkScene
                mode={mode}
                state={state}
                preset={preset}
                interaction={interaction}
                revision={revision}
                requestFrame={requestFrame}
                gleamRef={gleamRef}
                framingScale={framingScale}
                active={animationActive}
                reducedMotion={
                  reducedMotion
                }
              />
            </Suspense>
          </Canvas>
        </SavantMarkBoundary>
      </div>



      {mode ===
        "preloader" && (
        <div
          className="savant-mark__preloader-copy"
        >
          <span>
            {label}
          </span>

          <span
            className="savant-mark__preloader-state"
          >
            {state}
          </span>

          {progressValue !==
            undefined && (
            <div
              className="savant-mark__progress"
              aria-hidden="true"
            >
              <i
                style={{
                  transform:
                    `scaleX(${progressValue})`,
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}


useGLTF.preload(
  assetUrl,
)
