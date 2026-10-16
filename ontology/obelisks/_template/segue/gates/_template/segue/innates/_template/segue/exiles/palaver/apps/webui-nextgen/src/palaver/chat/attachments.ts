export type AttachmentState =
  | "ready"
  | "unsupported"
  | "error"

export type ChatAttachment = {
  id: string
  name: string
  type: string
  size: number
  text: string
  state: AttachmentState
  error: string
  addedAt: number
  previewUrl?: string
}

export const maxAttachmentMiB = 50

export const maxAttachmentBytes =
  maxAttachmentMiB
  * 1024
  * 1024

export const maxAttachmentText =
  200000

export const maxProjectedTextPerFile =
  30000

export const maxProjectedTextTotal =
  120000

const textExtensions =
  new Set([
    "txt",
    "md",
    "markdown",
    "json",
    "jsonl",
    "csv",
    "tsv",
    "js",
    "jsx",
    "ts",
    "tsx",
    "py",
    "sh",
    "bash",
    "zsh",
    "css",
    "scss",
    "html",
    "htm",
    "xml",
    "yaml",
    "yml",
    "toml",
    "ini",
    "cfg",
    "conf",
    "log",
    "sql",
    "graphql",
    "gql",
    "java",
    "c",
    "h",
    "cpp",
    "hpp",
    "rs",
    "go",
    "rb",
    "php"
  ])

function extension(
  name: string
) {
  return (
    name
      .split(".")
      .pop()
      ?.toLowerCase()
    ?? ""
  )
}

export function readableFile(
  file: File
) {
  if (
    file.type.startsWith(
      "text/"
    )
  ) {
    return true
  }

  if (
    file.type
      === "application/json"
    || file.type
      === "application/xml"
  ) {
    return true
  }

  return textExtensions.has(
    extension(
      file.name
    )
  )
}

export function humanBytes(
  value: number
) {
  if (
    value < 1024
  ) {
    return `${value} B`
  }

  if (
    value
    < 1024 * 1024
  ) {
    return (
      `${(
        value
        / 1024
      ).toFixed(1)} KiB`
    )
  }

  return (
    `${(
      value
      / 1024
      / 1024
    ).toFixed(1)} MiB`
  )
}

async function digest(
  value: string
) {
  if (
    !globalThis.crypto
      ?.subtle
  ) {
    return value
  }

  const encoded =
    new TextEncoder()
      .encode(
        value
      )

  const result =
    await globalThis.crypto
      .subtle
      .digest(
        "SHA-256",
        encoded
      )

  return Array
    .from(
      new Uint8Array(
        result
      )
    )
    .map(
      value =>
        value
          .toString(16)
          .padStart(
            2,
            "0"
          )
    )
    .join("")
}

export async function fileId(
  file: File
) {
  return digest(
    [
      file.name,
      file.size,
      file.lastModified,
      file.type
    ].join(
      ":"
    )
  )
}

export async function attachmentFromFile(
  file: File
): Promise<ChatAttachment> {
  const id =
    await fileId(
      file
    )

  const base = {
    id,

    name:
      file.name,

    type:
      file.type
      || "unknown",

    size:
      file.size,

    addedAt:
      Date.now()
  }

  if (
    file.size
    > maxAttachmentBytes
  ) {
    return {
      ...base,

      text:
        "",

      state:
        "unsupported",

      error:
        (
          "Attachment exceeds "
          + `the ${maxAttachmentMiB} MiB `
          + "local ingestion limit."
        )
    }
  }

  if (
    file.type.startsWith(
      "image/"
    )
  ) {
    return {
      ...base,

      text:
        "",

      state:
        "ready",

      error:
        "",

      previewUrl:
        URL.createObjectURL(
          file
        )
    }
  }

  if (
    !readableFile(
      file
    )
  ) {
    return {
      ...base,

      text:
        "",

      state:
        "unsupported",

      error:
        (
          "Attachment is retained "
          + "as metadata, but this "
          + "local client has no "
          + "binary parser for it."
        )
    }
  }

  try {
    const value =
      await file.text()

    return {
      ...base,

      text:
        value.slice(
          0,
          maxAttachmentText
        ),

      state:
        "ready",

      error:
        ""
    }

  } catch (
    reason
  ) {
    return {
      ...base,

      text:
        "",

      state:
        "error",

      error:
        reason instanceof Error
          ? reason.message
          : String(reason)
    }
  }
}

export async function attachmentFromText(
  value: string,
  name = "pasted-text.txt"
): Promise<ChatAttachment> {
  const text =
    value.slice(
      0,
      maxAttachmentText
    )

  return {
    id:
      await digest(
        (
          name
          + ":"
          + text
        )
      ),

    name,

    type:
      "text/plain",

    size:
      new Blob(
        [
          value
        ]
      ).size,

    text,

    state:
      "ready",

    error:
      "",

    addedAt:
      Date.now()
  }
}

export function persistedAttachment(
  attachment: ChatAttachment
): ChatAttachment {
  return {
    ...attachment,

    previewUrl:
      undefined
  }
}

export function projectAttachments(
  attachments:
    ChatAttachment[]
) {
  let remaining =
    maxProjectedTextTotal

  const sections:
    string[] = []

  attachments.forEach(
    (
      item,
      index
    ) => {
      const header = [
        (
          `attachment `
          + `${index + 1}: `
          + item.name
        ),

        `type: ${item.type}`,

        `size: ${item.size}`,

        `state: ${item.state}`
      ]

      if (
        item.state
        === "ready"
        && item.text
        && remaining > 0
      ) {
        const slice =
          item.text.slice(
            0,
            Math.min(
              maxProjectedTextPerFile,
              remaining
            )
          )

        remaining -=
          slice.length

        sections.push(
          [
            ...header,
            "",
            slice
          ].join(
            "\n"
          )
        )

        return
      }

      sections.push(
        [
          ...header,

          item.error
            ? (
              "note: "
              + item.error
            )
            : (
              "note: binary attachment "
              + "metadata only"
            )
        ].join(
          "\n"
        )
      )
    }
  )

  return sections.join(
    (
      "\n\n"
      + "===================="
      + "\n\n"
    )
  )
}

export function estimateTokens(
  text: string,
  attachments:
    ChatAttachment[]
) {
  const attachmentCharacters =
    attachments.reduce(
      (
        total,
        item
      ) =>
        total
        + item.text.length,
      0
    )

  return Math.ceil(
    (
      text.length
      + Math.min(
        attachmentCharacters,
        maxProjectedTextTotal
      )
    )
    / 4
  )
}
