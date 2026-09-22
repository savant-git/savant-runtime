import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion"
import {
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  GitBranch,
  Network,
  Quote,
  RotateCcw,
  Sparkles,
} from "lucide-react"
import {
  ReactNode,
  useMemo,
  useState,
} from "react"

export type PalaverMessageRecord = {
  id: string
  role: "user" | "assistant"
  body: string
  trace?: string
  createdAt: number
  parentId?: string | null
}

type Props = {
  message: PalaverMessageRecord
  copied: boolean
  onCopy: (
    id: string,
    text: string,
  ) => void
  onBranch: (
    message: PalaverMessageRecord,
  ) => void
  onRetry: (
    message: PalaverMessageRecord,
  ) => void
  onQuote: (
    message: PalaverMessageRecord,
  ) => void
}

type Block =
  | {
      type: "code"
      language: string
      content: string
    }
  | {
      type: "text"
      content: string
    }

function splitBlocks(
  source: string,
): Block[] {
  const blocks: Block[] = []

  const pattern =
    /```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```/g

  let cursor = 0
  let match:
    | RegExpExecArray
    | null = null

  while (
    (
      match =
        pattern.exec(source)
    ) !== null
  ) {
    if (
      match.index >
      cursor
    ) {
      blocks.push({
        type: "text",
        content:
          source.slice(
            cursor,
            match.index,
          ),
      })
    }

    blocks.push({
      type: "code",
      language:
        match[1] ||
        "text",
      content:
        match[2].replace(
          /\n$/,
          "",
        ),
    })

    cursor =
      match.index +
      match[0].length
  }

  if (
    cursor <
    source.length
  ) {
    blocks.push({
      type: "text",
      content:
        source.slice(cursor),
    })
  }

  return blocks.length
    ? blocks
    : [
        {
          type: "text",
          content: source,
        },
      ]
}

function renderInline(
  text: string,
): ReactNode[] {
  const tokens =
    text.split(
      /(`[^`]+`|\*\*[^*]+\*\*)/g,
    )

  return tokens.map(
    (
      token,
      index,
    ) => {
      if (
        token.startsWith(
          "`",
        ) &&
        token.endsWith(
          "`",
        )
      ) {
        return (
          <code
            key={index}
            className="palaver-inline-code"
          >
            {token.slice(
              1,
              -1,
            )}
          </code>
        )
      }

      if (
        token.startsWith(
          "**",
        ) &&
        token.endsWith(
          "**",
        )
      ) {
        return (
          <strong
            key={index}
          >
            {token.slice(
              2,
              -2,
            )}
          </strong>
        )
      }

      return token
    },
  )
}

function TextBlock({
  content,
}: {
  content: string
}) {
  const paragraphs =
    content
      .split(/\n{2,}/)
      .map(
        (value) =>
          value.trim(),
      )
      .filter(Boolean)

  return (
    <>
      {paragraphs.map(
        (
          paragraph,
          index,
        ) => {
          const lines =
            paragraph.split(
              "\n",
            )

          const list =
            lines.every(
              (line) =>
                /^[-*]\s+/.test(
                  line,
                ),
            )

          if (list) {
            return (
              <ul
                key={index}
                className="palaver-message-list"
              >
                {lines.map(
                  (
                    line,
                    lineIndex,
                  ) => (
                    <li
                      key={
                        lineIndex
                      }
                    >
                      {renderInline(
                        line.replace(
                          /^[-*]\s+/,
                          "",
                        ),
                      )}
                    </li>
                  ),
                )}
              </ul>
            )
          }

          return (
            <p key={index}>
              {lines.map(
                (
                  line,
                  lineIndex,
                ) => (
                  <span
                    key={
                      lineIndex
                    }
                  >
                    {renderInline(
                      line,
                    )}

                    {lineIndex <
                      lines.length -
                        1 && (
                      <br />
                    )}
                  </span>
                ),
              )}
            </p>
          )
        },
      )}
    </>
  )
}

