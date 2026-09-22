import { useEffect, useState } from "react"

const API =
  import.meta.env.VITE_PALAVER_API_BASE ||
  "http://127.0.0.1:8787"

export function useApi<T>(
  path: string,
  fallback: T,
  interval = 7000
) {
  const [data, setData] = useState<T>(fallback)
  const [error, setError] = useState<string>("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let dead = false

    async function load() {
      try {
        const res = await fetch(API + path)
        if (!res.ok) throw new Error(String(res.status))
        const json = await res.json()
        if (!dead) {
          setData(json)
          setError("")
          setLoading(false)
        }
      } catch (e: any) {
        if (!dead) {
          setError(String(e?.message || e))
          setLoading(false)
        }
      }
    }

    load()
    const id = window.setInterval(load, interval)

    return () => {
      dead = true
      window.clearInterval(id)
    }
  }, [path, interval])

  return { data, error, loading }
}
