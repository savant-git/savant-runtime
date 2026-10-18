import type {Message,ChatMode} from "./chat-types"
import type {ChatAttachment} from "./attachments"
import {persistedAttachment} from "./attachments"
import type {PalaverChatTool} from "./chat-tool-menu"
import {storageKey,modeKey,recentKey,recentToolKey,historyKey} from "./chat-configuration"
export function isChatMode(
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


export function loadMode():
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


export function messageId() {
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


export function safeJson(
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


export function loadMessages():
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


export function saveMessages(
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


export function loadRecent():
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


export function saveRecent(
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


export function loadRecentTools():
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


export function rememberTool(
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


export function loadPromptHistory():
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


export function savePromptHistory(
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
