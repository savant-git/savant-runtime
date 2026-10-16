import { Canvas, useFrame } from "@react-three/fiber"
import { useEffect, useMemo, useRef, useState } from "react"
import { IcosahedronGeometry, EdgesGeometry, LineSegments } from "three"

function Topology({ motion, pointer }: { motion: boolean; pointer: React.RefObject<{ x: number; y: number }> }) {
  const ref = useRef<LineSegments>(null)
  const geometry = useMemo(() => new IcosahedronGeometry(2.5, 3), [])
  const edges = useMemo(() => new EdgesGeometry(geometry), [geometry])
  useEffect(() => () => { edges.dispose(); geometry.dispose() }, [edges, geometry])
  useFrame(({ clock }, delta) => {
    if (!ref.current || !motion) return
    const ease = Math.min(1, delta * 2.8)
    const targetY = clock.elapsedTime * .02 + pointer.current.x * .15
    const targetX = clock.elapsedTime * .01 - pointer.current.y * .12
    ref.current.rotation.y += (targetY - ref.current.rotation.y) * ease
    ref.current.rotation.x += (targetX - ref.current.rotation.x) * ease
  })
  return <lineSegments ref={ref}>
    <primitive object={edges} attach="geometry" dispose={null} />
    <lineBasicMaterial color="#76b4a7" transparent opacity={.075} depthWrite={false} />
  </lineSegments>
}

export default function TopologyField() {
  const [motion, setMotion] = useState(false)
  const [visible, setVisible] = useState(true)
  const host = useRef<HTMLDivElement>(null)
  const pointer = useRef({ x: 0, y: 0 })
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setMotion(!query.matches)
    update(); query.addEventListener("change", update)
    return () => query.removeEventListener("change", update)
  }, [])
  useEffect(() => {
    if (!host.current || typeof IntersectionObserver === "undefined") return
    const observer = new IntersectionObserver(entries => setVisible(entries[0]?.isIntersecting ?? true), { threshold: 0 })
    observer.observe(host.current)
    return () => observer.disconnect()
  }, [])
  useEffect(() => {
    const element = host.current
    if (!element) return
    const move = (event: PointerEvent) => {
      const rect = element.getBoundingClientRect()
      if (!rect.width || !rect.height) return
      pointer.current.x = Math.max(-1, Math.min(1, ((event.clientX - rect.left) / rect.width) * 2 - 1))
      pointer.current.y = Math.max(-1, Math.min(1, ((event.clientY - rect.top) / rect.height) * 2 - 1))
    }
    const reset = () => { pointer.current.x = 0; pointer.current.y = 0 }
    element.addEventListener("pointermove", move, { passive: true })
    element.addEventListener("pointerleave", reset)
    return () => { element.removeEventListener("pointermove", move); element.removeEventListener("pointerleave", reset) }
  }, [])
  return <div ref={host} className="savant-topology-field" aria-hidden="true">
    <Canvas camera={{ position: [0, 0, 6] }} frameloop={motion && visible ? "always" : "demand"}
      dpr={[1, Math.min(1.5, typeof window === "undefined" ? 1 : window.devicePixelRatio || 1)]}
      gl={{ antialias: false, alpha: true, powerPreference: "low-power" }}>
      <Topology motion={motion && visible} pointer={pointer} />
    </Canvas>
  </div>
}
