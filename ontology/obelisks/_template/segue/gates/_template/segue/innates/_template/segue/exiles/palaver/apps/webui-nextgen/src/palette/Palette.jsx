import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"

export default function Palette({ open, close, send }) {
  const [value, setValue] = useState("")

  function run(v = value) {
    if (!v.trim()) return

    close()
    send(v.trim())
    setValue("")
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="palette-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={close}
        >
          <motion.div
            className="palette"
            initial={{ opacity: 0, y: 28, scale: .96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: .96 }}
            onClick={e => e.stopPropagation()}
          >
            <input
              autoFocus
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") run()
              }}
              placeholder="Command palette — ask, inspect, build, patch"
            />

            <div className="quick">
              {[
                "health",
                "files",
                "graph",
                "patches",
                "repository report",
                "file read runtime/core.py",
              ].map(x => (
                <button key={x} onClick={() => run(x)}>
                  {x}
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
