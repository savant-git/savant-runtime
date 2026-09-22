import { useEffect, useRef, useState } from "react"
import Graph from "graphology"
import Sigma from "sigma"
import { getJson } from "../api/client"

type NodeRow = {
  id?: string
  label?: string
  kind?: string
  size?: number
  x?: number
  y?: number
}

type EdgeRow = {
  source?: string
  target?: string
  kind?: string
  weight?: number
}

type Payload = {
  nodes?: NodeRow[]
  edges?: EdgeRow[]
}

function fallback(): Payload {
  return {
    nodes: [
      { id: "authority", label: "Authority", kind: "authority", size: 18 },
      { id: "lineage", label: "Lineage", kind: "lineage", size: 13 },
      { id: "dependency", label: "Dependency", kind: "dependency", size: 13 },
      { id: "relationship", label: "Relationship", kind: "relationship", size: 12 },
      { id: "memory", label: "Memory", kind: "memory", size: 11 },
      { id: "ontology", label: "Ontology", kind: "ontology", size: 11 }
    ],
    edges: [
      { source: "authority", target: "lineage", kind: "governs" },
      { source: "authority", target: "dependency", kind: "stabilizes" },
      { source: "dependency", target: "relationship", kind: "pressurizes" },
      { source: "memory", target: "ontology", kind: "informs" },
      { source: "ontology", target: "authority", kind: "anchors" }
    ]
  }
}

function colorFor(kind = "") {
  if (kind.includes("authority")) return "#f2e5c4"
  if (kind.includes("dependency")) return "#ff9f7a"
  if (kind.includes("lineage")) return "#a8c7ff"
  if (kind.includes("memory")) return "#b7f7d4"
  if (kind.includes("ontology")) return "#d6b4ff"
  return "#ffffff"
}

export default function GraphObservatory() {
  const ref = useRef<HTMLDivElement>(null)
  const [summary, setSummary] = useState({
    nodes: 0,
    edges: 0
  })

  useEffect(() => {
    let sigma: Sigma | null = null
    let dead = false

    async function run() {
      const payload =
        (await getJson<Payload>("/api/personality/graph")) ||
        (await getJson<Payload>("/api/authority/relationships")) ||
        (await getJson<Payload>("/api/graph")) ||
        fallback()

      if (dead || !ref.current) return

      const graph = new Graph()
      const nodes = payload.nodes || fallback().nodes || []
      const edges = payload.edges || fallback().edges || []

      nodes.forEach((node, index) => {
        const id = String(node.id || node.label || `node_${index}`)
        const angle =
          (index / Math.max(nodes.length, 1)) * Math.PI * 2
        const ring = 1 + (index % 4)

        graph.addNode(id, {
          x: node.x ?? Math.cos(angle) * ring,
          y: node.y ?? Math.sin(angle) * ring,
          size: node.size ?? 8,
          label: node.label || id,
          color: colorFor(node.kind)
        })
      })

      edges.forEach((edge, index) => {
        const source = String(edge.source || "")
        const target = String(edge.target || "")
        if (!source || !target) return
        if (!graph.hasNode(source) || !graph.hasNode(target)) return

        graph.addDirectedEdgeWithKey(
          `${source}->${target}:${index}`,
          source,
          target,
          {
            label: edge.kind || "relates",
            size: Math.max(1, Number(edge.weight || 1)),
            color: "rgba(255,255,255,.25)"
          }
        )
      })

      sigma = new Sigma(graph, ref.current, {
        renderEdgeLabels: false,
        allowInvalidContainer: true
      })

      setSummary({
        nodes: graph.order,
        edges: graph.size
      })
    }

    run()

    return () => {
      dead = true
      if (sigma) sigma.kill()
    }
  }, [])

  return (
    <section className="graph-observatory">
      <div className="graph-hud">
        <div>
          <p>graph-native observatory</p>
          <h1>Knowledge Terrain</h1>
        </div>

        <div className="graph-stats">
          <span>{summary.nodes} nodes</span>
          <span>{summary.edges} edges</span>
        </div>
      </div>

      <div className="graph-canvas" ref={ref} />

      <div className="graph-legend">
        <span>authority</span>
        <span>lineage</span>
        <span>dependency</span>
        <span>memory</span>
        <span>ontology</span>
      </div>
    </section>
  )
}
