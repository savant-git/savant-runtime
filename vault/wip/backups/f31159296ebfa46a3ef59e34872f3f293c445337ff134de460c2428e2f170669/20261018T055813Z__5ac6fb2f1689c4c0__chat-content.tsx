import {useState} from "react"
import {Code2,Check,Clipboard,TerminalSquare} from "../components/savant-glyphs"
export function extractCodeBlocks(
  content:
    string,
) {
  const results:
    string[] = [];

  const pattern =
    /```(?:[^\n]*)\n([\s\S]*?)```/g;

  let match:
    RegExpExecArray | null;

  while (
    (
      match =
        pattern.exec(
          content,
        )
    ) !== null
  ) {
    const code =
      match[
        1
      ]?.trim();

    if (
      code
    ) {
      results.push(
        code,
      );
    }
  }

  return results;
}



export function isUnknownRecord(
  value:
    unknown,
): value is Record<string, unknown> {
  return (
    value
    !== null
    && typeof value
    === "object"
    && !Array.isArray(
      value,
    )
  );
}


type RichPart =
  | {
      kind:
        "text";
      value:
        string;
    }
  | {
      kind:
        "code";
      value:
        string;
      language:
        string;
    };


function detectedLanguage(
  hint:
    string,
  code:
    string,
) {
  const normalized =
    hint
      .trim()
      .toLowerCase();

  const aliases:
    Record<
      string,
      string
    > = {
      sh:
        "bash",
      shell:
        "bash",
      zsh:
        "bash",
      py:
        "python",
      js:
        "javascript",
      jsx:
        "javascript",
      ts:
        "typescript",
      tsx:
        "typescript",
      htm:
        "html",
      txt:
        "text",
      plaintext:
        "text",
    };

  if (
    aliases[
      normalized
    ]
  ) {
    return aliases[
      normalized
    ];
  }

  if (
    normalized
  ) {
    return normalized;
  }

  const value =
    code.trim();

  if (
    /^#!/m.test(
      value,
    )
    || /\b(?:sudo|cd|chmod|mkdir|npm|pnpm|yarn|git|curl|ssh)\b/.test(
      value,
    )
  ) {
    return "bash";
  }

  if (
    /(?:^|\n)\s*(?:def|class|from|import)\s+\w+/.test(
      value,
    )
    || /\bprint\s*\(/.test(
      value,
    )
  ) {
    return "python";
  }

  if (
    /\b(?:const|let|var|function|console\.log)\b/.test(
      value,
    )
    || /=>/.test(
      value,
    )
  ) {
    return "javascript";
  }

  if (
    /^[\[{][\s\S]*[\]}]$/.test(
      value,
    )
  ) {
    try {
      JSON.parse(
        value,
      );

      return "json";
    } catch {
      // Continue.
    }
  }

  if (
    /<!doctype\s+html|<html|<div|<section|<main/i.test(
      value,
    )
  ) {
    return "html";
  }

  if (
    /\b(?:select|insert|update|delete|create table|alter table)\b/i.test(
      value,
    )
  ) {
    return "sql";
  }

  return "text";
}


function richParts(
  content:
    string,
): RichPart[] {
  const parts:
    RichPart[] = [];

  const pattern =
    /```([a-zA-Z0-9_+-]*)[ \t]*\n([\s\S]*?)```/g;

  let cursor =
    0;

  let match:
    RegExpExecArray
    | null;

  while (
    (
      match =
        pattern.exec(
          content,
        )
    )
  ) {
    if (
      match.index
      > cursor
    ) {
      parts.push({
        kind:
          "text",

        value:
          content.slice(
            cursor,
            match.index,
          ),
      });
    }

    parts.push({
      kind:
        "code",

      value:
        (
          match[
            2
          ]
          || ""
        ).replace(
          /\n$/,
          "",
        ),

      language:
        detectedLanguage(
          match[
            1
          ]
          || "",
          match[
            2
          ]
          || "",
        ),
    });

    cursor =
      pattern.lastIndex;
  }

  if (
    cursor
    < content.length
  ) {
    parts.push({
      kind:
        "text",

      value:
        content.slice(
          cursor,
        ),
    });
  }

  return parts.length
    ? parts
    : [
      {
        kind:
          "text",

        value:
          content,
      },
    ];
}


function CodeSurface({
  code,
  language,
  onStage,
}: {
  code:
    string;
  language:
    string;
  onStage: (
    value:
      string,
  ) => void;
}) {
  const [
    copied,
    setCopied,
  ] = useState(
    false,
  );

  const [
    wrapped,
    setWrapped,
  ] = useState(
    false,
  );

  const [
    collapsed,
    setCollapsed,
  ] = useState(
    false,
  );


  async function copyCode() {
    await navigator.clipboard
      .writeText(
        code,
      );

    setCopied(
      true,
    );

    window.setTimeout(
      () =>
        setCopied(
          false,
        ),
      1200,
    );
  }


  return (
    <section
      className={
        "palaver-code-block"
      }
    >
      <header
        className={
          "palaver-code-toolbar"
        }
      >
        <span
          className={
            "palaver-code-language"
          }
          title={
            "Detected code language"
          }
        >
          <Code2
            size={
              13
            }
          />

          {language}
        </span>

        <div
          className={
            "palaver-code-actions"
          }
        >
          <button
            type="button"
            onClick={
              () =>
                setWrapped(
                  value =>
                    !value,
                )
            }
            className={
              wrapped
                ? "active"
                : ""
            }
            title={
              "Toggle line wrapping"
            }
          >
            wrap
          </button>

          <button
            type="button"
            onClick={
              () =>
                setCollapsed(
                  value =>
                    !value,
                )
            }
            title={
              collapsed
                ? "Expand code"
                : "Collapse code"
            }
          >
            {collapsed
              ? "expand"
              : "collapse"}
          </button>

          <button
            type="button"
            onClick={
              () =>
                onStage(
                  code,
                )
            }
            title={
              "Stage in terminal"
            }
          >
            <TerminalSquare
              size={
                13
              }
            />
          </button>

          <button
            type="button"
            onClick={
              copyCode
            }
            title={
              "Copy code"
            }
          >
            {copied
              ? (
                <Check
                  size={
                    13
                  }
                />
              )
              : (
                <Clipboard
                  size={
                    13
                  }
                />
              )}
          </button>
        </div>
      </header>

      {!collapsed
      && (
        <pre
          className={
            wrapped
              ? "palaver-code-content wrapped"
              : "palaver-code-content"
          }
        >
          <code>
            {code}
          </code>
        </pre>
      )}

      <footer
        className={
          "palaver-code-meta"
        }
      >
        {
          code
            .split(
              "\n",
            )
            .length
        } lines
        {" · "}
        {
          new Blob([
            code,
          ]).size
        } bytes
      </footer>
    </section>
  );
}


export function RichMessage({
  content,
  onStage,
}: {
  content:
    string;
  onStage: (
    value:
      string,
  ) => void;
}) {
  return (
    <div
      className={
        "rich-message-content"
      }
    >
      {richParts(
        content,
      ).map(
        (
          part,
          index,
        ) =>
          part.kind
          === "code"
            ? (
              <CodeSurface
                key={
                  `code-${index}`
                }
                code={
                  part.value
                }
                language={
                  part.language
                }
                onStage={
                  onStage
                }
              />
            )
            : (
              <div
                key={
                  `text-${index}`
                }
                className={
                  "rich-message-text"
                }
              >
                {part.value}
              </div>
            ),
      )}
    </div>
  );
}
