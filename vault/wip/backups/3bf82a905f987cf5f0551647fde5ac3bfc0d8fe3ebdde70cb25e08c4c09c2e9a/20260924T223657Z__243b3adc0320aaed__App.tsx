import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";

type View = "chat" | "files" | "memory" | "runtime";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta?: string;
};

type JsonObject = Record<string, any>;

const css = `
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#edf1f7;background:#080a0e;font-synthesis:none}
*{box-sizing:border-box}
html,body,#root{margin:0;min-width:0;min-height:100%;background:#080a0e}
button,input,textarea{font:inherit}
button{color:inherit}

.palaver{
  min-height:100dvh;
  background:radial-gradient(circle at 50% -18%,#18202b 0,#0b0e13 42%,#07090c 100%);
  display:flex;
  flex-direction:column
}

.top{
  height:62px;
  border-bottom:1px solid #202631;
  background:rgba(9,12,17,.9);
  backdrop-filter:blur(18px);
  display:grid;
  grid-template-columns:1fr auto 1fr;
  align-items:center;
  padding:0 20px;
  position:sticky;
  top:0;
  z-index:20
}

.brand{
  display:flex;
  align-items:center;
  gap:10px
}

.sigil{
  width:31px;
  height:31px;
  border:1px solid #445168;
  border-radius:9px;
  display:grid;
  place-items:center;
  background:#151a22;
  font:700 17px ui-monospace,monospace
}

.brandtext{
  display:flex;
  flex-direction:column
}

.brandtext b{
  font-size:14px;
  letter-spacing:.06em
}

.brandtext small{
  font-size:10px;
  color:#697487
}

.nav{
  display:flex;
  gap:3px;
  border:1px solid #202631;
  border-radius:11px;
  background:#0d1117;
  padding:4px
}

.nav button{
  border:0;
  background:transparent;
  color:#768195;
  padding:7px 11px;
  border-radius:7px;
  cursor:pointer;
  font-size:12px
}

.nav button.on{
  background:#222936;
  color:#f3f6fa
}

.status{
  justify-self:end;
  display:flex;
  align-items:center;
  gap:7px;
  border:1px solid #202631;
  border-radius:999px;
  padding:7px 10px;
  color:#7c8798;
  font-size:11px
}

.dot{
  width:7px;
  height:7px;
  border-radius:50%;
  background:#697386
}

.dot.ok{
  background:#76d3a0;
  box-shadow:0 0 10px rgba(118,211,160,.35)
}

.dot.bad{
  background:#e4777f
}

.chat{
  width:min(900px,100%);
  margin:0 auto;
  flex:1;
  padding:30px 22px 170px
}

.thread{
  display:flex;
  flex-direction:column;
  gap:27px
}

.msg{
  display:grid;
  grid-template-columns:88px minmax(0,1fr);
  gap:8px 18px
}

.who{
  color:#657185;
  font:600 10px/1.5 ui-monospace,monospace;
  text-transform:uppercase;
  letter-spacing:.11em;
  padding-top:3px
}

.body{
  white-space:pre-wrap;
  overflow-wrap:anywhere;
  font-size:15px;
  line-height:1.72;
  color:#d8dee8
}

.msg.user .body{
  color:#f5f7fb
}

.meta{
  grid-column:2;
  color:#566173;
  font:10px/1.5 ui-monospace,monospace
}

.composerWrap{
  position:fixed;
  bottom:0;
  left:50%;
  transform:translateX(-50%);
  width:min(900px,calc(100% - 28px));
  padding:16px 0 18px;
  background:linear-gradient(180deg,transparent,#080a0e 24%)
}

.error{
  margin-bottom:8px;
  padding:9px 12px;
  border:1px solid #623b42;
  border-radius:9px;
  background:#231316;
  color:#e5a0a7;
  font-size:11px;
  white-space:pre-wrap
}

.composer{
  display:flex;
  align-items:flex-end;
  gap:10px;
  border:1px solid #303846;
  border-radius:17px;
  background:rgba(18,22,29,.97);
  padding:9px 9px 9px 16px;
  box-shadow:0 18px 70px rgba(0,0,0,.38)
}

.composer:focus-within{
  border-color:#52627d
}

.composer textarea{
  flex:1;
  border:0;
  outline:0;
  resize:none;
  min-height:38px;
  max-height:190px;
  padding:9px 0;
  background:transparent;
  color:#eef2f7;
  line-height:1.45
}

.composer textarea::placeholder{
  color:#5b6575
}

.send{
  width:40px;
  height:40px;
  border:0;
  border-radius:11px;
  background:#e7ebf2;
  color:#0b0e13;
  font-size:21px;
  cursor:pointer
}

.send:disabled{
  opacity:.3;
  cursor:default
}

.hint{
  display:flex;
  justify-content:space-between;
  padding:7px 5px 0;
  color:#4d5868;
  font-size:10px
}

.utility{
  width:min(1100px,calc(100% - 40px));
  margin:0 auto;
  padding:34px 0
}

.utility.narrow{
  width:min(900px,calc(100% - 40px))
}

.head{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:18px;
  margin-bottom:20px
}

.head h2{
  margin:0;
  font-size:22px
}

.head p{
  margin:6px 0 0;
  color:#6d7889;
  font-size:12px
}

.row{
  display:flex;
  gap:8px
}

.row input{
  flex:1;
  min-width:280px;
  border:1px solid #303846;
  background:#0d1117;
  color:#edf1f7;
  border-radius:8px;
  padding:9px 11px;
  outline:0
}

.action{
  border:1px solid #303846;
  background:#171c24;
  border-radius:8px;
  padding:9px 13px;
  cursor:pointer
}

.panel{
  border:1px solid #202631;
  border-radius:12px;
  background:#0d1015;
  min-height:55vh;
  padding:18px;
  color:#aeb9c8;
  font:11px/1.65 ui-monospace,monospace;
  white-space:pre-wrap;
  overflow:auto;
  overflow-wrap:anywhere
}

.files{
  display:grid;
  grid-template-columns:minmax(250px,.8fr) minmax(0,1.5fr);
  gap:14px
}

.list{
  padding:7px
}

.list button{
  width:100%;
  border:0;
  background:transparent;
  color:#aab4c2;
  text-align:left;
  padding:8px 9px;
  border-radius:7px;
  cursor:pointer;
  overflow-wrap:anywhere
}

.list button:hover{
  background:#171c24;
  color:#eef2f7
}

.thinking{
  opacity:.62
}

.thinking .body{
  letter-spacing:.18em
}

@media(max-width:720px){
  .top{
    height:auto;
    min-height:58px;
    grid-template-columns:1fr auto;
    padding:10px 14px;
    gap:8px
  }

  .brandtext small,
  .status span{
    display:none
  }

  .status{
    padding:7px
  }

  .nav{
    grid-column:1/-1;
    grid-row:2;
    width:100%
  }

  .nav button{
    flex:1
  }

  .chat{
    padding:24px 15px 160px
  }

  .msg{
    grid-template-columns:1fr;
    gap:4px
  }

  .meta{
    grid-column:1
  }

  .who{
    padding:0
  }

  .hint span:first-child{
    display:none
  }

  .head{
    align-items:stretch;
    flex-direction:column
  }

  .row input{
    min-width:0
  }

  .files{
    grid-template-columns:1fr
  }

  .utility{
    width:calc(100% - 28px)
  }
}
`;

