import {
  ChangeEvent,
  ClipboardEvent,
  DragEvent,
  FormEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AnimatePresence,
  motion,
} from "framer-motion";

import {
  Bot,
  Check,
  Clipboard,
  Code2,
  CornerDownLeft,
  Download,
  FilePlus2,
  FileText,
  Image,
  LoaderCircle,
  MessageSquareText,
  Pencil,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  TerminalSquare,
  Trash2,
  UserRound,
  VolumeX,
  X,
} from "lucide-react";

import {
  ChatAttachment,
  attachmentFromFile,
  attachmentFromText,
  estimateTokens,
  humanBytes,
  persistedAttachment,
  projectAttachments,
} from "../chat/attachments";

import ChatToolMenu, {
  PalaverCapabilities,
  PalaverChatTool,
} from "../chat/chat-tool-menu";

import ChatToolSurface
  from "../chat/chat-tool-surface";
import UrgeControl
  from "../chat/urge-control";

import {
  useWorkspaceStore,
} from "../state/workspace-store";


type MessageStatus =
  | "sending"
  | "sent"
  | "failed"
  | "received";


type Message = {
  id: string;

  role:
    | "user"
    | "assistant"
    | "system";

  content: string;
  trace?: string;
  timestamp: number;
  status?: MessageStatus;
  attachments?: ChatAttachment[];
};


type ChatMode =
  | "standard"
  | "develop"
  | "inspect"
  | "study"
  | "minimum";


type ResponsePayload = {
  ok?: boolean;
  answer?: string;
  response?: unknown;
  output_text?: string;
  output?: unknown;
  error?: string;
  error_code?: string;
  diagnostic?: string;
  retryable?: boolean;
  trace?: string;
};


const storageKey =
  "palaver.chat.v3";

const draftKey =
  "palaver.chat.draft.v2";

const modeKey =
  "palaver.chat.mode.v2";

const recentKey =
  "palaver.chat.recent-attachments.v2";

const recentToolKey =
  "palaver.chat.recent-tools.v1";

const historyKey =
  "palaver.chat.prompt-history.v1";

const longPasteThreshold =
  10000;


const capabilities:
  PalaverCapabilities = {
    createImage: {
      state:
        "unavailable",

      detail:
        "No image-generation backend contract is currently established.",
    },

    plugins: {
      state:
        "unavailable",

      detail:
        "No Palaver plugin execution registry is currently established.",
    },

    web: {
      state:
        "unavailable",

      detail:
        "No Palaver web/research backend contract is currently established.",
    },

    voice: {
      state:
        "unavailable",

      detail:
        "No currently verified voice contract is connected to this surface.",
    },
  };


const modeLabels:
  Record<
    ChatMode,
    string
  > = {
    standard:
      "standard",

    develop:
      "develop",

    inspect:
      "inspect",

    study:
      "study",

    minimum:
      "minimum",
  };


const modeInstructions:
  Record<
    ChatMode,
    string
  > = {
    standard:
      "",

    develop:
      (
        "Working mode: develop. "
        + "Optimize for implementation "
        + "and preserve current authority."
      ),

    inspect:
      (
        "Working mode: inspect. "
        + "Distinguish observed facts, "
        + "authority, inference and unknowns."
      ),

    study:
      (
        "Working mode: study. "
        + "Teach interactively, check understanding, "
        + "and progress from fundamentals to depth."
      ),

    minimum:
      (
        "Working mode: minimum. "
        + "Return only the minimum sufficient next action."
      ),
  };


function isChatMode(
  value:
    string | null,
): value is ChatMode {
  return (
    value === "standard"
    || value === "develop"
    || value === "inspect"
    || value === "study"
    || value === "minimum"
  );
}


function loadMode():
  ChatMode {
  const value =
    localStorage.getItem(
      modeKey,
    );

  return isChatMode(
    value,
  )
    ? value
    : "standard";
}


function messageId() {
  return (
    `${Date.now()}-`
    + Math.random()
      .toString(
        36,
      )
      .slice(
        2,
      )
  );
}


function safeJson(
  value:
    string,
): unknown {
  try {
    return JSON.parse(
      value,
    );
  } catch {
    return null;
  }
}


function loadMessages():
  Message[] {
  try {
    const value =
      localStorage.getItem(
        storageKey,
      );

    if (!value) {
      return [];
    }

    const parsed =
      JSON.parse(
        value,
      );

    return Array.isArray(
      parsed,
    )
      ? parsed
      : [];
  } catch {
    return [];
  }
}


function saveMessages(
  messages:
    Message[],
) {
  try {
    localStorage.setItem(
      storageKey,
      JSON.stringify(
        messages
          .slice(
            -300,
          )
          .map(
            message => ({
              ...message,

              attachments:
                message
                  .attachments
                  ?.map(
                    persistedAttachment,
                  ),
            }),
          ),
      ),
    );
  } catch {
    // Browser persistence is non-authoritative.
  }
}


function loadRecent():
  ChatAttachment[] {
  try {
    const value =
      localStorage.getItem(
        recentKey,
      );

    if (!value) {
      return [];
    }

    const parsed =
      JSON.parse(
        value,
      );

    return Array.isArray(
      parsed,
    )
      ? parsed
      : [];
  } catch {
    return [];
  }
}


function saveRecent(
  attachments:
    ChatAttachment[],
) {
  try {
    const prior =
      loadRecent();

    const merged = [
      ...attachments
        .filter(
          item =>
            item.state
            === "ready",
        )
        .map(
          item => ({
            ...persistedAttachment(
              item,
            ),

            text:
              item.text.slice(
                0,
                30000,
              ),
          }),
        ),

      ...prior,
    ];

    const seen =
      new Set<string>();

    const unique =
      merged.filter(
        item => {
          if (
            seen.has(
              item.id,
            )
          ) {
            return false;
          }

          seen.add(
            item.id,
          );

          return true;
        },
      );

    localStorage.setItem(
      recentKey,
      JSON.stringify(
        unique.slice(
          0,
          12,
        ),
      ),
    );
  } catch {
    // Browser persistence is non-authoritative.
  }
}


