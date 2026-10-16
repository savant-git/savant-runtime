export default function Timeline({
  rows=[],
}) {

  return (

    <div className="timeline">

      {
        rows
          .slice()
          .reverse()
          .slice(0,60)
          .map((row,i)=>(

            <div
              key={i}
              className="timeline-row"
            >

              <small>
                {row.timestamp}
              </small>

              <p>
                {row.summary}
              </p>

            </div>

          ))
      }

    </div>

  )

}
