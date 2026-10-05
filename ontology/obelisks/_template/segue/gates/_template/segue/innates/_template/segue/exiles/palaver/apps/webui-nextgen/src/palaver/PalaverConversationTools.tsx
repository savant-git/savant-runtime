import {
  Check,
  Clipboard,
  Download,
  FileJson,
  RotateCcw,
  Trash2,
  Upload,
  X,
} from "lucide-react"
import {
  ChangeEvent,
  useRef,
  useState,
} from "react"

type Props = {
  messageCount: number
  branchCount: number
  onCopy: () => Promise<void>
  onExport: () => string
  onImport: (
    raw: string,
  ) => boolean
  onClearCurrent: () => void
  onClearAll: () => void
}

function download(
  content: string,
  filename: string,
) {
  const blob =
    new Blob(
      [content],
      {
        type:
          "application/json;charset=utf-8",
      },
    )

  const url =
    URL.createObjectURL(
      blob,
    )

  const anchor =
    document.createElement(
      "a",
    )

  anchor.href = url
  anchor.download =
    filename

  document.body.appendChild(
    anchor,
  )

  anchor.click()
  anchor.remove()

  URL.revokeObjectURL(
    url,
  )
}

export default function PalaverConversationTools({
  messageCount,
  branchCount,
  onCopy,
  onExport,
  onImport,
  onClearCurrent,
  onClearAll,
}: Props) {
  const fileRef =
    useRef<HTMLInputElement>(
      null,
    )

  const [copied, setCopied] =
    useState(false)

  const [
    importState,
    setImportState,
  ] = useState<
    "idle" | "ok" | "error"
  >("idle")

  const copy =
    async () => {
      await onCopy()

      setCopied(true)

      window.setTimeout(
        () =>
          setCopied(false),
        1200,
      )
    }

  const exportJson =
    () => {
      download(
        onExport(),
        `palaver-conversation-${new Date()
          .toISOString()
          .replace(
            /[:.]/g,
            "-",
          )}.json`,
      )
    }

  const importJson =
    async (
      event:
        ChangeEvent<HTMLInputElement>,
    ) => {
      const file =
        event.target
          .files?.[0]

      event.target.value =
        ""

      if (!file) {
        return
      }

      try {
        const raw =
          await file.text()

        const ok =
          onImport(raw)

        setImportState(
          ok
            ? "ok"
            : "error",
        )
      } catch {
        setImportState(
          "error",
        )
      }

      window.setTimeout(
        () =>
          setImportState(
            "idle",
          ),
        1800,
      )
    }

  return (
    <section className="palaver-conversation-tools">
      <header>
        <span>
          local conversation
        </span>

        <small>
          {messageCount} messages ·{" "}
          {branchCount} paths
        </small>
      </header>

      <div>
        <button
          type="button"
          onClick={copy}
          disabled={
            messageCount === 0
          }
        >
          {copied ? (
            <Check
              size={15}
            />
          ) : (
            <Clipboard
              size={15}
            />
          )}

          <span>
            {copied
              ? "copied"
              : "copy path"}
          </span>
        </button>

        <button
          type="button"
          onClick={
            exportJson
          }
        >
          <Download
            size={15}
          />

          <span>
            export
          </span>
        </button>

        <button
          type="button"
          onClick={() =>
            fileRef.current?.click()
          }
        >
          {importState ===
          "ok" ? (
            <Check
              size={15}
            />
          ) : importState ===
            "error" ? (
            <X
              size={15}
            />
          ) : (
            <Upload
              size={15}
            />
          )}

          <span>
            {importState ===
            "ok"
              ? "imported"
              : importState ===
                  "error"
                ? "invalid"
                : "import"}
          </span>
        </button>

        <button
          type="button"
          onClick={
            onClearCurrent
          }
          disabled={
            messageCount === 0
          }
        >
          <RotateCcw
            size={15}
          />

          <span>
            clear path
          </span>
        </button>

        <button
          type="button"
          className="danger"
          onClick={
            onClearAll
          }
          disabled={
            messageCount ===
              0 &&
            branchCount === 0
          }
        >
          <Trash2
            size={15}
          />

          <span>
            clear all
          </span>
        </button>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        className="sr-only"
        onChange={
          importJson
        }
      />

      <footer>
        <FileJson
          size={13}
        />

        <span>
          browser-local,
          disposable ui state
        </span>
      </footer>
    </section>
  )
}
