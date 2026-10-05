export default function Composer({
  input,
  setInput,
  submit,
  openPalette,
}) {
  return (
    <div className="composer">
      <textarea
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
        placeholder="Ask Palaver anything..."
      />

      <button onClick={openPalette}>⌘</button>
      <button className="accent" onClick={submit}>➜</button>
    </div>
  )
}
