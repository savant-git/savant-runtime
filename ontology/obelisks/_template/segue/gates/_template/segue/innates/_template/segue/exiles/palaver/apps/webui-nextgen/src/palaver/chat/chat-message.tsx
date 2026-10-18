import {memo,useMemo,useState} from "react"
import {motion} from "framer-motion"
import {Bot,UserRound,Pencil,Check,Clipboard,RefreshCw,TerminalSquare,Image,FileText,Code2} from "../components/savant-glyphs"
import {useWorkspaceStore} from "../state/workspace-store"
import {extractCodeBlocks,RichMessage} from "./chat-content"
import {humanBytes} from "./attachments"
import type {Message} from "./chat-types"
import UrgeControl from "./urge-control"
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
  const setActive=useWorkspaceStore(state=>state.setActive);
  const stageTerminal=useWorkspaceStore(state=>state.stageTerminal);
  const setLastActivity=useWorkspaceStore(state=>state.setLastActivity);

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

      {message.contextProjection && (
        <details className="chat-trace chat-message-details">
          <summary>conversation context</summary>
          <p>
            prior turns included: {message.contextProjection.included}
            {" · "}omitted by bounds: {message.contextProjection.omitted}
          </p>
          <p>quoted conversation projection; AI output is not authority</p>
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



export default memo(MessageCard)
