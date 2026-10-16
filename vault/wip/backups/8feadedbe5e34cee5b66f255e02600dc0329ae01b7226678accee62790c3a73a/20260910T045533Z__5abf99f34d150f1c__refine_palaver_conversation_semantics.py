#!/usr/bin/env python3

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


SCHEMA = "savant.palaver.conversation-semantics-refinement.v1"

ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "palaver/apps/webui-nextgen"
)

PALAVER = ROOT / "src/palaver/Palaver.tsx"
CONVERSATION_TOOLS = (
    ROOT / "src/palaver/PalaverConversationTools.tsx"
)
CONVERSATION_HOOK = (
    ROOT / "src/palaver/usePalaverConversation.ts"
)


class RefinementError(RuntimeError):
    pass


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> tuple[str, bool]:
    if new in text:
        return text, False

    count = text.count(old)

    if count != 1:
        raise RefinementError(
            f"{label}: expected exactly one source anchor, found {count}"
        )

    return text.replace(old, new, 1), True


def write_atomic(
    path: Path,
    text: str,
    mode: int,
) -> None:
    temporary = path.with_name(
        f".{path.name}.palaver-refine.tmp"
    )

    temporary.write_text(
        text,
        encoding="utf-8",
    )

    os.chmod(
        temporary,
        stat.S_IMODE(mode),
    )

    os.replace(
        temporary,
        path,
    )


def refine_palaver() -> bool:
    text = PALAVER.read_text(
        encoding="utf-8",
    )

    original = text

    text, _ = replace_once(
        text,
        '''import {
  FormEvent,
  KeyboardEvent,
} from "react"
''',
        '''import type {
  FormEvent,
  KeyboardEvent,
} from "react"
''',
        "react type imports",
    )

    text, _ = replace_once(
        text,
        '''    setDraft(
      message.role === "assistant"
        ? "Take this in a different direction: "
        : "",
    )
''',
        '''    /*
     * Branch creation must not inject semantic substance.
     * The new path inherits only the selected conversation state.
     */
''',
        "branch semantic injection",
    )

    quote_old = '''  const quoteMessage = useCallback(
    (message: PalaverMessageRecord) => {
      setDraft(
        `${draft}${draft ? "\\n\\n" : ""}> ${message.body.replace(
          /\\n/g,
          "\\n> ",
        )}\\n\\n`,
      )

      focusComposer()
    },
    [draft, focusComposer],
  )
'''

    quote_new = '''  const quoteMessage = useCallback(
    (message: PalaverMessageRecord) => {
      const source = message.body
        .split("\\n")
        .slice(0, 8)
        .join("\\n")
        .slice(0, 600)

      const truncated =
        source.length < message.body.length

      const excerpt =
        `${source}${truncated ? "…" : ""}`

      setDraft(
        `${draft}${draft ? "\\n\\n" : ""}> ${excerpt.replace(
          /\\n/g,
          "\\n> ",
        )}\\n\\n`,
      )

      focusComposer()
    },
    [draft, focusComposer],
  )
'''

    text, _ = replace_once(
        text,
        quote_old,
        quote_new,
        "bounded quote insertion",
    )

    if text == original:
        return False

    write_atomic(
        PALAVER,
        text,
        PALAVER.stat().st_mode,
    )

    return True


def refine_conversation_tools() -> bool:
    text = CONVERSATION_TOOLS.read_text(
        encoding="utf-8",
    )

    original = text

    text, _ = replace_once(
        text,
        'import { ChangeEvent, useRef, useState } from "react"\n',
        (
            'import { useRef, useState } from "react"\n'
            'import type { ChangeEvent } from "react"\n'
        ),
        "conversation tools type import",
    )

    if text == original:
        return False

    write_atomic(
        CONVERSATION_TOOLS,
        text,
        CONVERSATION_TOOLS.stat().st_mode,
    )

    return True


def refine_conversation_hook() -> bool:
    text = CONVERSATION_HOOK.read_text(
        encoding="utf-8",
    )

    original = text

    text, _ = replace_once(
        text,
        '''import {
  Dispatch,
  SetStateAction,
''',
        '''import {
''',
        "conversation hook runtime type imports",
    )

    anchor = 'from "react"\n'

    if (
        'import type { Dispatch, SetStateAction } from "react"\n'
        not in text
    ):
        index = text.find(anchor)

        if index < 0:
            raise RefinementError(
                "conversation hook: react import terminator not found"
            )

        index += len(anchor)

        text = (
            text[:index]
            + 'import type { Dispatch, SetStateAction } from "react"\n'
            + text[index:]
        )

    if text == original:
        return False

    write_atomic(
        CONVERSATION_HOOK,
        text,
        CONVERSATION_HOOK.stat().st_mode,
    )

    return True


def main() -> int:
    required = (
        PALAVER,
        CONVERSATION_TOOLS,
        CONVERSATION_HOOK,
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise RefinementError(
            "required palaver source missing: "
            + ", ".join(missing)
        )

    changed = {
        "palaver": refine_palaver(),
        "conversation_tools":
            refine_conversation_tools(),
        "conversation_hook":
            refine_conversation_hook(),
    }

    print(
        {
            "schema": SCHEMA,
            "changed": changed,
        }
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RefinementError as exc:
        print(
            f"{SCHEMA}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
