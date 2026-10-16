import { Command } from "cmdk"
import { useWorkspaceStore } from "./workspace-store"

export function CommandPalette() {

  const {
    commandOpen,
    setCommandOpen,
    setActive
  } = useWorkspaceStore()

  if(!commandOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/50">
      <Command className="mx-auto mt-32 max-w-2xl rounded-xl border bg-black">
        <Command.Input placeholder="Navigate..." />
        <Command.List>

          {[
            "graph",
            "authority",
            "repository",
            "memory",
            "runtime",
            "ontology"
          ].map(item=>(
            <Command.Item
              key={item}
              onSelect={()=>{
                setActive(item as any)
                setCommandOpen(false)
              }}
            >
              {item}
            </Command.Item>
          ))}

        </Command.List>
      </Command>
    </div>
  )
}
