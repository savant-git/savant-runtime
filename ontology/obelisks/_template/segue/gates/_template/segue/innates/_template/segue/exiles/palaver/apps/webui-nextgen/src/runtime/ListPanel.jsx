export default function ListPanel({title, rows=[]}) {
  return (
    <div className="trace">
      <b>{title}</b>
      <pre>{rows.slice(0, 300).join("\n")}</pre>
    </div>
  )
}