function CodeBlock({
  language,
  content,
}: {
  language: string
  content: string
}) {
  const [
    copied,
    setCopied,
  ] = useState(false)

  const copy =
    async () => {
      await navigator.clipboard.writeText(
        content,
      )

      setCopied(true)

      window.setTimeout(
        () =>
          setCopied(false),
        1200,
      )
    }

  return (
    <div className="palaver-code-block">
      <header>
        <span>
          {language}
        </span>

        <button
          onClick={copy}
        >
          {copied ? (
            <Check
              size={13}
            />
          ) : (
            <Copy
              size={13}
            />
          )}

          {copied
            ? "copied"
            : "copy"}
        </button>
      </header>

      <pre>
        <code>
          {content}
        </code>
      </pre>
    </div>
  )
}

export default function PalaverMessage({
  message,
  copied,
  onCopy,
  onBranch,
  onRetry,
  onQuote,
}: Props) {
  const reducedMotion =
    useReducedMotion()

  const [
    traceOpen,
    setTraceOpen,
  ] = useState(false)

  const blocks =
    useMemo(
      () =>
        splitBlocks(
          message.body,
        ),
      [message.body],
    )

  return (
    <motion.article
      layout
      className={[
        "message",
        `message-${message.role}`,
      ].join(" ")}
      initial={
        reducedMotion
          ? false
          : {
              opacity: 0,
              y: 20,
              scale:
                0.985,
            }
      }
      animate={{
        opacity: 1,
        y: 0,
        scale: 1,
      }}
      exit={{
        opacity: 0,
        y: -8,
      }}
      transition={{
        type: "spring",
        stiffness: 340,
        damping: 31,
      }}
    >
      <header className="message-head">
        <div>
          {message.role ===
          "assistant" ? (
            <Sparkles
              size={12}
            />
          ) : null}

          <span>
            {message.role ===
            "user"
              ? "you"
              : "palaver"}
          </span>
        </div>

        <time>
          {new Intl.DateTimeFormat(
            undefined,
            {
              hour: "numeric",
              minute:
                "2-digit",
            },
          ).format(
            message.createdAt,
          )}
        </time>
      </header>

      <div className="message-body palaver-rich-message">
        {blocks.map(
          (
            block,
            index,
          ) =>
            block.type ===
            "code" ? (
              <CodeBlock
                key={index}
                language={
                  block.language
                }
                content={
                  block.content
                }
              />
            ) : (
              <TextBlock
                key={index}
                content={
                  block.content
                }
              />
            ),
        )}
      </div>

      <footer className="message-actions">
        <button
          onClick={() =>
            onCopy(
              message.id,
              message.body,
            )
          }
        >
          {copied ? (
            <Check
              size={14}
            />
          ) : (
            <Copy
              size={14}
            />
          )}

          {copied
            ? "copied"
            : "copy"}
        </button>

        <button
          onClick={() =>
            onQuote(
              message,
            )
          }
        >
          <Quote
            size={14}
          />
          quote
        </button>

        <button
          onClick={() =>
            onBranch(
              message,
            )
          }
        >
          <GitBranch
            size={14}
          />
          branch
        </button>

        {message.role ===
          "assistant" && (
          <button
            onClick={() =>
              onRetry(
                message,
              )
            }
          >
            <RotateCcw
              size={14}
            />
            retry
          </button>
        )}

        {message.trace && (
          <button
            onClick={() =>
              setTraceOpen(
                (current) =>
                  !current,
              )
            }
          >
            <Network
              size={14}
            />

            trace

            {traceOpen ? (
              <ChevronDown
                size={12}
              />
            ) : (
              <ChevronRight
                size={12}
              />
            )}
          </button>
        )}
      </footer>

      <AnimatePresence>
        {message.trace &&
          traceOpen && (
            <motion.pre
              className="message-trace"
              initial={{
                opacity: 0,
                height: 0,
              }}
              animate={{
                opacity: 1,
                height:
                  "auto",
              }}
              exit={{
                opacity: 0,
                height: 0,
              }}
            >
              {message.trace}
            </motion.pre>
          )}
      </AnimatePresence>
    </motion.article>
  )
}