function id() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function api(
  path: string,
  options: RequestInit = {},
): Promise<JsonObject> {
  const response = await fetch(path, {
    ...options,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(options.body
        ? {"Content-Type": "application/json"}
        : {}),
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let payload: JsonObject = {};

  if (text.trim()) {
    try {
      payload = JSON.parse(text);
    } catch {
      if (response.ok) {
        payload = {
          ok: true,
          response: text,
        };
      } else {
        payload = {
          ok: false,
          error: text,
        };
      }
    }
  }

  if (!response.ok || payload.ok === false) {
    const detail = payload.diagnostic
      ? `\n${payload.diagnostic}`
      : "";

    const error = new Error(
      `${
        payload.error ||
        payload.response ||
        `HTTP ${response.status}`
      }${detail}`,
    );

    (error as any).code = payload.error_code;
    throw error;
  }

  return payload;
}

function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, running]);

  async function send() {
    const message = draft.trim();

    if (!message || running) {
      return;
    }

    const user: ChatMessage = {
      id: id(),
      role: "user",
      content: message,
    };

    setMessages((current) => [
      ...current,
      user,
    ]);

    setDraft("");
    setError("");
    setRunning(true);

    try {
      const payload = await api(
        "/api/chat",
        {
          method: "POST",
          body: JSON.stringify({
            message,
          }),
        },
      );

      const content = String(
        payload.response ??
        payload.answer ??
        "",
      ).trim();

      if (!content) {
        throw new Error(
          "Palaver returned no response text.",
        );
      }

      const meta = [
        payload.persona_id
          ? `persona ${payload.persona_id}`
          : null,

        payload.provider_owner
          ? `orchestration ${payload.provider_owner}`
          : null,

        payload.context_receipt?.memory_count != null
          ? `memory ${payload.context_receipt.memory_count}`
          : null,
      ]
        .filter(Boolean)
        .join(" · ");

      setMessages((current) => [
        ...current,
        {
          id: id(),
          role: "assistant",
          content,
          meta,
        },
      ]);
    } catch (reason) {
      const messageText =
        reason instanceof Error
          ? reason.message
          : String(reason);

      setError(messageText);

      setMessages((current) => [
        ...current,
        {
          id: id(),
          role: "assistant",
          content: `Request failed: ${messageText}`,
          meta: "authority unchanged",
        },
      ]);
    } finally {
      setRunning(false);
    }
  }

  function submit(
    event: FormEvent,
  ) {
    event.preventDefault();
    void send();
  }

  function keydown(
    event: KeyboardEvent<HTMLTextAreaElement>,
  ) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <main className="chat">
      <section
        className="thread"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <article className="msg assistant">
            <div className="who">
              orobouros
            </div>

            <div className="body">
              Palaver is ready. Conversation belongs to
              Palaver, orchestration to Opus, and persona
              to Envoy.
            </div>
          </article>
        )}

        {messages.map((message) => (
          <article
            className={`msg ${message.role}`}
            key={message.id}
          >
            <div className="who">
              {message.role === "user"
                ? "you"
                : "orobouros"}
            </div>

            <div className="body">
              {message.content}
            </div>

            {message.meta && (
              <div className="meta">
                {message.meta}
              </div>
            )}
          </article>
        ))}

        {running && (
          <article className="msg assistant thinking">
            <div className="who">
              orobouros
            </div>

            <div className="body">
              ● ● ●
            </div>
          </article>
        )}

        <div ref={bottom} />
      </section>

      <form
        className="composerWrap"
        onSubmit={submit}
      >
        {error && (
          <div className="error">
            {error}
          </div>
        )}

        <div className="composer">
          <textarea
            autoFocus
            rows={1}
            value={draft}
            onChange={(event) =>
              setDraft(event.target.value)
            }
            onKeyDown={keydown}
            placeholder="Message Orobouros…"
            disabled={running}
          />

          <button
            className="send"
            type="submit"
            disabled={
              running ||
              !draft.trim()
            }
          >
            {running ? "…" : "↑"}
          </button>
        </div>

        <div className="hint">
          <span>
            Enter to send · Shift+Enter for a new line
          </span>

          <span>
            Palaver · Opus · Envoy
          </span>
        </div>
      </form>
    </main>
  );
}

