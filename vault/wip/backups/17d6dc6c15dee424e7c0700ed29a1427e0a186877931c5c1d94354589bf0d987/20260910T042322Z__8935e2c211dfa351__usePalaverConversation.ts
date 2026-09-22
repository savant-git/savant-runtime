import {
  useCallback,
  useMemo,
  useState,
} from "react"
import type {
  PalaverMessageRecord,
} from "./PalaverMessage"
import type {
  ConversationBranch,
} from "./PalaverBranches"

function uid(
  prefix: string,
) {
  if (
    typeof crypto !==
      "undefined" &&
    "randomUUID" in crypto
  ) {
    return `${prefix}:${crypto.randomUUID()}`
  }

  return `${prefix}:${Date.now()}:${Math.random()
    .toString(36)
    .slice(2)}`
}

function branchLabel(
  message: PalaverMessageRecord,
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
    return compact
  }

  return `${compact.slice(
    0,
    49,
  )}…`
}

export function usePalaverConversation() {
  const [
    mainMessages,
    setMainMessages,
  ] = useState<
    PalaverMessageRecord[]
  >([])

  const [
    branches,
    setBranches,
  ] = useState<
    ConversationBranch[]
  >([])

  const [
    activeBranchId,
    setActiveBranchId,
  ] = useState<
    string | null
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

  const setMessages =
    useCallback(
      (
        update:
          | PalaverMessageRecord[]
          | ((
              current:
                PalaverMessageRecord[],
            ) =>
              PalaverMessageRecord[]),
      ) => {
        if (
          activeBranchId ===
          null
        ) {
          setMainMessages(
            update,
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

                const next =
                  typeof update ===
                  "function"
                    ? update(
                        branch.messages,
                      )
                    : update

                return {
                  ...branch,
                  messages:
                    next,
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

        if (
          sourceIndex < 0
        ) {
          return null
        }

        const id =
          uid("branch")

        const branch:
          ConversationBranch =
          {
            id,
            sourceMessageId:
              source.id,
            label:
              branchLabel(
                source,
              ),
            createdAt:
              Date.now(),
            messages:
              messages
                .slice(
                  0,
                  sourceIndex + 1,
                )
                .map(
                  (message) => ({
                    ...message,
                  }),
                ),
          }

        setBranches(
          (current) => [
            ...current,
            branch,
          ],
        )

        setActiveBranchId(
          id,
        )

        return id
      },
      [messages],
    )

  const selectBranch =
    useCallback(
      (
        branchId:
          | string
          | null,
      ) => {
        if (
          branchId ===
          null
        ) {
          setActiveBranchId(
            null,
          )
          return
        }

        if (
          branches.some(
            (branch) =>
              branch.id ===
              branchId,
          )
        ) {
          setActiveBranchId(
            branchId,
          )
        }
      },
      [branches],
    )

  return {
    messages,
    setMessages,
    mainMessages,
    branches,
    activeBranchId,
    createBranch,
    selectBranch,
  }
}
