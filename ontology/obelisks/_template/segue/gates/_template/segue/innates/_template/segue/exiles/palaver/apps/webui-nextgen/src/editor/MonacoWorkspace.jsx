import Editor
from "@monaco-editor/react"

export default function MonacoWorkspace(
{
  path,
  content,
}){

  return (
    <Editor
      height="100%"
      defaultLanguage="python"
      theme="vs-dark"
      value={content}
      options={{
        minimap:{
          enabled:true
        },
        smoothScrolling:true,
        fontSize:13,
      }}
    />
  )
}
