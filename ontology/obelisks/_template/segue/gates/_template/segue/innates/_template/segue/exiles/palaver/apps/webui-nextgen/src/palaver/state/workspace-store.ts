import {
  appendReplay,
  replayWorkspace,
  type ReplayAction,
  type ReplayJournal,
  type ReplayState
} from "./workspace-replay"

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
  | "expert"


export type WorkspaceMode =
  | "single"
  | "chat-terminal-split"


export type WorkspacePreset =
  | "conversation"
  | "inference"
  | "context"
  | "review"
  | "inspection"
  | "focus"


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

  workspacePreset:
    WorkspacePreset

  leftPanelVisible:
    boolean

  rightPanelVisible:
    boolean

  statusbarVisible:
    boolean

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

  setWorkspacePreset: (
    value: WorkspacePreset
  ) => void

  applyWorkspacePreset: (
    value: WorkspacePreset
  ) => void

  toggleLeftPanel:
    () => void

  toggleRightPanel:
    () => void

  toggleStatusbar:
    () => void

  restoreWorkspace:
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

  replayJournal: ReplayJournal
  replayActions: () => void
  clearReplayJournal: () => void
}


function presetState(
  value: WorkspacePreset
) {
  switch (
    value
  ) {
    case "conversation":
      return {
        active:
          "chat" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "inference":
      return {
        active:
          "system" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "context":
      return {
        active:
          "memory" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "review":
      return {
        active:
          "source" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "inspection":
      return {
        active:
          "kindred" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          false,

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true
      }

    case "focus":
      return {
        active:
          "chat" as PalaverModule,

        workspaceMode:
          "single" as WorkspaceMode,

        focusMode:
          true,

        leftPanelVisible:
          false,

        rightPanelVisible:
          false,

        statusbarVisible:
          true
      }
  }
}


const initialReplayState: ReplayState = {
  active: "chat",
  density: "comfortable",
  workspaceMode: "single",
  workspacePreset: "conversation",
  focusMode: false,
  leftPanelVisible: true,
  rightPanelVisible: true,
  statusbarVisible: true
}

function replayStateOf(state: State): ReplayState {
  return {
    active: state.active,
    density: state.density,
    workspaceMode: state.workspaceMode,
    workspacePreset: state.workspacePreset,
    focusMode: state.focusMode,
    leftPanelVisible: state.leftPanelVisible,
    rightPanelVisible: state.rightPanelVisible,
    statusbarVisible: state.statusbarVisible
  }
}

function recordAction(state: State, action: ReplayAction): ReplayJournal {
  return appendReplay(state.replayJournal, action)
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

        workspacePreset:
          "conversation",

        leftPanelVisible:
          true,

        rightPanelVisible:
          true,

        statusbarVisible:
          true,

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

        replayJournal: {
          initial: initialReplayState,
          entries: []
        },

        replayActions: () => {
          const journal = get().replayJournal
          const restored = replayWorkspace(journal)
          set({
            ...restored,
            lastActivity: "workspace actions replayed"
          })
        },

        clearReplayJournal: () =>
          set(state => ({
            replayJournal: {
              initial: replayStateOf(state),
              entries: []
            }
          })),

        setActive:
          active =>
            set(state => ({
              replayJournal: recordAction(state, { type: "activate", value: active }),
              active,

              workspaceMode:
                "single",

              lastActivity:
                `opened ${active}`
            })),

        setCommandOpen:
          commandOpen =>
            set({
              commandOpen
            }),

        toggleFocus:
          () => {
            const enabled =
              !get().focusMode

            set(state => ({
              replayJournal: recordAction(state, { type: "focus", value: enabled }),
              focusMode:
                enabled,

              lastActivity:
                enabled
                  ? "focus mode enabled"
                  : "focus mode disabled"
            }))
          },

        cycleDensity:
          () => {
            const current =
              get().density

            const density:
              Density =
                current
                === "comfortable"
                  ? "compact"
                  : current
                  === "compact"
                    ? "expert"
                    : "comfortable"

            set(state => ({
              replayJournal: recordAction(state, { type: "density", value: density }),
              density,

              lastActivity:
                `density ${density}`
            }))
          },

        setWorkspaceMode:
          workspaceMode =>
            set(state => ({
              workspaceMode,
              replayJournal: recordAction(state, { type: "mode", value: workspaceMode })
            })),

        toggleChatTerminalSplit:
          () => {
            const opening =
              get().workspaceMode
              !== "chat-terminal-split"

            set(state => ({
              replayJournal: recordAction(state, {
                type: "mode", value: opening ? "chat-terminal-split" : "single"
              }),
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
            }))
          },

        setWorkspacePreset:
          workspacePreset =>
            set(state => ({
              workspacePreset,
              replayJournal: recordAction(state, { type: "preset", value: workspacePreset })
            })),

        applyWorkspacePreset:
          workspacePreset =>
            set(state => ({
              replayJournal: recordAction(state, {
                type: "snapshot",
                value: {
                  ...replayStateOf(state),
                  ...presetState(workspacePreset),
                  workspacePreset
                }
              }),
              workspacePreset,

              ...presetState(
                workspacePreset
              ),

              lastActivity:
                (
                  "workspace preset "
                  + workspacePreset
                )
            })),

        toggleLeftPanel:
          () => {
            const visible =
              !get().leftPanelVisible

            set(state => ({
              replayJournal: recordAction(state, { type: "visibility", target: "leftPanelVisible", value: visible }),
              leftPanelVisible:
                visible,

              lastActivity:
                visible
                  ? "tool rail opened"
                  : "tool rail hidden"
            }))
          },

        toggleRightPanel:
          () => {
            const visible =
              !get().rightPanelVisible

            set(state => ({
              replayJournal: recordAction(state, { type: "visibility", target: "rightPanelVisible", value: visible }),
              rightPanelVisible:
                visible,

              lastActivity:
                visible
                  ? "context inspector opened"
                  : "context inspector hidden"
            }))
          },

        toggleStatusbar:
          () => {
            const visible =
              !get().statusbarVisible

            set(state => ({
              replayJournal: recordAction(state, { type: "visibility", target: "statusbarVisible", value: visible }),
              statusbarVisible:
                visible,

              lastActivity:
                visible
                  ? "status rail opened"
                  : "status rail hidden"
            }))
          },

        restoreWorkspace:
          () =>
            set(state => ({
              replayJournal: recordAction(state, {
                type: "snapshot",
                value: {
                  ...replayStateOf(state),
                  workspacePreset: "conversation",
                  workspaceMode: "single",
                  focusMode: false,
                  density: "comfortable",
                  leftPanelVisible: true,
                  rightPanelVisible: true,
                  statusbarVisible: true
                }
              }),
              workspacePreset:
                "conversation",

              workspaceMode:
                "single",

              focusMode:
                false,

              density:
                "comfortable",

              leftPanelVisible:
                true,

              rightPanelVisible:
                true,

              statusbarVisible:
                true,

              lastActivity:
                "workspace restored"
            })),

        setComposerDraft:
          composerDraft =>
            set({
              composerDraft
            }),

        stageTerminal:
          text =>
            set(state => ({
              replayJournal: recordAction(state, { type: "mode", value: "chat-terminal-split" }),
              terminalStage: {
                id:
                  Date.now(),

                text
              },

              workspaceMode:
                "chat-terminal-split",

              lastActivity:
                "terminal input staged"
            })),

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
            set(state => ({
              replayJournal: recordAction(state, { type: "activate", value: "source" }),
              sourcePath:
                path,

              active:
                "source",

              workspaceMode:
                "single",

              lastActivity:
                `opened ${path}`
            })),

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
          "palaver-workspace-v9",

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

            workspacePreset:
              state.workspacePreset,

            leftPanelVisible:
              state.leftPanelVisible,

            rightPanelVisible:
              state.rightPanelVisible,

            statusbarVisible:
              state.statusbarVisible,

            sourcePath:
              state.sourcePath
          }),

        onRehydrateStorage: () => state => {
          if (state) {
            state.clearReplayJournal()
          }
        },

        version:
          9,

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

            if (
              value?.density
              !== "compact"
              && value?.density
              !== "comfortable"
              && value?.density
              !== "expert"
            ) {
              value.density =
                "comfortable"
            }

            if (
              !value?.workspacePreset
            ) {
              value.workspacePreset =
                "conversation"
            }

            if (
              typeof value
                ?.leftPanelVisible
              !== "boolean"
            ) {
              value.leftPanelVisible =
                true
            }

            if (
              typeof value
                ?.rightPanelVisible
              !== "boolean"
            ) {
              value.rightPanelVisible =
                true
            }

            if (
              typeof value
                ?.statusbarVisible
              !== "boolean"
            ) {
              value.statusbarVisible =
                true
            }

            return value
          }
      }
    )
  )
