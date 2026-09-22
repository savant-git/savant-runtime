export default function CommandCenter(){

  const commands = [
    "health",
    "graph",
    "timeline",
    "repository report",
    "patches",
    "memory",
    "agents",
    "workspace",
  ]

  return (
    <div className="trace">
      <b>COMMAND CENTER</b>

      <div
        style={{
          display:"grid",
          gridTemplateColumns:
            "repeat(2,1fr)",
          gap:"8px",
          marginTop:"12px",
        }}
      >
        {
          commands.map(cmd=>(
            <button
              key={cmd}
            >
              {cmd}
            </button>
          ))
        }
      </div>
    </div>
  )
}
