import {
  useEffect,
  useMemo,
  useState
} from "react"

import Editor
  from "@monaco-editor/react"

import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Braces,
  Clipboard,
  Copy,
  FileCode2,
  FolderTree,
  MessageSquareText,
  RefreshCw,
  Search
} from "lucide-react"

import {
  decodeFileResponse,
  FileIndexEntry,
  repositoryEntries
} from "../lib/file-contract"

import {
  useWorkspaceStore
} from "../state/workspace-store"


function languageFor(
  path: string
) {
  const lower =
    path.toLowerCase()

  if (
    lower.endsWith(".py")
  ) return "python"

  if (
    /\.(ts|tsx)$/
      .test(lower)
  ) return "typescript"

  if (
    /\.(js|jsx|mjs|cjs)$/
      .test(lower)
  ) return "javascript"

  if (
    lower.endsWith(".json")
  ) return "json"

  if (
    lower.endsWith(".css")
  ) return "css"

  if (
    lower.endsWith(".html")
  ) return "html"

  if (
    lower.endsWith(".md")
  ) return "markdown"

  if (
    /\.(sh|bash)$/
      .test(lower)
  ) return "shell"

  if (
    /\.(yaml|yml)$/
      .test(lower)
  ) return "yaml"

  if (
    lower.endsWith(".xml")
  ) return "xml"

  return "plaintext"
}


