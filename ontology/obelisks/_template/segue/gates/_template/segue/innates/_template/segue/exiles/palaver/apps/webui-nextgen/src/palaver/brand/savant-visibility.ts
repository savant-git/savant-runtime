import {useEffect,useState} from "react"
import type React from "react"
export function useAnimationVisibility(root: React.RefObject<HTMLDivElement | null>) {
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    let intersects = true
    const update = () => setVisible(intersects && !document.hidden)
    const observer = typeof IntersectionObserver === "undefined" ? null :
      new IntersectionObserver(entries => {
        intersects = entries.some(entry => entry.isIntersecting)
        update()
      })
    if (root.current) observer?.observe(root.current)
    document.addEventListener("visibilitychange", update)
    update()
    return () => {
      observer?.disconnect()
      document.removeEventListener("visibilitychange", update)
    }
  }, [root])
  return visible
}

export function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(
    () => typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  )
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setReducedMotion(query.matches)
    update()
    query.addEventListener("change", update)
    return () => query.removeEventListener("change", update)
  }, [])
  return reducedMotion
}
