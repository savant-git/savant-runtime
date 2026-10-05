export default function DiffViewer({
  diff=""
}){

  return (

    <pre
      style={{
        margin:0,
        padding:"16px",
        overflow:"auto",
        height:"100%",
        fontSize:"12px",
        fontFamily:
          "monospace",
      }}
    >
      {diff}
    </pre>

  )
}
