import { useEffect } from "react"
import {
  loadWorkspace,
  saveWorkspace,
} from "./workspaceStore"

export default function WorkspaceManager({
  state,
  setState,
}) {

  useEffect(() => {
    const existing =
      loadWorkspace()

    setState(existing)
  }, [])

  useEffect(() => {
    saveWorkspace(state)
  }, [state])

  return null
}