function loadRecentTools():
  PalaverChatTool[] {
  try {
    const value =
      localStorage.getItem(
        recentToolKey,
      );

    if (!value) {
      return [];
    }

    const parsed =
      JSON.parse(
        value,
      );

    return Array.isArray(
      parsed,
    )
      ? parsed.slice(
          0,
          6,
        )
      : [];
  } catch {
    return [];
  }
}


function rememberTool(
  tool:
    PalaverChatTool,
) {
  try {
    const next = [
      tool,

      ...loadRecentTools()
        .filter(
          item =>
            item !== tool,
        ),
    ].slice(
      0,
      6,
    );

    localStorage.setItem(
      recentToolKey,
      JSON.stringify(
        next,
      ),
    );

    return next;
  } catch {
    return [
      tool,
    ];
  }
}


function loadPromptHistory():
  string[] {
  try {
    const value =
      localStorage.getItem(
        historyKey,
      );

    if (!value) {
      return [];
    }

    const parsed =
      JSON.parse(
        value,
      );

    return Array.isArray(
      parsed,
    )
      ? parsed
      : [];
  } catch {
    return [];
  }
}


function savePromptHistory(
  text:
    string,
) {
  if (
    !text.trim()
  ) {
    return;
  }

  try {
    const next = [
      text.trim(),

      ...loadPromptHistory()
        .filter(
          item =>
            item
            !== text.trim(),
        ),
    ].slice(
      0,
      50,
    );

    localStorage.setItem(
      historyKey,
      JSON.stringify(
        next,
      ),
    );
  } catch {
    // Local command history is non-authoritative.
  }
}


