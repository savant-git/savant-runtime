import { useMemo, useState } from "react"

export default function MemoryExplorer({
  files = [],
}) {

  const [query,setQuery] =
    useState("")

  const results =
    useMemo(() => {

      if (!query.trim())
        return []

      const q =
        query.toLowerCase()

      return files
        .filter(
          x =>
            x.toLowerCase()
             .includes(q)
        )
        .slice(0,100)

    }, [files, query])

  return (
    <div className="memory-explorer">

      <input
        value={query}
        onChange={e=>
          setQuery(
            e.target.value
          )
        }
        placeholder="Search memory..."
      />

      <div className="memory-results">

        {
          results.map(row => (
            <div
              key={row}
              className="memory-row"
            >
              {row}
            </div>
          ))
        }

      </div>

    </div>
  )
}
