export default function RuntimePanel({data}) {
  if (!data) return null

  return (
    <div className="trace">
      <b>RUNTIME</b>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  )
}
