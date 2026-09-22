export default function WorkstationGrid({
  left,
  center,
  right,
}){

  return (

    <div
      style={{
        display:"grid",
        gridTemplateColumns:
          "320px 1fr 420px",
        gap:"16px",
        height:"100%",
      }}
    >

      <div>{left}</div>

      <div>{center}</div>

      <div>{right}</div>

    </div>

  )
}