export default function SourceStudio() {
  const {
    sourcePath,
    openSource,
    setActive,
    setComposerDraft,
    setLastActivity
  } = useWorkspaceStore()

  const [
    files,
    setFiles
  ] = useState<
    FileIndexEntry[]
  >([])

  const [
    query,
    setQuery
  ] = useState("")

  const [
    content,
    setContent
  ] = useState("")

  const [
    actualPath,
    setActualPath
  ] = useState("")

  const [
    size,
    setSize
  ] = useState<
    number | null
  >(null)

  const [
    truncated,
    setTruncated
  ] = useState(false)

  const [
    error,
    setError
  ] = useState("")

  const [
    technical,
    setTechnical
  ] = useState("")

  const [
    technicalOpen,
    setTechnicalOpen
  ] = useState(false)

  const [
    loading,
    setLoading
  ] = useState(false)

  const [
    history,
    setHistory
  ] = useState<string[]>([])

  const [
    historyIndex,
    setHistoryIndex
  ] = useState(-1)


  async function loadFiles() {
    setLoading(true)

    try {
      const response =
        await fetch(
          "/api/repository/files",
          {
            cache:
              "no-store"
          }
        )

      const payload =
        await response.json()

      const next =
        repositoryEntries(
          payload
        )

      setFiles(next)

      setLastActivity(
        `indexed ${next.length} readable source files`
      )
    } catch (
      reason
    ) {
      setError(
        "Palaver could not load the source index."
      )

      setTechnical(
        String(reason)
      )
    } finally {
      setLoading(false)
    }
  }


  async function readFile(
    path: string,
    recordHistory = true
  ) {
    if (!path) {
      return
    }

    setLoading(true)
    setError("")
    setTechnical("")
    setTechnicalOpen(false)
    setContent("")
    setActualPath(path)
    setSize(null)
    setTruncated(false)

    try {
      const response =
        await fetch(
          `/api/file?path=${encodeURIComponent(path)}`,
          {
            cache:
              "no-store"
          }
        )

      const text =
        await response.text()

      let payload:
        unknown = text

      try {
        payload =
          JSON.parse(text)
      } catch {
        payload = text
      }

      const result =
        decodeFileResponse(
          payload,
          path,
          response.ok
        )

      if (!result.ok) {
        setError(
          result.error
        )

        setTechnical(
          result.technical
        )

        return
      }

      setContent(
        result.content
      )

      setActualPath(
        result.path
      )

      setSize(
        result.size
      )

      setTruncated(
        result.truncated
      )

      if (
        recordHistory
      ) {
        setHistory(
          current => {
            const trimmed =
              historyIndex >= 0
                ? current.slice(
                    0,
                    historyIndex + 1
                  )
                : current

            if (
              trimmed.at(-1)
              === path
            ) {
              return trimmed
            }

            const next =
              [
                ...trimmed,
                path
              ].slice(-100)

            window.setTimeout(
              () =>
                setHistoryIndex(
                  next.length - 1
                ),
              0
            )

            return next
          }
        )
      }

      setLastActivity(
        `reading ${result.path}`
      )
    } catch (
      reason
    ) {
      setError(
        "Palaver could not read this file."
      )

      setTechnical(
        String(reason)
      )
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadFiles()
  }, [])


  useEffect(() => {
    if (sourcePath) {
      readFile(
        sourcePath
      )
    }
  }, [sourcePath])


  const visible =
    useMemo(
      () => {
        const term =
          query
            .trim()
            .toLowerCase()

        if (!term) {
          return files
        }

        const terms =
          term
            .split(/\s+/)
            .filter(Boolean)

        return files.filter(
          entry => {
            const haystack =
              `${entry.name} ${entry.path}`
                .toLowerCase()

            return terms.every(
              value =>
                haystack.includes(
                  value
                )
            )
          }
        )
      },
      [
        files,
        query
      ]
    )


  function askPalaver() {
    if (
      !actualPath
      || !content
    ) {
      return
    }

    setComposerDraft(
      [
        "Analyze this source file.",
        `file: ${actualPath}`,
        "",
        content.slice(
          0,
          30000
        )
      ].join("\n")
    )

    setActive("chat")

    setLastActivity(
      `attached ${actualPath} to palaver`
    )
  }


  function navigateHistory(
    delta: number
  ) {
    const nextIndex =
      historyIndex
      + delta

    if (
      nextIndex < 0
      || nextIndex
      >= history.length
    ) {
      return
    }

    const path =
      history[nextIndex]

    setHistoryIndex(
      nextIndex
    )

    openSource(path)

    readFile(
      path,
      false
    )
  }


  return (
    <section className="source-studio">
      <header className="source-header">
        <div>
          <Braces size={18} />

          <div>
            <span>
              live readable source
            </span>

            <h1>
              files
            </h1>

            <p>
              Browse actual source, inspect it in Monaco, copy it, or send it directly to Palaver.
            </p>
          </div>
        </div>

        <div>
          <button
            type="button"
            disabled={
              historyIndex <= 0
            }
            onClick={() =>
              navigateHistory(-1)
            }
            title="Back"
          >
            <ArrowLeft
              size={14}
            />
          </button>

          <button
            type="button"
            disabled={
              historyIndex < 0
              || historyIndex
              >= history.length - 1
            }
            onClick={() =>
              navigateHistory(1)
            }
            title="Forward"
          >
            <ArrowRight
              size={14}
            />
          </button>

          <button
            type="button"
            onClick={
              loadFiles
            }
            title="Refresh source index"
          >
            <RefreshCw
              size={14}
            />
          </button>

          <button
            type="button"
            disabled={
              !content
            }
            onClick={
              askPalaver
            }
          >
            <MessageSquareText
              size={14}
            />

            ask palaver
          </button>
        </div>
      </header>


      <main className="source-workspace">
        <aside className="source-tree">
          <label>
            <Search
              size={13}
            />

            <input
              value={query}
              onChange={
                event =>
                  setQuery(
                    event.target.value
                  )
              }
              placeholder="Search filenames and paths…"
            />
          </label>

          <header>
            <FolderTree
              size={13}
            />

            <span>
              {visible.length}
              {" "}
              readable files
            </span>
          </header>

          <div>
            {visible
              .slice(
                0,
                4000
              )
              .map(
                entry => (
                  <button
                    type="button"
                    key={
                      entry.path
                    }
                    className={
                      entry.path
                      === sourcePath
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      openSource(
                        entry.path
                      )
                    }
                    title={
                      entry.path
                    }
                  >
                    <FileCode2
                      size={12}
                    />

                    <span>
                      {entry.name}
                    </span>
                  </button>
                )
              )}
          </div>
        </aside>


        <section className="source-editor">
          <header>
            <span>
              {actualPath
                || "Choose a source file"}
            </span>

            <div>
              {size !== null && (
                <span>
                  {size.toLocaleString()}
                  {" "}
                  chars
                </span>
              )}

              {actualPath && (
                <button
                  type="button"
                  onClick={() =>
                    navigator.clipboard
                      .writeText(
                        actualPath
                      )
                  }
                  title="Copy path"
                >
                  <Copy
                    size={13}
                  />
                </button>
              )}

              {content && (
                <button
                  type="button"
                  onClick={() =>
                    navigator.clipboard
                      .writeText(
                        content
                      )
                  }
                  title="Copy source"
                >
                  <Clipboard
                    size={13}
                  />
                </button>
              )}
            </div>
          </header>


          {error
            ? (
              <div className="source-readable-error">
                <AlertTriangle
                  size={24}
                />

                <strong>
                  File unavailable
                </strong>

                <p>
                  {error}
                </p>

                {technical && (
                  <button
                    type="button"
                    onClick={() =>
                      setTechnicalOpen(
                        value =>
                          !value
                      )
                    }
                  >
                    {technicalOpen
                      ? "hide technical details"
                      : "technical details"}
                  </button>
                )}

                {technicalOpen && (
                  <pre>
                    {technical}
                  </pre>
                )}
              </div>
            )
            : actualPath
              ? (
                <>
                  <Editor
                    path={
                      actualPath
                    }
                    value={
                      content
                    }
                    language={
                      languageFor(
                        actualPath
                      )
                    }
                    theme="vs-dark"
                    options={{
                      readOnly:
                        true,

                      automaticLayout:
                        true,

                      minimap: {
                        enabled:
                          true
                      },

                      fontSize:
                        12,

                      smoothScrolling:
                        true,

                      wordWrap:
                        "off",

                      folding:
                        true,

                      stickyScroll: {
                        enabled:
                          true
                      },

                      bracketPairColorization: {
                        enabled:
                          true
                      },

                      guides: {
                        indentation:
                          true,

                        bracketPairs:
                          true
                      },

                      renderWhitespace:
                        "selection",

                      scrollBeyondLastLine:
                        false
                    }}
                  />

                  {truncated && (
                    <div className="source-loading">
                      Preview truncated by the current Palaver backend read limit.
                    </div>
                  )}
                </>
              )
              : (
                <div className="source-empty">
                  <FileCode2
                    size={38}
                  />

                  <strong>
                    Choose a file
                  </strong>

                  <span>
                    Only source candidates compatible with Palaver’s current read policy are shown.
                  </span>
                </div>
              )
          }


          {loading && (
            <div className="source-loading">
              reading filesystem
            </div>
          )}
        </section>
      </main>
    </section>
  )
}
