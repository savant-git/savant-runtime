import type React from "react"
import type {MaterialPreset} from "./savant-surfaces"
export type SavantMarkMode = "header" | "preloader"
export type SavantMarkState =
  | "idle" | "thinking" | "streaming" | "tool"
  | "complete" | "degraded" | "failure"

export type SavantMarkProps = {
  mode?: SavantMarkMode
  state?: SavantMarkState
  className?: string
  label?: string
  progress?: number
  active?: boolean
  controls?: boolean
  controlsTarget?: HTMLElement | null
  framingScale?: number
}

export type MarkSceneProps = {
  mode: SavantMarkMode
  state: SavantMarkState
  active: boolean
  preset: MaterialPreset
  interaction: React.MutableRefObject<Interaction>
  revision: number
  requestFrame: React.MutableRefObject<(()=>void)|null>
  reducedMotion: boolean
  gleamRef: React.RefObject<HTMLDivElement | null>
  framingScale: number
}


export type Interaction = { yaw: number; pitch: number; dragging: boolean }
