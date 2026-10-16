import { create } from "zustand"

export type Surface =
  | "authority"
  | "graph"
  | "repository"
  | "memory"
  | "runtime"
  | "ontology"

type State = {
  active: Surface
  commandOpen: boolean
  setActive: (s: Surface) => void
  setCommandOpen: (v: boolean) => void
}

export const useWorkspaceStore =
create<State>((set)=>({
  active:"graph",
  commandOpen:false,
  setActive:(active)=>set({active}),
  setCommandOpen:(commandOpen)=>set({commandOpen})
}))
