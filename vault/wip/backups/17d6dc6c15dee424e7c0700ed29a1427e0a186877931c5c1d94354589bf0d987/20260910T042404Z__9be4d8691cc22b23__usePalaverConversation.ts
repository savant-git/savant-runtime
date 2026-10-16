import {
  Dispatch,
  SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import type {
  PalaverMessageRecord,
} from "./PalaverMessage"
import type {
  ConversationBranch,
} from "./PalaverBranches"

const schema =
  "savant.palaver.local-conversation.v1"

const storageKey =
  "savant.palaver.local-conversation.v1"

const channelName =
  "savant.palaver.local-conversation.v1"

const maxMessagesPerPath = 500
const maxBranches = 100
const maxMessageCharacters = 250000
const maxBranchLabelCharacters = 120

type PersistedConversation = {
  schema: typeof schema
  revision: number
  savedAt: number
  activeBranchId: string | null
  mainMessages: PalaverMessageRecord[]
  branches: ConversationBranch[]
}

type ConversationUpdate =
  | PalaverMessageRecord[]
  | ((
      current: PalaverMessageRecord[],
    ) => PalaverMessageRecord[])

function uid(
  prefix: string,
) {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID ===
      "function"
  ) {
    return `${prefix}:${crypto.randomUUID()}`
  }

  return `${prefix}:${Date.now()}:${Math.random()
    .toString(36)
    .slice(2)}`
}

function finiteNumber(
  value: unknown,
): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value)
  )
}

function nonEmptyString(
  value: unknown,
): value is string {
  return (
    typeof value === "string" &&
    value.length > 0
  )
}

function nullableString(
  value: unknown,
): value is string | null {
  return (
    value === null ||
    typeof value === "string"
  )
}

function sanitizeMessage(
  value: unknown,
): PalaverMessageRecord | null {
  if (
    !value ||
    typeof value !== "object"
  ) {
    return null
  }

  const candidate =
    value as Record<
      string,
      unknown
    >

  if (
    !nonEmptyString(
      candidate.id,
    ) ||
    (
      candidate.role !==
        "user" &&
      candidate.role !==
        "assistant"
    ) ||
    typeof candidate.body !==
      "string" ||
    !finiteNumber(
      candidate.createdAt,
    )
  ) {
    return null
  }

  const body =
    candidate.body.slice(
      0,
      maxMessageCharacters,
    )

  const trace =
    typeof candidate.trace ===
      "string"
      ? candidate.trace.slice(
          0,
          maxMessageCharacters,
        )
      : undefined

  const parentId =
    nullableString(
      candidate.parentId,
    )
      ? candidate.parentId
      : null

  return {
    id: candidate.id,
    role: candidate.role,
    body,
    trace,
    createdAt:
      candidate.createdAt,
    parentId,
  }
}

function sanitizeMessages(
  value: unknown,
) {
  if (!Array.isArray(value)) {
    return []
  }

  const seen =
    new Set<string>()

  const messages:
    PalaverMessageRecord[] =
    []

  for (
    const candidate of value
  ) {
    const message =
      sanitizeMessage(candidate)

    if (
      !message ||
      seen.has(message.id)
    ) {
      continue
    }

    seen.add(message.id)
    messages.push(message)

    if (
      messages.length >=
      maxMessagesPerPath
    ) {
      break
    }
  }

  return messages
}

function sanitizeBranch(
  value: unknown,
): ConversationBranch | null {
  if (
    !value ||
    typeof value !== "object"
  ) {
    return null
  }

  const candidate =
    value as Record<
      string,
      unknown
    >

  if (
    !nonEmptyString(
      candidate.id,
    ) ||
    !nonEmptyString(
      candidate.sourceMessageId,
    ) ||
    typeof candidate.label !==
      "string" ||
    !finiteNumber(
      candidate.createdAt,
    )
  ) {
    return null
  }

  return {
    id:
      candidate.id,
    sourceMessageId:
      candidate.sourceMessageId,
    label:
      candidate.label
        .replace(
          /\s+/g,
          " ",
        )
        .trim()
        .slice(
          0,
          maxBranchLabelCharacters,
        ),
    createdAt:
      candidate.createdAt,
    messages:
      sanitizeMessages(
        candidate.messages,
      ),
  }
}

