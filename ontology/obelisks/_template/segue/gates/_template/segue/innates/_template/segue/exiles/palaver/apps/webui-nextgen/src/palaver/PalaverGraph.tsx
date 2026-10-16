import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  Focus,
  Minus,
  Plus,
  RotateCcw,
} from "lucide-react"
import {
  PointerEvent,
  WheelEvent,
  useMemo,
  useRef,
  useState,
} from "react"

type GraphNode = {
  id: string
  label?: string
  type?: string
  group?: string
  metadata?: Record<string, unknown>
}

type GraphEdge = {
  source: string
  target: string
  relation?: string
  type?: string
}

type GraphPayload = {
  nodes?: GraphNode[]
  edges?: GraphEdge[]
}

type PositionedNode =
  GraphNode & {
    x: number
    y: number
  }

type Props = {
  data: unknown
  onAsk: (
    prompt: string,
  ) => void
}

function normalize(
  value: unknown,
): GraphPayload {
  if (
    !value ||
    typeof value !== "object"
  ) {
    return {}
  }

  const record =
    value as Record<
      string,
      unknown
    >

  const nodes =
    Array.isArray(record.nodes)
      ? record.nodes.filter(
          (
            item,
          ): item is GraphNode =>
            Boolean(
              item &&
                typeof item ===
                  "object" &&
                "id" in item &&
                typeof (
                  item as GraphNode
                ).id === "string",
            ),
        )
      : []

  const edges =
    Array.isArray(record.edges)
      ? record.edges.filter(
          (
            item,
          ): item is GraphEdge =>
            Boolean(
              item &&
                typeof item ===
                  "object" &&
                "source" in item &&
                "target" in item &&
                typeof (
                  item as GraphEdge
                ).source ===
                  "string" &&
                typeof (
                  item as GraphEdge
                ).target ===
                  "string",
            ),
        )
      : []

  return {
    nodes,
    edges,
  }
}

function hash(
  text: string,
) {
  let value = 2166136261

  for (
    let index = 0;
    index < text.length;
    index += 1
  ) {
    value ^= text.charCodeAt(
      index,
    )

    value = Math.imul(
      value,
      16777619,
    )
  }

  return value >>> 0
}

function layout(
  nodes: GraphNode[],
) {
  if (!nodes.length) {
    return []
  }

  const ordered = [
    ...nodes,
  ].sort(
    (left, right) =>
      left.id.localeCompare(
        right.id,
      ),
  )

  const total =
    ordered.length

  const golden =
    Math.PI *
    (3 - Math.sqrt(5))

  return ordered.map(
    (
      node,
      index,
    ): PositionedNode => {
      const normalized =
        total === 1
          ? 0
          : index /
            (total - 1)

      const radius =
        90 +
        normalized * 330

      const angle =
        index * golden +
        (hash(node.id) %
          628) /
          100

      return {
        ...node,
        x:
          Math.cos(angle) *
          radius,
        y:
          Math.sin(angle) *
          radius,
      }
    },
  )
}

