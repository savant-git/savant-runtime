import {
  create
} from "zustand"

import {
  persist
} from "zustand/middleware"


export type PalaverModule =
  | "chat"
  | "terminal"
  | "memory"
  | "source"
  | "kindred"
  | "search"
  | "work"
  | "system"
  | "guide"


export type Observatory =
  PalaverModule


export type Density =
  | "compact"
  | "comfortable"


export type WorkspaceMode =
  | "single"
  | "chat-terminal-split"


type TerminalStage = {
  id: number
  text: string
}


export type UploadedContext = {
  id: string
  name: string
  type: string
  size: number
  text: string
}


type State = {
  active:
    PalaverModule

  commandOpen:
    boolean

  focusMode:
    boolean

  density:
    Density

  workspaceMode:
    WorkspaceMode

  composerDraft:
    string

  terminalStage:
    TerminalStage | null

  lastActivity:
    string

  sourcePath:
    string

  uploadedContext:
    UploadedContext[]

  setActive: (
    value: PalaverModule
  ) => void

  setCommandOpen: (
    value: boolean
  ) => void

  toggleFocus:
    () => void

  cycleDensity:
    () => void

  setWorkspaceMode: (
    value: WorkspaceMode
  ) => void

  toggleChatTerminalSplit:
    () => void

  setComposerDraft: (
    value: string
  ) => void

  stageTerminal: (
    value: string
  ) => void

  clearTerminalStage:
    () => void

  setLastActivity: (
    value: string
  ) => void

  openSource: (
    path: string
  ) => void

  addUploadedContext: (
    value: UploadedContext[]
  ) => void

  removeUploadedContext: (
    id: string
  ) => void

  clearUploadedContext:
    () => void
}


export const useWorkspaceStore =
  create<State>()(
    persist(
      (
        set,
        get
      ) => ({
        active:
          "chat",

        commandOpen:
          false,

        focusMode:
          false,

        density:
          "comfortable",

        workspaceMode:
          "single",

        composerDraft:
          "",

        terminalStage:
          null,

        lastActivity:
          "palaver ready",

        sourcePath:
          "",

        uploadedContext:
          [],

        setActive:
          active =>
            set({
              active,

              workspaceMode:
                "single",

              lastActivity:
                `opened ${active}`
            }),

        setCommandOpen:
          commandOpen =>
            set({
              commandOpen
            }),

        toggleFocus:
          () =>
            set({
              focusMode:
                !get().focusMode
            }),

        cycleDensity:
          () =>
            set({
              density:
                get().density
                === "comfortable"
                  ? "compact"
                  : "comfortable"
            }),

        setWorkspaceMode:
          workspaceMode =>
            set({
              workspaceMode
            }),

        toggleChatTerminalSplit:
          () => {
            const opening =
              get().workspaceMode
              !== "chat-terminal-split"

            set({
              workspaceMode:
                opening
                  ? "chat-terminal-split"
                  : "single",

              lastActivity:
                opening
                  ? (
                    "chat and terminal "
                    + "split opened"
                  )
                  : (
                    "chat and terminal "
                    + "split closed"
                  )
            })
          },

        setComposerDraft:
          composerDraft =>
            set({
              composerDraft
            }),

        stageTerminal:
          text =>
            set({
              terminalStage: {
                id:
                  Date.now(),

                text
              },

              workspaceMode:
                "chat-terminal-split",

              lastActivity:
                "terminal input staged"
            }),

        clearTerminalStage:
          () =>
            set({
              terminalStage:
                null
            }),

        setLastActivity:
          lastActivity =>
            set({
              lastActivity
            }),

        openSource:
          path =>
            set({
              sourcePath:
                path,

              active:
                "source",

              workspaceMode:
                "single",

              lastActivity:
                `opened ${path}`
            }),

        addUploadedContext:
          value =>
            set(
              state => {
                const existing =
                  new Set(
                    state
                      .uploadedContext
                      .map(
                        item =>
                          item.id
                      )
                  )

                const next =
                  value.filter(
                    item =>
                      !existing.has(
                        item.id
                      )
                  )

                return {
                  uploadedContext: [
                    ...state.uploadedContext,
                    ...next
                  ].slice(
                    -30
                  ),

                  lastActivity:
                    (
                      `${next.length} `
                      + "attachment"
                      + (
                        next.length
                        === 1
                          ? ""
                          : "s"
                      )
                      + " added"
                    )
                }
              }
            ),

        removeUploadedContext:
          id =>
            set(
              state => ({
                uploadedContext:
                  state
                    .uploadedContext
                    .filter(
                      item =>
                        item.id
                        !== id
                    )
              })
            ),

        clearUploadedContext:
          () =>
            set({
              uploadedContext:
                []
            })
      }),
      {
        name:
          "palaver-workspace-v8",

        partialize:
          state => ({
            active:
              state.active,

            focusMode:
              state.focusMode,

            density:
              state.density,

            workspaceMode:
              state.workspaceMode,

            sourcePath:
              state.sourcePath
          }),

        version:
          8,

        migrate:
          persisted => {
            const value =
              persisted as any

            if (
              value?.active
              === "uploads"
            ) {
              value.active =
                "chat"
            }

            return value
          }
      }
    )
  )