function sanitizeBranches(
  value: unknown,
) {
  if (!Array.isArray(value)) {
    return []
  }

  const branches:
    ConversationBranch[] =
    []

  const seen =
    new Set<string>()

  for (
    const candidate of value
  ) {
    const branch =
      sanitizeBranch(candidate)

    if (
      !branch ||
      seen.has(branch.id)
    ) {
      continue
    }

    seen.add(branch.id)
    branches.push(branch)

    if (
      branches.length >=
      maxBranches
    ) {
      break
    }
  }

  return branches
}

function sanitizePayload(
  value: unknown,
): PersistedConversation | null {
  if (
    !value ||
    typeof value !== "object"
  ) {
    return null
  }

  const candidate =
    value as Record<
      string,
      unknown
    >

  if (
    candidate.schema !== schema
  ) {
    return null
  }

  const branches =
    sanitizeBranches(
      candidate.branches,
    )

  let activeBranchId =
    nullableString(
      candidate.activeBranchId,
    )
      ? candidate.activeBranchId
      : null

  if (
    activeBranchId !== null &&
    !branches.some(
      (branch) =>
        branch.id ===
        activeBranchId,
    )
  ) {
    activeBranchId = null
  }

  return {
    schema,
    revision:
      finiteNumber(
        candidate.revision,
      )
        ? candidate.revision
        : 0,
    savedAt:
      finiteNumber(
        candidate.savedAt,
      )
        ? candidate.savedAt
        : 0,
    activeBranchId,
    mainMessages:
      sanitizeMessages(
        candidate.mainMessages,
      ),
    branches,
  }
}

function readPersisted():
  | PersistedConversation
  | null {
  try {
    const raw =
      localStorage.getItem(
        storageKey,
      )

    if (!raw) {
      return null
    }

    return sanitizePayload(
      JSON.parse(raw),
    )
  } catch {
    return null
  }
}

function branchLabel(
  message:
    PalaverMessageRecord,
) {
  const compact =
    message.body
      .replace(
        /\s+/g,
        " ",
      )
      .trim()

  if (
    compact.length <= 52
  ) {
    return (
      compact ||
      "conversation branch"
    )
  }

  return `${compact.slice(
    0,
    49,
  )}…`
}

function applyUpdate(
  current:
    PalaverMessageRecord[],
  update:
    ConversationUpdate,
) {
  const next =
    typeof update ===
      "function"
      ? update(current)
      : update

  return sanitizeMessages(
    next,
  )
}

export function usePalaverConversation() {
  const initial =
    useMemo(
      () => readPersisted(),
      [],
    )

  const [
    mainMessages,
    setMainMessages,
  ] = useState<
    PalaverMessageRecord[]
  >(
    initial?.mainMessages ??
      [],
  )

  const [
    branches,
    setBranches,
  ] = useState<
    ConversationBranch[]
  >(
    initial?.branches ?? [],
  )

  const [
    activeBranchId,
    setActiveBranchId,
  ] = useState<
    string | null
  >(
    initial?.activeBranchId ??
      null,
  )

  const revisionRef =
    useRef(
      initial?.revision ??
        0,
    )

  const applyingRemoteRef =
    useRef(false)

  const channelRef =
    useRef<
      BroadcastChannel | null
    >(null)

  const messages =
    useMemo(() => {
      if (
        activeBranchId ===
        null
      ) {
        return mainMessages
      }

      return (
        branches.find(
          (branch) =>
            branch.id ===
            activeBranchId,
        )?.messages ?? []
      )
    }, [
      activeBranchId,
      branches,
      mainMessages,
    ])

  const setMessages:
    Dispatch<
      SetStateAction<
        PalaverMessageRecord[]
      >
    > = useCallback(
      (
        update,
      ) => {
        if (
          activeBranchId ===
          null
        ) {
          setMainMessages(
            (current) =>
              applyUpdate(
                current,
                update,
              ),
          )

          return
        }

        setBranches(
          (current) =>
            current.map(
              (branch) => {
                if (
                  branch.id !==
                  activeBranchId
                ) {
                  return branch
                }

                return {
                  ...branch,
                  messages:
                    applyUpdate(
                      branch.messages,
                      update,
                    ),
                }
              },
            ),
        )
      },
      [activeBranchId],
    )

  const createBranch =
    useCallback(
      (
        source:
          PalaverMessageRecord,
      ) => {
        const sourceIndex =
          messages.findIndex(
            (message) =>
              message.id ===
              source.id,
          )
