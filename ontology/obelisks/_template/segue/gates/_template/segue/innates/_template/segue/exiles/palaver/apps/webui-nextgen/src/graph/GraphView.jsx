export default function GraphView({
  graph,
}) {

  const nodes =
    (graph?.nodes || [])
      .slice(0,90)

  const edges =
    (graph?.edges || [])
      .slice(0,220)

  const points =
    nodes.map((n,i)=>{

      const a =
        (i /
        Math.max(
          nodes.length,
          1
        )) *
        Math.PI *
        2

      return {
        id:n.id,
        x:50+Math.cos(a)*34,
        y:50+Math.sin(a)*34,
      }

    })

  return (
    <div className="graph-wrap">

      <svg viewBox="0 0 100 100">

        {
          edges.map((e,i)=>{

            const a =
              points[
                i %
                Math.max(
                  points.length,
                  1
                )
              ]

            const b =
              points[
                (i*7) %
                Math.max(
                  points.length,
                  1
                )
              ]

            if(!a || !b)
              return null

            return (
              <line
                key={i}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
              />
            )

          })
        }

        {
          points.map((p,i)=>
            <circle
              key={p.id || i}
              cx={p.x}
              cy={p.y}
              r="0.75"
            />
          )
        }

      </svg>

      <div className="graph-meta">
        <strong>
          {graph?.node_count || nodes.length}
        </strong>
        {" "}nodes

        <strong>
          {graph?.edge_count || edges.length}
        </strong>
        {" "}edges
      </div>

    </div>
  )

}
