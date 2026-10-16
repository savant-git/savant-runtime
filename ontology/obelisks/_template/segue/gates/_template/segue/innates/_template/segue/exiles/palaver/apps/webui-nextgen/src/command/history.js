const KEY =
  "palaver.command.history"

export function loadHistory(){

  try{

    return JSON.parse(
      localStorage.getItem(KEY)
      || "[]"
    )

  }catch{

    return []

  }

}

export function pushHistory(
  command
){

  const rows =
    loadHistory()

  rows.unshift(command)

  localStorage.setItem(
    KEY,
    JSON.stringify(
      rows.slice(0,500)
    )
  )

}
