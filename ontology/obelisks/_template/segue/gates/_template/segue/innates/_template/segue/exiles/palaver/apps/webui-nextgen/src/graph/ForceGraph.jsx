import { useEffect, useRef } from "react"
import * as d3 from "d3"

export default function ForceGraph({
  graph
}){

  const ref = useRef()

  useEffect(()=>{

    if(
      !graph ||
      !ref.current
    ) return

    const svg =
      d3.select(ref.current)

    svg.selectAll("*")
      .remove()

    const width = 900
    const height = 700

    svg
      .attr(
        "viewBox",
        [0,0,width,height]
      )

    const nodes =
      [...(graph.nodes||[])]

    const links =
      [...(graph.edges||[])]

    const sim =
      d3.forceSimulation(nodes)
        .force(
          "link",
          d3.forceLink(links)
            .id(d=>d.id)
            .distance(80)
        )
        .force(
          "charge",
          d3.forceManyBody()
            .strength(-120)
        )
        .force(
          "center",
          d3.forceCenter(
            width/2,
            height/2
          )
        )

    const link =
      svg.append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")

    const node =
      svg.append("g")
        .selectAll("circle")
        .data(nodes)
        .enter()
        .append("circle")
        .attr("r",3)

    sim.on("tick",()=>{

      link
        .attr("x1",d=>d.source.x)
        .attr("y1",d=>d.source.y)
        .attr("x2",d=>d.target.x)
        .attr("y2",d=>d.target.y)

      node
        .attr("cx",d=>d.x)
        .attr("cy",d=>d.y)

    })

  },[graph])

  return (
    <svg
      ref={ref}
      style={{
        width:"100%",
        height:"100%",
      }}
    />
  )
}
