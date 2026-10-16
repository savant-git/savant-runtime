export type FileClass =
  | "source"
  | "generated"
  | "cache"
  | "protected"
  | "binary"
  | "unknown"


export type FileIndexEntry = {
  path: string
  name: string
  classification: FileClass
  readableCandidate: boolean
  reason: string
}


export type ReadFileResult = {
  ok: boolean
  path: string
  content: string
  size: number | null
  truncated: boolean
  error: string
  technical: string
}


const protectedParts =
  new Set([
    ".git",
    ".venv",
    "__pycache__",
    "node_modules"
  ])


const cacheParts =
  new Set([
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    ".parcel-cache",
    ".vite"
  ])


const generatedParts =
  new Set([
    "dist",
    "build",
    "coverage"
  ])


const binaryExtensions =
  new Set([
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",
    ".dat",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf"
  ])


function basename(
  path: string
) {
  const normalized =
    path.replace(
      /\/+$/,
      ""
    )

  return (
    normalized
      .split("/")
      .pop()
    || normalized
  )
}


function extension(
  path: string
) {
  const name =
    basename(path)

  const index =
    name.lastIndexOf(".")

  if (
    index <= 0
  ) {
    return ""
  }

  return name
    .slice(index)
    .toLowerCase()
}


export function normalizePath(
  value: string
) {
  return value
    .replace(/\\/g, "/")
    .replace(/^\/+/, "")
    .replace(/\/+/g, "/")
    .trim()
}


export function classifyPath(
  rawPath: string
): FileIndexEntry {
  const path =
    normalizePath(rawPath)

  const parts =
    path
      .split("/")
      .filter(Boolean)

  const name =
    basename(path)

  if (
    parts.some(
      part =>
        protectedParts.has(part)
    )
  ) {
    return {
      path,
      name,
      classification:
        "protected",
      readableCandidate:
        false,
      reason:
        "Palaver intentionally blocks this protected path."
    }
  }

  if (
    parts.some(
      part =>
        cacheParts.has(part)
    )
  ) {
    return {
      path,
      name,
      classification:
        "cache",
      readableCandidate:
        false,
      reason:
        "Cache files are hidden from the normal source workspace."
    }
  }

  if (
    parts.some(
      part =>
        generatedParts.has(part)
    )
  ) {
    return {
      path,
      name,
      classification:
        "generated",
      readableCandidate:
        false,
      reason:
        "Generated build output is hidden from the normal source workspace."
    }
  }

  const ext =
    extension(path)

  if (
    binaryExtensions.has(ext)
  ) {
    return {
      path,
      name,
      classification:
        "binary",
      readableCandidate:
        false,
      reason:
        "This file is not treated as editable text source."
    }
  }

  return {
    path,
    name,
    classification:
      "source",
    readableCandidate:
      true,
    reason:
      "Readable source candidate."
  }
}


function collectStrings(
  value: unknown,
  output: string[]
) {
  if (
    typeof value
    === "string"
  ) {
    output.push(value)
    return
  }

  if (
    Array.isArray(value)
  ) {
    value.forEach(
      item =>
        collectStrings(
          item,
          output
        )
    )

    return
  }

  if (
    value
    && typeof value
    === "object"
  ) {
    const record =
      value as
        Record<string, unknown>

    if (
      Array.isArray(
        record.files
      )
    ) {
      collectStrings(
        record.files,
        output
      )
      return
    }

    for (
      const [
        key,
        item
      ] of Object.entries(record)
    ) {
      if (
        [
          "path",
          "file",
          "filename"
        ].includes(key)
        && typeof item
        === "string"
      ) {
        output.push(item)
      } else if (
        item
        && typeof item
        === "object"
      ) {
        collectStrings(
          item,
          output
        )
      }
    }
  }
}


export function repositoryEntries(
  payload: unknown,
  includeUnavailable = false
): FileIndexEntry[] {
  const raw:
    string[] = []

  collectStrings(
    payload,
    raw
  )

  const unique =
    new Map<
      string,
      FileIndexEntry
    >()

  for (
    const candidate
    of raw
  ) {
    const entry =
      classifyPath(candidate)

    if (!entry.path) {
      continue
    }

    if (
      !includeUnavailable
      && !entry.readableCandidate
    ) {
      continue
    }

    unique.set(
      entry.path,
      entry
    )
  }

  return [
    ...unique.values()
  ].sort(
    (
      left,
      right
    ) =>
      left.name.localeCompare(
        right.name
      )
      || left.path.localeCompare(
        right.path
      )
  )
}


function technicalText(
  value: unknown
) {
  if (
    typeof value
    === "string"
  ) {
    return value
  }

  try {
    return JSON.stringify(
      value,
      null,
      2
    )
  } catch {
    return String(value)
  }
}


export function decodeFileResponse(
  payload: unknown,
  requestedPath: string,
  httpOk: boolean
): ReadFileResult {
  const technical =
    technicalText(payload)

  if (
    !payload
    || typeof payload
    !== "object"
  ) {
    return {
      ok: false,
      path:
        requestedPath,
      content: "",
      size: null,
      truncated: false,
      error:
        "Palaver returned an invalid file response.",
      technical
    }
  }

  const root =
    payload as
      Record<string, unknown>

  if (
    !httpOk
    || root.ok === false
  ) {
    const rawError =
      String(
        root.error
        ?? "file request failed"
      )

    let message =
      "Palaver could not read this file."

    if (
      /blocked protected path/i
        .test(rawError)
    ) {
      message =
        "Palaver can see this indexed path, but it is intentionally protected from file reading."
    } else if (
      /blocked outside root/i
        .test(rawError)
    ) {
      message =
        "This path is outside the Savant runtime root and cannot be opened here."
    } else if (
      /missing file|missing path/i
        .test(rawError)
    ) {
      message =
        "This file no longer exists at the indexed path."
    } else if (
      /not a file/i
        .test(rawError)
    ) {
      message =
        "This path is a directory, not a readable source file."
    }

    return {
      ok: false,
      path:
        requestedPath,
      content: "",
      size: null,
      truncated: false,
      error:
        message,
      technical
    }
  }

  const file =
    root.file

  if (
    file
    && typeof file
    === "object"
  ) {
    const record =
      file as
        Record<string, unknown>

    const content =
      typeof record.content
      === "string"
        ? record.content
        : ""

    const size =
      typeof record.size
      === "number"
        ? record.size
        : null

    return {
      ok: true,
      path:
        typeof record.path
        === "string"
          ? record.path
          : requestedPath,
      content,
      size,
      truncated:
        size !== null
        && content.length
        < size,
      error: "",
      technical
    }
  }

  return {
    ok: false,
    path:
      requestedPath,
    content: "",
    size: null,
    truncated: false,
    error:
      "Palaver returned file metadata without readable source content.",
    technical
  }
}
