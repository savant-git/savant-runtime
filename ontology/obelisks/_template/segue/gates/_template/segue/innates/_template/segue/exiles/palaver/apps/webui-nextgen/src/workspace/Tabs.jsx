export default function Tabs(
{
  tabs=[],
  active,
  onSelect,
}){

  return (
    <div
      style={{
        display:"flex",
        gap:"8px",
        padding:"8px",
      }}
    >
      {
        tabs.map(tab=>(
          <button
            key={tab.id}
            onClick={()=>
              onSelect(
                tab.id
              )
            }
          >
            {tab.title}
          </button>
        ))
      }
    </div>
  )
}