function Files() {
  const [path, setPath] = useState("");
  const [tree, setTree] = useState<any>(null);
  const [file, setFile] = useState<any>(null);
  const [error, setError] = useState("");

  async function browse(
    next = path,
  ) {
    try {
      setError("");

      setTree(
        await api(
          `/api/tree?path=${encodeURIComponent(
            next,
          )}`,
        ),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : String(reason),
      );
    }
  }

  async function open(
    filePath: string,
  ) {
    try {
      setError("");

      setFile(
        await api(
          `/api/file?path=${encodeURIComponent(
            filePath,
          )}`,
        ),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : String(reason),
      );
    }
  }

  useEffect(() => {
    void browse("");
  }, []);

  const entries =
    Array.isArray(tree)
      ? tree
      : Array.isArray(tree?.tree)
        ? tree.tree
        : Array.isArray(tree?.entries)
          ? tree.entries
          : Array.isArray(tree?.children)
            ? tree.children
            : [];

  return (
    <main className="utility">
      <header className="head">
        <div>
          <h2>
            filesystem
          </h2>

          <p>
            Inspect Savant directly without turning
            Palaver into an IDE.
          </p>
        </div>

        <div className="row">
          <input
            value={path}
            onChange={(event) =>
              setPath(event.target.value)
            }
            placeholder="path"
          />

          <button
            className="action"
            onClick={() =>
              void browse()
            }
          >
            open
          </button>
        </div>
      </header>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <div className="files">
        <section className="panel list">
          {entries.map(
            (
              entry: any,
              index: number,
            ) => {
              const filePath = String(
                entry?.path ??
                entry?.name ??
                entry,
              );

              return (
                <button
                  key={`${filePath}-${index}`}
                  onClick={() =>
                    void open(filePath)
                  }
                >
                  {filePath}
                </button>
              );
            },
          )}

          {!entries.length &&
            "No entries returned."}
        </section>

        <pre className="panel">
          {file
            ? String(
                file.content ??
                JSON.stringify(
                  file,
                  null,
                  2,
                ),
              )
            : "Select a file."}
        </pre>
      </div>
    </main>
  );
}