export default function PalaverGraph({
  data,
  onAsk,
}: Props) {
  const reducedMotion =
    useReducedMotion()

  const payload =
    useMemo(
      () => normalize(data),
      [data],
    )

  const nodes =
    useMemo(
      () =>
        layout(
          payload.nodes ?? [],
        ),
      [payload.nodes],
    )

  const nodeMap =
    useMemo(
      () =>
        new Map(
          nodes.map((node) => [
            node.id,
            node,
          ]),
        ),
      [nodes],
    )

  const [selected, setSelected] =
    useState<string | null>(
      null,
    )

  const [scale, setScale] =
    useState(1)

  const [offset, setOffset] =
    useState({
      x: 0,
      y: 0,
    })

  const dragRef = useRef<{
    x: number
    y: number
    originX: number
    originY: number
  } | null>(null)

  const selectedNode =
    selected
      ? nodeMap.get(selected)
      : undefined

  const zoom = (
    amount: number,
  ) => {
    setScale((current) =>
      Math.min(
        2.8,
        Math.max(
          0.35,
          current + amount,
        ),
      ),
    )
  }

  const reset = () => {
    setScale(1)
    setOffset({
      x: 0,
      y: 0,
    })
    setSelected(null)
  }

  const onWheel = (
    event: WheelEvent,
  ) => {
    event.preventDefault()

    zoom(
      event.deltaY > 0
        ? -0.12
        : 0.12,
    )
  }

  const onPointerDown = (
    event: PointerEvent,
  ) => {
    if (
      (
        event.target as HTMLElement
      ).closest(
        "[data-graph-node]",
      )
    ) {
      return
    }

    dragRef.current = {
      x: event.clientX,
      y: event.clientY,
      originX: offset.x,
      originY: offset.y,
    }

    event.currentTarget.setPointerCapture(
      event.pointerId,
    )
  }

  const onPointerMove = (
    event: PointerEvent,
  ) => {
    const drag =
      dragRef.current

    if (!drag) {
      return
    }

    setOffset({
      x:
        drag.originX +
        event.clientX -
        drag.x,
      y:
        drag.originY +
        event.clientY -
        drag.y,
    })
  }

  const onPointerUp = (
    event: PointerEvent,
  ) => {
    dragRef.current = null

    if (
      event.currentTarget.hasPointerCapture(
        event.pointerId,
      )
    ) {
      event.currentTarget.releasePointerCapture(
        event.pointerId,
      )
    }
  }

  if (!nodes.length) {
    return (
      <div className="palaver-graph-empty">
        No graph nodes were returned.
      </div>
    )
  }

  return (
    <div
      className="palaver-graph"
      onWheel={onWheel}
      onPointerDown={
        onPointerDown
      }
      onPointerMove={
        onPointerMove
      }
      onPointerUp={
        onPointerUp
      }
      onPointerCancel={
        onPointerUp
      }
    >
      <div className="palaver-graph-controls">
        <button
          onClick={() =>
            zoom(0.18)
          }
          aria-label="Zoom graph in"
        >
          <Plus size={16} />
        </button>

        <button
          onClick={() =>
            zoom(-0.18)
          }
          aria-label="Zoom graph out"
        >
          <Minus size={16} />
        </button>

        <button
          onClick={reset}
          aria-label="Reset graph"
        >
          <RotateCcw
            size={15}
          />
        </button>
      </div>

      <div className="palaver-graph-counter">
        <strong>
          {nodes.length}
        </strong>
        <span>nodes</span>

        <strong>
          {
            payload.edges
              ?.length ?? 0
          }
        </strong>
        <span>edges</span>
      </div>

      <motion.div
        className="palaver-graph-world"
        animate={{
          x: offset.x,
          y: offset.y,
          scale,
        }}
        transition={
          reducedMotion
            ? {
                duration: 0,
              }
            : {
                type: "spring",
                stiffness: 280,
                damping: 34,
              }
        }
      >
        <svg
          className="palaver-graph-lines"
          viewBox="-500 -500 1000 1000"
          preserveAspectRatio="xMidYMid meet"
        >
          {(payload.edges ?? []).map(
            (
              edge,
              index,
            ) => {
              const source =
                nodeMap.get(
                  edge.source,
                )

              const target =
                nodeMap.get(
                  edge.target,
                )

              if (
                !source ||
                !target
              ) {
                return null
              }

              const emphasized =
                selected &&
                (
                  source.id ===
                    selected ||
                  target.id ===
                    selected
                )

              return (
                <line
                  key={`${edge.source}:${edge.target}:${index}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  className={
                    emphasized
                      ? "active"
                      : ""
                  }
                />
              )
            },
          )}
        </svg>

        {nodes.map(
          (
            node,
            index,
          ) => {
            const active =
              selected ===
              node.id

            return (
              <motion.button
                key={node.id}
                data-graph-node
                className={[
                  "palaver-graph-node",
                  active
                    ? "active"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                style={{
                  left:
                    `calc(50% + ${node.x}px)`,
                  top:
                    `calc(50% + ${node.y}px)`,
                }}
                initial={
                  reducedMotion
                    ? false
                    : {
                        opacity: 0,
                        scale: 0.6,
                      }
                }
                animate={{
                  opacity: 1,
                  scale: active
                    ? 1.2
                    : 1,
                }}
                transition={{
                  delay:
                    reducedMotion
                      ? 0
                      : Math.min(
                          index *
                            0.008,
                          0.5,
                        ),
                }}
                onClick={() =>
                  setSelected(
                    active
                      ? null
                      : node.id,
                  )
                }
              >
                <i />

                <span>
                  {node.label ??
                    node.id}
                </span>
              </motion.button>
            )
          },
        )}
      </motion.div>

      <AnimatePresence>
        {selectedNode && (
          <motion.div
            className="palaver-graph-inspector"
            initial={{
              opacity: 0,
              y: 15,
            }}
            animate={{
              opacity: 1,
              y: 0,
            }}
            exit={{
              opacity: 0,
              y: 10,
            }}
          >
            <header>
              <Focus size={15} />
              <span>
                selected
              </span>
            </header>

            <strong>
              {selectedNode.label ??
                selectedNode.id}
            </strong>

            <small>
              {selectedNode.type ??
                selectedNode.group ??
                "graph node"}
            </small>

            <button
              onClick={() =>
                onAsk(
                  `Explain the SAVANT graph node "${selectedNode.id}", what connects to it, why those relationships matter, and whether anything requires attention.`,
                )
              }
            >
              ask palaver
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
