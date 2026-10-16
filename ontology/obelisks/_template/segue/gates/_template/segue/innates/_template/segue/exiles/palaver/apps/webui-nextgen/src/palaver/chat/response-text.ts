/**
 * Display projection only. Never evaluates code or promotes provider metadata.
 * Fenced JSON and ordinary JSON documents retain their original text.
 */
type RecordValue = Record<string, unknown>;
const maxDepth = 16;

function record(value: unknown): value is RecordValue {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function envelope(value: unknown, depth = 0): boolean {
  if (depth > 4 || !record(value)) return false;
  return Array.isArray(value.choices)
    || Array.isArray(value.output)
    || Array.isArray(value.candidates)
    || "output_text" in value
    || "answer" in value
    || "reply" in value
    || "response" in value
    || (record(value.message) && "content" in value.message)
    || envelope(value.data, depth + 1)
    || envelope(value.result, depth + 1)
    || (typeof value.type === "string"
      && /^(?:message|text|output_text|text_delta|content_block_delta)$/.test(value.type));
}

export function assistantTextFromValue(value: unknown): string {
  const visited = new WeakSet<object>();

  function extract(current: unknown, depth: number): string {
    if (depth > maxDepth || current == null) return "";

    if (typeof current === "string") {
      if (!current.trim()) return "";
      const trimmed = current.trim();
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        try {
          const decoded: unknown = JSON.parse(trimmed);
          if (envelope(decoded)) return extract(decoded, depth + 1);
          if (Array.isArray(decoded) && decoded.some(item => envelope(item))) {
            return extract(decoded, depth + 1);
          }
        } catch {
          // Non-JSON prose, source text and code remain untouched.
        }
      }
      return current;
    }

    if (typeof current !== "object") return "";
    if (visited.has(current)) return "";
    visited.add(current);

    if (Array.isArray(current)) {
      return current.map(part => extract(part, depth + 1))
        .filter(Boolean).join("\n");
    }
    if (!record(current)) return "";

    const type = typeof current.type === "string" ? current.type : "";
    if (/tool|function_call|reasoning|image|audio/.test(type)) return "";
    if (current.role === "tool" || current.role === "system"
      || current.role === "developer" || current.role === "user") return "";

    for (const key of ["output_text", "answer", "reply"]) {
      if (current[key] !== undefined) {
        const text = extract(current[key], depth + 1);
        if (text) return text;
      }
    }

    if (Array.isArray(current.choices)) {
      // Alternatives are alternatives, not a single concatenated reply.
      for (const choice of current.choices) {
        if (!record(choice)) continue;
        const text = extract(choice.message ?? choice.delta ?? choice.text, depth + 1);
        if (text) return text;
      }
      return "";
    }

    if (Array.isArray(current.candidates)) {
      for (const candidate of current.candidates) {
        if (!record(candidate)) continue;
        const text = extract(candidate.content, depth + 1);
        if (text) return text;
      }
      return "";
    }

    if (Array.isArray(current.output)) {
      return extract(current.output, depth + 1);
    }

    for (const key of ["response", "message", "content", "parts", "text", "delta", "refusal"]) {
      if (current[key] === undefined) continue;
      const text = extract(current[key], depth + 1);
      if (text) return text;
    }

    // A recognized transport wrapper may nest the actual response.
    for (const key of ["result", "data"]) {
      if (envelope(current[key])) {
        const text = extract(current[key], depth + 1);
        if (text) return text;
      }
    }
    return "";
  }

  return extract(value, 0);
}
