export default function TopBar({
  status,
  loadTree,
  loadGraph,
  openPalette,
  send,
}) {
  return (
    <header className="top">
      <div className="brand">
        <div className="logo">§</div>

        <div>
          <h1>PALAVER</h1>
          <p>persistent AI workstation / runtime builder / server cockpit</p>
        </div>
      </div>

      <nav>
        <button className="active">Chat</button>
        <button onClick={loadTree}>Files</button>
        <button onClick={loadGraph}>Graph</button>
        <button onClick={() => send("patches")}>Patches</button>
        <button onClick={openPalette}>Palette</button>
      </nav>

      <div className="status">
        <span className="dot" />
        {status}
      </div>
    </header>
  )
}
