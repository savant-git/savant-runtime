import { useState } from "react"
import Editor from "@monaco-editor/react"

export default function EditorWorkspace({

  path,
  content="",

  onSave,
  onDiff,

}){

  const [value,setValue] =
    useState(content)

  return (

    <div
      style={{
        height:"100%",
        display:"flex",
        flexDirection:"column",
      }}
    >

      <div
        style={{
          display:"flex",
          gap:"8px",
          padding:"8px",
          borderBottom:
            "1px solid rgba(255,255,255,.08)",
        }}
      >

        <button
          onClick={()=>
            onSave?.(
              path,
              value
            )
          }
        >
          Save
        </button>

        <button
          onClick={()=>
            onDiff?.(
              path,
              value
            )
          }
        >
          Diff
        </button>

        <div>
          {path}
        </div>

      </div>

      <div
        style={{
          flex:1,
        }}
      >

        <Editor
          theme="vs-dark"
          defaultLanguage="python"
          value={value}
          onChange={(v)=>
            setValue(v || "")
          }
        />

      </div>

    </div>
  )
}
