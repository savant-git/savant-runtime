import { useMemo, useState } from "react"

export default function RepositorySearch({
  files = [],
  openFile,
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
    <div className="repo-search">

      <input
        value={query}
        onChange={e=>
          setQuery(
            e.target.value
          )
        }
        placeholder="Search repository..."
      />

      <div className="repo-results">
        {
          results.map(file => (
            <button
              key={file}
              onClick={()=>
                openFile(file)
              }
            >
              {file}
            </button>
          ))
        }
      </div>

    </div>
  )
}
