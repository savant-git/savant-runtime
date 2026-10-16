import { useEffect } from "react"
import { Panel, PanelGroup, PanelResizeHandle }
from "react-resizable-panels"

import { motion } from "framer-motion"

import { AmbientField } from "./ambient-field"
import { CommandPalette } from "./command-palette"
import { useWorkspaceStore } from "./workspace-store"

export function CognitiveShell() {

  const {
    active,
    setCommandOpen
  } = useWorkspaceStore()

  useEffect(()=>{
    const fn=(e:KeyboardEvent)=>{
      if((e.metaKey||e.ctrlKey)&&e.key==="k"){
        e.preventDefault()
        setCommandOpen(true)
      }
    }

    window.addEventListener("keydown",fn)
    return ()=>window.removeEventListener("keydown",fn)
  },[])

  return (
    <div className="h-screen w-screen bg-black text-white relative">

      <AmbientField />

      <CommandPalette />

      <PanelGroup direction="horizontal">

        <Panel defaultSize={18}>
          <div className="h-full border-r border-white/10">
            PALAVER
          </div>
        </Panel>

        <PanelResizeHandle />

        <Panel defaultSize={64}>
          <motion.div
            layout
            className="h-full"
          >
            {active}
          </motion.div>
        </Panel>

        <PanelResizeHandle />

        <Panel defaultSize={18}>
          <div className="h-full border-l border-white/10">
            CONTEXT
          </div>
        </Panel>

      </PanelGroup>

    </div>
  )
}
