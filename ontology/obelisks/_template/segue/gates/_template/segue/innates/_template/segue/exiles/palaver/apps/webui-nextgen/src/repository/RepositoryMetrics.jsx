import { useEffect, useState } from "react"

const API =
  "http://127.0.0.1:8787"

export default function RepositoryMetrics(){

  const [count,setCount] =
    useState(0)

  useEffect(()=>{

    fetch(
      API +
      "/api/repository/files"
    )
      .then(r=>r.json())
      .then(data=>{

        setCount(
          (
            data.files ||
            []
          ).length
        )

      })

  },[])

  return (

    <div
      className="trace"
    >

      <b>
        Repository
      </b>

      <h2>
        {
          count
            .toLocaleString()
        }
      </h2>

      <small>
        indexed files
      </small>

    </div>

  )
}