function extractCodeBlocks(
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



function isUnknownRecord(
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


function assistantTextFromValue(
  value:
    unknown,
): string {
  if (
    typeof value
    === "string"
  ) {
    const trimmed =
      value.trim();

    if (
      (
        trimmed.startsWith(
          "{",
        )
        || trimmed.startsWith(
          "[",
        )
      )
    ) {
      const nested =
        safeJson(
          trimmed,
        );

      if (
        nested
        && nested
        !== value
      ) {
        const extracted =
          assistantTextFromValue(
            nested,
          );

        if (
          extracted
        ) {
          return extracted;
        }
      }
    }

    return trimmed;
  }

  if (
    !isUnknownRecord(
      value,
    )
  ) {
    return "";
  }

  const record =
    value;

  for (
    const key
    of [
      "output_text",
      "answer",
      "reply",
      "text",
    ]
  ) {
    const candidate =
      record[
        key
      ];

    if (
      typeof candidate
      === "string"
      && candidate.trim()
    ) {
      return candidate.trim();
    }
  }

  const output =
    record.output;

  if (
    Array.isArray(
      output,
    )
  ) {
    for (
      const item
      of output
    ) {
      if (
        !isUnknownRecord(
          item,
        )
      ) {
        continue;
      }

      const content =
        item.content;

      if (
        !Array.isArray(
          content,
        )
      ) {
        continue;
      }

      for (
        const part
        of content
      ) {
        if (
          !isUnknownRecord(
            part,
          )
        ) {
          continue;
        }

        const partRecord =
          part;

        if (
          typeof partRecord.text
          === "string"
          && partRecord.text
            .trim()
        ) {
          return partRecord.text
            .trim();
        }
      }
    }
  }

  const response =
    record.response;

  if (
    response
    !== undefined
  ) {
    const extracted =
      assistantTextFromValue(
        response,
      );

    if (
      extracted
    ) {
      return extracted;
    }
  }

  return "";
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


function RichMessage({
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


async function responsePayload(
  response:
    Response,
): Promise<ResponsePayload> {
  const text =
    await response.text();

  if (
    !text.trim()
  ) {
    return {
      ok:
        response.ok,
    };
  }

  const parsed =
    safeJson(
      text,
    );

  if (
    parsed
    && typeof parsed
    === "object"
  ) {
    return parsed as ResponsePayload;
  }

  return {
    ok:
      response.ok,

    answer:
      response.ok
        ? text
        : undefined,

    error:
      response.ok
        ? undefined
        : text,
  };
}


function projectedMessage(
  content:
    string,

  attachments:
    ChatAttachment[],

  mode:
    ChatMode,
) {
  const sections:
    string[] = [];

  if (
    modeInstructions[
      mode
    ]
  ) {
    sections.push(
      modeInstructions[
        mode
      ],
    );
  }

  if (
    content
  ) {
    sections.push(
      content,
    );
  }

  if (
    attachments.length
  ) {
    sections.push(
      [
        "User-supplied attachments follow.",

        (
          "They are working evidence, not authority "
          + "merely because they were attached."
        ),

        "",

        projectAttachments(
          attachments,
        ),
      ].join(
        "\n",
      ),
    );
  }

  return sections.join(
    "\n\n",
  );
}


function MessageCard({
  message,
  onEdit,
  onRetry,
  personas,
  personaId,
}: {
  message:
    Message;

  onEdit: (
    message:
      Message,
  ) => void;

  onRetry: (
    message:
      Message,
  ) => void;

  personas:
    Array<{
      persona_id?: string;
      display_name?: string;
    }>;

  personaId:
    string;
}) {
  const {
    setActive,
    stageTerminal,
    setLastActivity,
  } = useWorkspaceStore();

  const [
    copied,
    setCopied,
  ] = useState(
    false,
  );

  const codeBlocks =
    useMemo(
      () =>
        extractCodeBlocks(
          message.content,
        ),
      [
        message.content,
      ],
    );


  async function copy() {
    await navigator.clipboard
      .writeText(
        message.content,
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


  function stage(
    value:
      string,
  ) {
    stageTerminal(
      value,
    );

    setActive(
      "terminal",
    );

    setLastActivity(
      "command staged in terminal",
    );
  }


  const Icon =
    message.role
    === "user"
      ? UserRound
      : Bot;


  return (
    <motion.article
      className={
        (
          "chat-message "
          + `chat-message-${message.role}`
        )
      }
      initial={{
        opacity:
          0,

        y:
          8,
      }}
      animate={{
        opacity:
          1,

        y:
          0,
      }}
      transition={{
        duration:
          .17,
      }}
    >
      <header
        className={
          "chat-message-header"
        }
      >
        <div
          className={
            "chat-message-author"
          }
        >
          <span
            className={
              "chat-avatar"
            }
          >
            <Icon
              size={
                14
              }
            />
          </span>

          <div>
            <strong>
              {message.role
              === "user"
                ? "operator"
                : "palaver"}
            </strong>

            <span>
              {new Date(
                message.timestamp,
              ).toLocaleTimeString(
                [],
                {
                  hour:
                    "2-digit",

                  minute:
                    "2-digit",
                },
              )}

              {message.status
                ? (
                  ` · ${message.status}`
                )
                : ""}
            </span>
          </div>
        </div>

        <div
          className={
            "chat-message-actions"
          }
        >
          {message.role
          === "user"
          && (
            <button
              type="button"
              onClick={
                () =>
                  onEdit(
                    message,
                  )
              }
              title={
                "Edit and resend"
              }
            >
              <Pencil
                size={
                  14
                }
              />
            </button>
          )}

          <button
            type="button"
            onClick={
              copy
            }
            title={
              "Copy message"
            }
          >
            {copied
              ? (
                <Check
                  size={
                    14
                  }
                />
              )
              : (
                <Clipboard
                  size={
                    14
                  }
                />
              )}
          </button>

          {message.role
          === "assistant"
          && (
            <button
              type="button"
              onClick={
                () =>
                  onRetry(
                    message,
                  )
              }
              title={
                "Regenerate"
              }
            >
              <RefreshCw
                size={
                  14
                }
              />
            </button>
          )}
          {message.role
          === "assistant"
          && (
            <UrgeControl
              messageId={
                message.id
              }
              personas={
                personas
              }
              defaultPersonaId={
                personaId
              }
            />
          )}

          {message.role
          === "assistant"
          && codeBlocks.length
          > 0
          && (
            <button
              type="button"
              onClick={
                () =>
                  stage(
                    codeBlocks[
                      0
                    ],
                  )
              }
              title={
                "Stage first code block in terminal"
              }
            >
              <TerminalSquare
                size={
                  14
                }
              />
            </button>
          )}
        </div>
      </header>

      {message.attachments
      && message.attachments.length
      > 0
      && (
        <div
          className={
            "chat-message-attachments"
          }
        >
          {message.attachments.map(
            item => (
              <div
                key={
                  item.id
                }
                className={
                  "chat-message-attachment"
                }
              >
                {item.type
                  .startsWith(
                    "image/",
                  )
                  ? (
                    <Image
                      size={
                        13
                      }
                    />
                  )
                  : (
                    <FileText
                      size={
                        13
                      }
                    />
                  )}

                <span>
                  {item.name}
                </span>

                <small>
                  {humanBytes(
                    item.size,
                  )}
                </small>
              </div>
            ),
          )}
        </div>
      )}

      <div
        className={
          "chat-message-content"
        }
      >
        <RichMessage
          content={
            message.content
          }
          onStage={
            stage
          }
        />
      </div>

      {message.role
      === "assistant"
      && codeBlocks.length
      > 0
      && (
        <div
          className={
            "chat-code-actions"
          }
        >
          {codeBlocks.map(
            (
              code,
              index,
            ) => (
              <button
                type="button"
                key={
                  (
                    `${message.id}-`
                    + index
                  )
                }
                onClick={
                  () =>
                    stage(
                      code,
                    )
                }
              >
                <Code2
                  size={
                    13
                  }
                />

                stage code{" "}
                {index + 1}
              </button>
            ),
          )}
        </div>
      )}

      {message.trace
      && (
        <details
          className={
            "chat-trace"
          }
        >
          <summary>
            execution lineage
          </summary>

          <pre>
            {message.trace}
          </pre>
        </details>
      )}

      <details
        className={
          "chat-trace chat-message-details"
        }
      >
        <summary>
          response details
        </summary>

        <pre>
          {JSON.stringify(
            {
              id: message.id,
              role: message.role,
              status:
                message.status
                || "complete",
              timestamp:
                new Date(
                  message.timestamp,
                ).toISOString(),
            },
            null,
            2,
          )}
        </pre>
      </details>

      {message.attachments
      && message.attachments.length
      > 0
      && (
        <details
          className={
            "chat-trace chat-message-details"
          }
        >
          <summary>
            attached context
          </summary>

          <pre>
            {message.attachments
              .map(
                item =>
                  `${item.name} · ${humanBytes(item.size)}`,
              )
              .join(
                "\n",
              )}
          </pre>
        </details>
      )}
    </motion.article>
  );
}


export default function ChatObservatory() {
  const {
    composerDraft,
    setComposerDraft,
    setLastActivity,
    setActive,
  } = useWorkspaceStore();

  const [
    messages,
    setMessages,
  ] = useState<
    Message[]
  >(
    loadMessages,
  );

  const [
    attachments,
    setAttachments,
  ] = useState<
    ChatAttachment[]
  >([]);

  const [
    recent,
    setRecent,
  ] = useState<
    ChatAttachment[]
  >(
    loadRecent,
  );

  const [
    recentTools,
    setRecentTools,
  ] = useState<
    PalaverChatTool[]
  >(
    loadRecentTools,
  );

  const [
    running,
    setRunning,
  ] = useState(
    false,
  );

  const [
    error,
    setError,
  ] = useState(
    "",
  );

  const [
    health,
    setHealth,
  ] = useState<
    | "checking"
    | "online"
    | "degraded"
  >(
    "checking",
  );

  const [
    personas,
    setPersonas,
  ] = useState<
    Array<{
      persona_id?: string;
      display_name?: string;
    }>
  >([
    {
      persona_id: "orobouros",
      display_name: "Orobouros",
    },
  ]);

  const [
    personaId,
    setPersonaId,
  ] = useState(
    "orobouros",
  );

  const [
    menuOpen,
    setMenuOpen,
  ] = useState(
    false,
  );

  const [
    mode,
    setMode,
  ] = useState<
    ChatMode
  >(
    loadMode,
  );

  const [
    dragging,
    setDragging,
  ] = useState(
    false,
  );

  const [
    historyCursor,
    setHistoryCursor,
  ] = useState(
    -1,
  );

  const bottomRef =
    useRef<
      HTMLDivElement | null
    >(
      null,
    );

  const textareaRef =
    useRef<
      HTMLTextAreaElement | null
    >(
      null,
    );

  const fileInputRef =
    useRef<
      HTMLInputElement | null
    >(
      null,
    );

  const imageInputRef =
    useRef<
      HTMLInputElement | null
    >(
      null,
    );

  const cameraInputRef =
    useRef<
      HTMLInputElement | null
    >(
      null,
    );

  const abortRef =
    useRef<
      AbortController | null
    >(
      null,
    );

  const tokenEstimate =
    useMemo(
      () =>
        estimateTokens(
          composerDraft,
          attachments,
        ),
      [
        composerDraft,
        attachments,
      ],
    );


  useEffect(
    () => {
      saveMessages(
        messages,
      );

      bottomRef.current
        ?.scrollIntoView({
          behavior:
            window.matchMedia(
              "(prefers-reduced-motion: reduce)",
            ).matches
              ? "auto"
              : "smooth",

          block:
            "end",
        });
    },
    [
      messages,
    ],
  );


  useEffect(
    () => {
      try {
        localStorage.setItem(
          draftKey,
          composerDraft,
        );
      } catch {
        // Browser draft persistence is non-authoritative.
      }
    },
    [
      composerDraft,
    ],
  );


  useEffect(
    () => {
      const stored =
        localStorage.getItem(
          draftKey,
        );

      if (
        stored
        && !composerDraft
      ) {
        setComposerDraft(
          stored,
        );
      }
    },
    [],
  );


  useEffect(
    () => {
      try {
        localStorage.setItem(
          modeKey,
          mode,
        );
      } catch {
        // Browser mode persistence is non-authoritative.
      }
    },
    [
      mode,
    ],
  );


  useEffect(
    () => {
      let alive = true;

      async function loadPersonas() {
        try {
          const response =
            await fetch(
              "/api/voice/personas",
              {
                cache: "no-store",
              },
            );

          const payload =
            await response.json();

          const rows =
            Array.isArray(
              payload?.personas,
            )
              ? payload.personas
              : [];

          if (
            alive
            && rows.length
          ) {
            setPersonas(
              rows,
            );

            if (
              !rows.some(
                (
                  item:
                    {
                      persona_id?: string;
                    },
                ) =>
                  item.persona_id
                  === personaId,
              )
            ) {
              setPersonaId(
                rows.some(
                  (
                    item:
                      {
                        persona_id?: string;
                      },
                  ) =>
                    item.persona_id
                    === "orobouros",
                )
                  ? "orobouros"
                  : (
                    rows[0]
                      ?.persona_id
                    || "orobouros"
                  ),
              );
            }
          }
        } catch {
          // Envoy registry remains projected through the default fallback.
        }
      }

      void loadPersonas();

      return () => {
        alive = false;
      };
    },
    [],
  );


  useEffect(
    () => {
      const textarea =
        textareaRef.current;

      if (
        !textarea
      ) {
        return;
      }

      const currentHeight =
        textarea.offsetHeight;

      const contentHeight =
        Math.min(
          textarea.scrollHeight,
          Math.max(
            260,
            Math.floor(
              window.innerHeight
              * 0.42,
            ),
          ),
        );

      textarea.style.height =
        `${Math.max(
          currentHeight,
          contentHeight,
        )}px`;
    },
    [
      composerDraft,
    ],
  );


  useEffect(
    () => {
      let alive =
        true;

      async function check() {
        try {
          const response =
            await fetch(
              "/api/health",
              {
                cache:
                  "no-store",
              },
            );

          if (
            alive
          ) {
            setHealth(
              response.ok
                ? "online"
                : "degraded",
            );
          }
        } catch {
          if (
            alive
          ) {
            setHealth(
              "degraded",
            );
          }
        }
      }

      void check();

      const timer =
        window.setInterval(
          () =>
            void check(),
          30000,
        );

      return () => {
        alive =
          false;

        window.clearInterval(
          timer,
        );
      };
    },
    [],
  );


  useEffect(
    () => {
      return () => {
        abortRef.current
          ?.abort();
      };
    },
    [],
  );


  async function ingest(
    files:
      File[],
  ) {
    if (
      files.length
      === 0
    ) {
      return;
    }

    const results =
      await Promise.all(
        files.map(
          attachmentFromFile,
        ),
      );

    setAttachments(
      current => {
        const existing =
          new Set(
            current.map(
              item =>
                item.id,
            ),
          );

        return [
          ...current,

          ...results.filter(
            item =>
              !existing.has(
                item.id,
              ),
          ),
        ];
      },
    );

    saveRecent(
      results,
    );

    setRecent(
      loadRecent(),
    );

    setLastActivity(
      (
        `${results.length} attachment`
        + (
          results.length
          === 1
            ? ""
            : "s"
        )
        + " added to chat"
      ),
    );
  }


  function fileInput(
    event:
      ChangeEvent<HTMLInputElement>,
  ) {
    void ingest(
      Array.from(
        event.target.files
        ?? [],
      ),
    );

    event.target.value =
      "";
  }


  function removeAttachment(
    id:
      string,
  ) {
    setAttachments(
      current =>
        current.filter(
          item => {
            if (
              item.id
              === id
              && item.previewUrl
            ) {
              URL.revokeObjectURL(
                item.previewUrl,
              );
            }

            return (
              item.id
              !== id
            );
          },
        ),
    );
  }


  function addRecent(
    item:
      ChatAttachment,
  ) {
    setAttachments(
      current => {
        if (
          current.some(
            existing =>
              existing.id
              === item.id,
          )
        ) {
          return current;
        }

        return [
          ...current,
          item,
        ];
      },
    );

    setMenuOpen(
      false,
    );
  }


  async function pasteClipboard() {
    try {
      const value =
        await navigator.clipboard
          .readText();

      if (
        !value
      ) {
        return;
      }

      const attachment =
        await attachmentFromText(
          value,
          "clipboard.txt",
        );

      setAttachments(
        current => [
          ...current,
          attachment,
        ],
      );

      saveRecent([
        attachment,
      ]);

      setRecent(
        loadRecent(),
      );

      setMenuOpen(
        false,
      );
    } catch (
      reason
    ) {
      setError(
        reason
        instanceof Error
          ? reason.message
          : String(
              reason,
            ),
      );
    }
  }


  async function composerPaste(
    event:
      ClipboardEvent<HTMLTextAreaElement>,
  ) {
    const files =
      Array.from(
        event
          .clipboardData
          .files,
      );

    if (
      files.length
    ) {
      event.preventDefault();

      await ingest(
        files,
      );

      return;
    }

    const text =
      event
        .clipboardData
        .getData(
          "text/plain",
        );

    if (
      text.length
      > longPasteThreshold
    ) {
      event.preventDefault();

      const attachment =
        await attachmentFromText(
          text,
          "long-paste.txt",
        );

      setAttachments(
        current => [
          ...current,
          attachment,
        ],
      );

      saveRecent([
        attachment,
      ]);

      setRecent(
        loadRecent(),
      );

      setLastActivity(
        "long paste converted to attachment",
      );
    }
  }


  function handleDrop(
    event:
      DragEvent<HTMLElement>,
  ) {
    event.preventDefault();

    setDragging(
      false,
    );

    void ingest(
      Array.from(
        event
          .dataTransfer
          .files,
      ),
    );
  }


  function updateStatus(
    id:
      string,

    status:
      MessageStatus,
  ) {
    setMessages(
      current =>
        current.map(
          message =>
            message.id
            === id
              ? {
                  ...message,
                  status,
                }
              : message,
        ),
    );
  }


  async function send(
    raw?:
      string,

    suppliedAttachments?:
      ChatAttachment[],
  ) {
    const content =
      (
        raw
        ?? composerDraft
      ).trim();

    const selected =
      suppliedAttachments
      ?? attachments;

    if (
      (
        !content
        && selected.length
        === 0
      )
      || running
    ) {
      return;
    }

    savePromptHistory(
      content,
    );

    setHistoryCursor(
      -1,
    );

    const userMessage:
      Message = {
        id:
          messageId(),

        role:
          "user",

        content:
          content
          || "(attachments)",

        timestamp:
          Date.now(),

        status:
          "sending",

        attachments:
          selected.map(
            persistedAttachment,
          ),
      };

    setMessages(
      current => [
        ...current,
        userMessage,
      ],
    );

    setComposerDraft(
      "",
    );

    setAttachments(
      [],
    );

    setRunning(
      true,
    );

    setError(
      "",
    );

    setLastActivity(
      "palaver inference requested",
    );

    const controller =
      new AbortController();

    abortRef.current =
      controller;

    const timeout =
      window.setTimeout(
        () =>
          controller.abort(
            "request timeout",
          ),
        310000,
      );

    try {
      const response =
        await fetch(
          "/api/chat",
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                message:
                  projectedMessage(
                    content,
                    selected,
                    mode,
                  ),

                persona_id:
                  personaId,
              }),

            signal:
              controller.signal,

            cache:
              "no-store",
          },
        );

      const payload =
        await responsePayload(
          response,
        );

      if (
        !response.ok
        || payload.ok
        === false
      ) {
        throw new Error(
          payload.error
          || payload.answer
          || payload.response
          || (
            `HTTP ${response.status}`
          ),
        );
      }

      updateStatus(
        userMessage.id,
        "sent",
      );

      setMessages(
        current => [
          ...current,

          {
            id:
              messageId(),

            role:
              "assistant",

            content:
              assistantTextFromValue(
                payload,
              )
              || "(empty response)",

            trace:
              payload.trace
              || "",

            timestamp:
              Date.now(),

            status:
              "received",
          },
        ],
      );

      setLastActivity(
        "palaver response received",
      );
    } catch (
      reason
    ) {
      const aborted =
        controller.signal
          .aborted;

      const value =
        aborted
          ? "request stopped"
          : (
            reason
            instanceof Error
              ? reason.message
              : String(
                  reason,
                )
          );

      updateStatus(
        userMessage.id,
        "failed",
      );

      setError(
        value,
      );

      if (
        !aborted
      ) {
        setMessages(
          current => [
            ...current,

            {
              id:
                messageId(),

              role:
                "system",

              content:
                value,

              timestamp:
                Date.now(),

              status:
                "failed",
            },
          ],
        );
      }
    } finally {
      window.clearTimeout(
        timeout,
      );

      abortRef.current =
        null;

      setRunning(
        false,
      );
    }
  }


  function stop() {
    abortRef.current
      ?.abort(
        "operator stopped request",
      );
  }


  function submit(
    event:
      FormEvent,
  ) {
    event.preventDefault();

    void send();
  }


  function recallHistory(
    direction:
      -1 | 1,
  ) {
    const history =
      loadPromptHistory();

    if (
      history.length
      === 0
    ) {
      return;
    }

    const next =
      Math.max(
        -1,
        Math.min(
          history.length
          - 1,

          historyCursor
          + direction,
        ),
      );

    setHistoryCursor(
      next,
    );

    if (
      next
      === -1
    ) {
      return;
    }

    setComposerDraft(
      history[
        next
      ],
    );
  }


  function keyDown(
    event:
      KeyboardEvent<HTMLTextAreaElement>,
  ) {
    if (
      event.key
      === "Enter"
      && (
        event.metaKey
        || event.ctrlKey
      )
    ) {
      event.preventDefault();

      void send();

      return;
    }

    if (
      event.altKey
      && event.key
      === "ArrowUp"
    ) {
      event.preventDefault();

      recallHistory(
        1,
      );

      return;
    }

    if (
      event.altKey
      && event.key
      === "ArrowDown"
    ) {
      event.preventDefault();

      recallHistory(
        -1,
      );
    }
  }


  function editMessage(
    message:
      Message,
  ) {
    setComposerDraft(
      message.content
      === "(attachments)"
        ? ""
        : message.content,
    );

    setAttachments(
      message.attachments
        ?.map(
          item => ({
            ...item,
          }),
        )
      ?? [],
    );

    setLastActivity(
      "message restored to composer",
    );

    window.requestAnimationFrame(
      () =>
        textareaRef.current
          ?.focus(),
    );
  }


  function retryMessage(
    assistant:
      Message,
  ) {
    const index =
      messages.findIndex(
        item =>
          item.id
          === assistant.id,
      );

    if (
      index < 0
    ) {
      return;
    }

    for (
      let cursor =
        index - 1;

      cursor >= 0;

      cursor -= 1
    ) {
      const candidate =
        messages[
          cursor
        ];

      if (
        candidate.role
        === "user"
      ) {
        setMessages(
          messages.slice(
            0,
            cursor,
          ),
        );

        setLastActivity(
          "conversation reset to retry point",
        );

        void send(
          candidate.content
          === "(attachments)"
            ? ""
            : candidate.content,

          candidate.attachments
          ?? [],
        );

        return;
      }
    }
  }


  function clearConversation() {
    abortRef.current
      ?.abort();

    setMessages(
      [],
    );

    setAttachments(
      [],
    );

    localStorage.removeItem(
      storageKey,
    );

    setError(
      "",
    );

    setLastActivity(
      "local chat projection cleared",
    );
  }


  function newConversation() {
    clearConversation();

    setComposerDraft(
      "",
    );

    localStorage.removeItem(
      draftKey,
    );

    setLastActivity(
      "new palaver conversation",
    );
  }


  function exportConversation() {
    const payload =
      JSON.stringify(
        {
          exported_at:
            new Date()
              .toISOString(),

          surface:
            "palaver",

          authority_effect:
            "none",

          messages,
        },
        null,
        2,
      );

    const blob =
      new Blob(
        [
          payload,
        ],
        {
          type:
            "application/json",
        },
      );

    const url =
      URL.createObjectURL(
        blob,
      );

    const anchor =
      document.createElement(
        "a",
      );

    anchor.href =
      url;

    anchor.download =
      (
        "palaver-chat-"
        + Date.now()
        + ".json"
      );

    anchor.click();

    window.setTimeout(
      () =>
        URL.revokeObjectURL(
          url,
        ),
      1000,
    );
  }


  function unavailable(
    tool:
      PalaverChatTool,

    label:
      string,
  ) {
    const next =
      rememberTool(
        tool,
      );

    setRecentTools(
      next,
    );

    setError(
      (
        label
        + " is represented in Palaver, "
        + "but its backend capability "
        + "is not currently connected."
      ),
    );

    setLastActivity(
      (
        label
        + " requested but unavailable"
      ),
    );

    setMenuOpen(
      false,
    );
  }


  function toolSelected(
    tool:
      PalaverChatTool,
  ) {
    setRecentTools(
      rememberTool(
        tool,
      ),
    );

    switch (
      tool
    ) {
      case "files":
        setMenuOpen(
          false,
        );

        fileInputRef.current
          ?.click();

        return;

      case "image":
        setMenuOpen(
          false,
        );

        imageInputRef.current
          ?.click();

        return;

      case "camera":
        setMenuOpen(
          false,
        );

        cameraInputRef.current
          ?.click();

        return;

      case "clipboard":
        void pasteClipboard();

        return;

      case "study":
        setMode(
          "study",
        );

        setMenuOpen(
          false,
        );

        setLastActivity(
          "study mode selected",
        );

        return;

      case "terminal":
        setMenuOpen(
          false,
        );

        setActive(
          "terminal",
        );

        return;

      case "memory":
        setMenuOpen(
          false,
        );

        setActive(
          "memory",
        );

        return;

      case "source-search":
        setMenuOpen(
          false,
        );

        setActive(
          "search",
        );

        return;

      case "create-image":
        unavailable(
          tool,
          "create image",
        );

        return;

      case "plugins":
        unavailable(
          tool,
          "plugins",
        );

        return;

      case "web-search":
        unavailable(
          tool,
          "web search",
        );

        return;

      case "deep-research":
        unavailable(
          tool,
          "deep research",
        );

        return;

      case "voice":
        unavailable(
          tool,
          "voice",
        );

        return;
    }
  }


  return (
    <section
      className={
        dragging
          ? (
            "chat-observatory "
            + "chat-dragging"
          )
          : "chat-observatory"
      }
      onDragEnter={
        event => {
          event.preventDefault();

          setDragging(
            true,
          );
        }
      }
      onDragOver={
        event => {
          event.preventDefault();

          setDragging(
            true,
          );
        }
      }
      onDragLeave={
        event => {
          event.preventDefault();

          if (
            event.currentTarget
            === event.target
          ) {
            setDragging(
              false,
            );
          }
        }
      }
      onDrop={
        handleDrop
      }
    >
      {dragging
      && (
        <div
          className={
            "chat-drop-overlay"
          }
        >
          <FilePlus2
            size={
              28
            }
          />

          <strong>
            drop files into palaver
          </strong>
        </div>
      )}

      <header
        className={
          "chat-hero"
        }
      >
        <div
          className={
            "chat-hero-brand"
          }
        >
          <div
            className={
              "chat-sigil"
            }
          >
            <MessageSquareText
              size={
                18
              }
            />
          </div>

          <div>
            <p>
              conversation /
              cognition /
              development
            </p>

            <h1>
              palaver
            </h1>
          </div>
        </div>

        <div
          className={
            "chat-hero-status"
          }
        >
          <span
            className={
              (
                "runtime-light "
                + `runtime-${health}`
              )
            }
          />

          <span>
            {health}
          </span>

          <button
            type="button"
            onClick={
              exportConversation
            }
            title={
              "Export conversation"
            }
          >
            <Download
              size={
                14
              }
            />
          </button>

          <button
            type="button"
            onClick={
              newConversation
            }
            title={
              "New conversation"
            }
          >
            <Plus
              size={
                14
              }
            />
          </button>

          <button
            type="button"
            onClick={
              clearConversation
            }
            title={
              "Clear local conversation"
            }
          >
            <Trash2
              size={
                14
              }
            />
          </button>
        </div>
      </header>

      <div
        className={
          "chat-stage"
        }
      >
        {messages.length
        === 0
        && (
          <motion.div
            className={
              "chat-empty"
            }
            initial={{
              opacity:
                0,

              scale:
                .985,
            }}
            animate={{
              opacity:
                1,

              scale:
                1,
            }}
          >
            <div
              className={
                "chat-empty-orbit"
              }
            >
              <Bot
                size={
                  26
                }
              />
            </div>

            <span>
              cognitive workstation
            </span>

            <h2>
              Converse with Savant.
            </h2>

            <p>
              Palaver owns conversation.
              Envoy projects persona.
              Opus executes inference.
              Coda remains mutation owner.
            </p>

            <div
              className={
                "chat-empty-actions"
              }
            >
              <button
                type="button"
                onClick={
                  () =>
                    void send(
                      (
                        "Show the current active "
                        + "Niche task and only the "
                        + "minimum context required "
                        + "to continue it."
                      ),
                    )
                }
              >
                active work
              </button>

              <button
                type="button"
                onClick={
                  () =>
                    void send(
                      (
                        "Give me a concise runtime "
                        + "status for Palaver, Envoy, "
                        + "Opus, Niche, Coda, and Scrybe."
                      ),
                    )
                }
              >
                runtime
              </button>
            </div>
          </motion.div>
        )}

        <div
          className={
            "chat-thread"
          }
        >
          <AnimatePresence
            initial={
              false
            }
          >
            {messages.map(
              message => (
                <MessageCard
                  key={
                    message.id
                  }
                  message={
                    message
                  }
                  onEdit={
                    editMessage
                  }
                  onRetry={
                    retryMessage
                  }
                  personas={
                    personas
                  }
                  personaId={
                    personaId
                  }
                />
              ),
            )}
          </AnimatePresence>

          {running
          && (
            <motion.div
              className={
                "chat-thinking"
              }
              initial={{
                opacity:
                  0,
              }}
              animate={{
                opacity:
                  1,
              }}
            >
              <LoaderCircle
                size={
                  14
                }
                className={
                  "spin"
                }
              />

              <span>
                opus executing
              </span>
            </motion.div>
          )}

          <div
            ref={
              bottomRef
            }
          />
        </div>
      </div>

      <form
        className={
          "chat-composer"
        }
        onSubmit={
          submit
        }
      >
        {attachments.length
        > 0
        && (
          <div
            className={
              "composer-attachments"
            }
          >
            {attachments.map(
              item => (
                <article
                  key={
                    item.id
                  }
                  className={
                    (
                      "composer-attachment "
                      + item.state
                    )
                  }
                >
                  {item.previewUrl
                  && item.type
                    .startsWith(
                      "image/",
                    )
                    ? (
                      <img
                        src={
                          item.previewUrl
                        }
                        alt=""
                      />
                    )
                    : (
                      <span
                        className={
                          "composer-attachment-icon"
                        }
                      >
                        {item.type
                          .startsWith(
                            "image/",
                          )
                          ? (
                            <Image
                              size={
                                15
                              }
                            />
                          )
                          : (
                            <FileText
                              size={
                                15
                              }
                            />
                          )}
                      </span>
                    )}

                  <div>
                    <strong>
                      {item.name}
                    </strong>

                    <span>
                      {humanBytes(
                        item.size,
                      )}
                      {" · "}
                      {item.state}
                    </span>

                    {item.error
                    && (
                      <small>
                        {item.error}
                      </small>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={
                      () =>
                        removeAttachment(
                          item.id,
                        )
                    }
                    title={
                      "Remove attachment"
                    }
                  >
                    <X
                      size={
                        13
                      }
                    />
                  </button>
                </article>
              ),
            )}
          </div>
        )}

        <div
          className={
            "composer-context"
          }
        >
          <label
            className={
              "composer-persona"
            }
            title={
              "Envoy persona used for this conversation"
            }
          >
            <Bot
              size={
                12
              }
            />

            <select
              value={
                personaId
              }
              onChange={
                event =>
                  setPersonaId(
                    event.target.value,
                  )
              }
              aria-label={
                "Persona"
              }
            >
              {personas.map(
                persona => {
                  const id =
                    persona.persona_id
                    || "orobouros";

                  return (
                    <option
                      key={
                        id
                      }
                      value={
                        id
                      }
                    >
                      {persona.display_name
                      || id}
                    </option>
                  );
                },
              )}
            </select>
          </label>

          <button
            className={
              "composer-voice-muted"
            }
            type="button"
            disabled
            aria-label={
              "Persona voice muted"
            }
            title={
              "Voice is intentionally locked muted until persona voices are implemented"
            }
          >
            <VolumeX
              size={
                13
              }
            />
          </button>
        </div>

        <div
          className={
            "composer-core"
          }
        >
          <div
            className={
              "composer-plus-wrap"
            }
          >
            <ChatToolSurface
              open={
                menuOpen
              }
              onOpenChange={
                setMenuOpen
              }
            >
              <ChatToolMenu
                onTool={
                  toolSelected
                }
                capabilities={
                  capabilities
                }
                recentTools={
                  recentTools
                }
              />

              {recent.length
              > 0
              && (
                <section
                  className={
                    "palaver-tool-group"
                  }
                >
                  <header>
                    recent material
                  </header>

                  {recent
                    .slice(
                      0,
                      4,
                    )
                    .map(
                      item => (
                        <button
                          type="button"
                          className={
                            "palaver-tool-item"
                          }
                          key={
                            item.id
                          }
                          onClick={
                            () =>
                              addRecent(
                                item,
                              )
                          }
                        >
                          <span
                            className={
                              "palaver-tool-icon"
                            }
                          >
                            <FileText
                              size={
                                16
                              }
                            />
                          </span>

                          <span
                            className={
                              "palaver-tool-copy"
                            }
                          >
                            <strong>
                              {item.name}
                            </strong>

                            <small>
                              {humanBytes(
                                item.size,
                              )}
                            </small>
                          </span>
                        </button>
                      ),
                    )}
                </section>
              )}

              <section
                className={
                  "palaver-tool-group"
                }
              >
                <header>
                  working mode
                </header>

                {(
                  [
                    "standard",
                    "develop",
                    "inspect",
                    "study",
                    "minimum",
                  ] as ChatMode[]
                ).map(
                  value => (
                    <button
                      type="button"
                      className={
                        (
                          "palaver-tool-item "
                          + (
                            mode
                            === value
                              ? "selected"
                              : ""
                          )
                        )
                      }
                      key={
                        value
                      }
                      onClick={
                        () => {
                          setMode(
                            value,
                          );

                          setMenuOpen(
                            false,
                          );
                        }
                      }
                    >
                      <span
                        className={
                          "palaver-tool-icon"
                        }
                      >
                        <Sparkles
                          size={
                            16
                          }
                        />
                      </span>

                      <span
                        className={
                          "palaver-tool-copy"
                        }
                      >
                        <strong>
                          {modeLabels[
                            value
                          ]}
                        </strong>

                        <small>
                          {value
                          === "standard"
                            ? (
                              "normal Palaver behavior"
                            )
                            : modeInstructions[
                                value
                              ]}
                        </small>
                      </span>

                      {mode
                      === value
                      && (
                        <span
                          className={
                            (
                              "palaver-capability-state "
                              + "state-connected"
                            )
                          }
                        >
                          <Check
                            size={
                              10
                            }
                          />
                          active
                        </span>
                      )}
                    </button>
                  ),
                )}
              </section>
            </ChatToolSurface>
          </div>

          <textarea
            ref={
              textareaRef
            }
            value={
              composerDraft
            }
            onChange={
              event =>
                setComposerDraft(
                  event.target.value,
                )
            }
            onKeyDown={
              keyDown
            }
            onPaste={
              event =>
                void composerPaste(
                  event,
                )
            }
            placeholder={
              (
                "Ask Palaver, develop Savant, "
                + "inspect context, or stage work…"
              )
            }
            rows={
              1
            }
            aria-label={
              "Message Palaver"
            }
          />

          {running
            ? (
              <button
                className={
                  "composer-send composer-stop"
                }
                type="button"
                onClick={
                  stop
                }
                title={
                  "Stop generation"
                }
              >
                <Square
                  size={
                    15
                  }
                />
              </button>
            )
            : (
              <button
                className={
                  "composer-send"
                }
                type="submit"
                disabled={
                  (
                    !composerDraft
                      .trim()
                    && attachments.length
                    === 0
                  )
                }
                title={
                  "Send · Ctrl/⌘ + Enter"
                }
              >
                <Send
                  size={
                    17
                  }
                />
              </button>
            )}
        </div>

        <footer
          className={
            "composer-footer"
          }
        >
          <span>
            <CornerDownLeft
              size={
                11
              }
            />
            ctrl/⌘ + enter
          </span>

          <span>
            alt + ↑/↓ · recall
          </span>

          <span>
            mode · {mode}
          </span>

          <span>
            context · ~
            {tokenEstimate}
            {" "}
            tokens
          </span>

          {error
          && (
            <span
              className={
                "composer-error"
              }
            >
              {error}
            </span>
          )}

          <span>
            AI output is not authority
          </span>
        </footer>

        <input
          ref={
            fileInputRef
          }
          hidden
          multiple
          type="file"
          onChange={
            fileInput
          }
        />

        <input
          ref={
            imageInputRef
          }
          hidden
          multiple
          type="file"
          accept={
            "image/*"
          }
          onChange={
            fileInput
          }
        />

        <input
          ref={
            cameraInputRef
          }
          hidden
          type="file"
          accept={
            "image/*"
          }
          capture={
            "environment"
          }
          onChange={
            fileInput
          }
        />
      </form>
    </section>
  );
}
