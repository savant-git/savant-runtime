export default function RuntimeMetrics(){

  return (
    <div className="trace">

      <b>RUNTIME</b>

      <div
        style={{
          display:"grid",
          gridTemplateColumns:
            "repeat(2,1fr)",
          gap:"12px",
          marginTop:"12px",
        }}
      >

        <div>
          <small>Repository</small>
          <h3>237,689</h3>
        </div>

        <div>
          <small>Nodes</small>
          <h3>666</h3>
        </div>

        <div>
          <small>Edges</small>
          <h3>3,339</h3>
        </div>

        <div>
          <small>Status</small>
          <h3>ONLINE</h3>
        </div>

      </div>

    </div>
  )
}
