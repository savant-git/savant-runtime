from __future__ import annotations

import re


PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
AWS_ACCESS_KEY = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
ASSIGNMENT = re.compile(
    r"(?im)^(?P<prefix>\s*(?:export\s+)?(?:api[_-]?key|secret(?:[_-]?key)?|token|password|passwd|aws_access_key_id|aws_secret_access_key|github_token|openai_api_key|anthropic_api_key)\s*[:=]\s*)(?P<quote>['\"]?)(?P<value>[^\s'\"#]+)(?P=quote)"
)
URL_CREDENTIAL = re.compile(r"(?P<scheme>https?://)(?P<user>[^/@:\s]+):(?P<password>[^/@\s]+)@")


def redact_text(text: str) -> tuple[str, int]:
    count = 0

    def replace_private(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        header = match.group(0).splitlines()[0]
        return f"{header}\n[REDACTED PRIVATE KEY]\n-----END REDACTED PRIVATE KEY-----"

    text = PRIVATE_KEY.sub(replace_private, text)

    def simple(pattern: re.Pattern[str], replacement: str, value: str) -> str:
        nonlocal count
        value, substitutions = pattern.subn(replacement, value)
        count += substitutions
        return value

    text = simple(AWS_ACCESS_KEY, "[REDACTED AWS ACCESS KEY]", text)
    text = simple(JWT, "[REDACTED JWT]", text)

    def replace_assignment(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        quote = match.group("quote")
        return f"{match.group('prefix')}{quote}[REDACTED]{quote}"

    text = ASSIGNMENT.sub(replace_assignment, text)

    def replace_url(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"{match.group('scheme')}[REDACTED]:[REDACTED]@"

    text = URL_CREDENTIAL.sub(replace_url, text)
    return text, count