function Memory() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function search() {
    if (!query.trim()) {
      return;
    }

    try {
      setError("");

      setResult(
        await api(
          `/api/memory/search?q=${encodeURIComponent(
            query.trim(),
          )}`,
        ),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : String(reason),
      );
    }
  }

  return (
    <main className="utility narrow">
      <header className="head">
        <div>
          <h2>
            memory
          </h2>

          <p>
            Search Palaver's persistent memory surface.
          </p>
        </div>
      </header>

      <div className="row">
        <input
          value={query}
          onChange={(event) =>
            setQuery(event.target.value)
          }
          onKeyDown={(event) => {
            if (
              event.key === "Enter"
            ) {
              void search();
            }
          }}
          placeholder="Search memory…"
        />

        <button
          className="action"
          onClick={() =>
            void search()
          }
        >
          search
        </button>
      </div>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <pre
        className="panel"
        style={{
          marginTop: 14,
        }}
      >
        {result
          ? JSON.stringify(
              result,
              null,
              2,
            )
          : "No search yet."}
      </pre>
    </main>
  );
}

function Runtime({
  health,
  error,
  refresh,
}: {
  health: any;
  error: string;
  refresh: () => void;
}) {
  return (
    <main className="utility narrow">
      <header className="head">
        <div>
          <h2>
            runtime
          </h2>

          <p>
            Operational truth without dashboard clutter.
          </p>
        </div>

        <button
          className="action"
          onClick={refresh}
        >
          refresh
        </button>
      </header>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <pre className="panel">
        {health
          ? JSON.stringify(
              health,
              null,
              2,
            )
          : "Loading runtime…"}
      </pre>
    </main>
  );
}

export default function App() {
  const [view, setView] =
    useState<View>("chat");

  const [health, setHealth] =
    useState<any>(null);

  const [
    healthError,
    setHealthError,
  ] = useState("");

  async function refresh() {
    try {
      setHealthError("");

      setHealth(
        await api(
          "/api/runtime",
        ),
      );
    } catch (reason) {
      setHealthError(
        reason instanceof Error
          ? reason.message
          : String(reason),
      );
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div className="palaver">
      <style>
        {css}
      </style>

      <header className="top">
        <div className="brand">
          <div className="sigil">
            p
          </div>

          <div className="brandtext">
            <b>
              palaver
            </b>

            <small>
              ouroboros interface
            </small>
          </div>
        </div>

        <nav className="nav">
          {(
            [
              "chat",
              "files",
              "memory",
              "runtime",
            ] as View[]
          ).map((item) => (
            <button
              key={item}
              className={
                view === item
                  ? "on"
                  : ""
              }
              onClick={() =>
                setView(item)
              }
            >
              {item}
            </button>
          ))}
        </nav>

        <div
          className="status"
          title={
            healthError ||
            "Palaver runtime"
          }
        >
          <span
            className={`dot ${
              healthError
                ? "bad"
                : health
                  ? "ok"
                  : ""
            }`}
          />

          <span>
            {healthError
              ? "offline"
              : health
                ? "connected"
                : "connecting"}
          </span>
        </div>
      </header>

      {view === "chat" && (
        <Chat />
      )}

      {view === "files" && (
        <Files />
      )}

      {view === "memory" && (
        <Memory />
      )}

      {view === "runtime" && (
        <Runtime
          health={health}
          error={healthError}
          refresh={() =>
            void refresh()
          }
        />
      )}
    </div>
  );
}
