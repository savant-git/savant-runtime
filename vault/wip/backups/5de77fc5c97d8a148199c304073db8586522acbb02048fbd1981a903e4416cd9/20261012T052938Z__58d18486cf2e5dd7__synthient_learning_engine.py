
import argparse
import asyncio
import hashlib
import re
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urldefrag, urlparse

from playwright.async_api import async_playwright

from synthient_learning_memory import LearningMemory


BLOCKED = re.compile(
    r"submit|complete|claim|redeem|cash.?out|"
    r"withdraw|purchase|pay|buy|delete|remove|"
    r"confirm|accept|agree|consent|register|"
    r"sign.?up|login|log.?in|captcha|verify|"
    r"upload|send|checkout|subscribe|"
    r"account|settings|logout|log.?out|"
    r"transfer|reward|balance|payment|"
    r"survey|questionnaire|profile|"
    r"unsubscribe|reset|token|api.?key",
    re.IGNORECASE,
)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:20]


def origin(url):
    parsed = urlparse(url)
    port = parsed.port

    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    return parsed.scheme, parsed.hostname, port


def same_origin(first, second):
    return origin(first) == origin(second)


def normalize(url):
    return urldefrag(url)[0]


def safe_navigation(control, base_url):
    if control["disabled"]:
        return None

    if control["tag"] != "a":
        return None

    label = control["text"]
    href = control["href"]

    if not label or not href:
        return None

    if BLOCKED.search(label):
        return None

    destination = normalize(urljoin(base_url, href))
    parsed = urlparse(destination)

    if parsed.scheme != "https":
        return None

    if not same_origin(base_url, destination):
        return None

    if parsed.username or parsed.password:
        return None

    if parsed.query:
        return None

    if BLOCKED.search(parsed.path):
        return None

    return destination


async def observe(page):
    controls = await page.locator(
        "a[href], button, [role='button']"
    ).evaluate_all(
        """elements => elements.slice(0, 100).map(
            (element, index) => ({
                index,
                tag: element.tagName.toLowerCase(),
                text: (
                    element.innerText ||
                    element.getAttribute('aria-label') ||
                    ''
                ).trim().slice(0, 100),
                href: element.getAttribute('href'),
                disabled: Boolean(element.disabled)
            })
        )"""
    )

    body = (
        await page.locator("body").inner_text()
    )[:5000]

    title = await page.title()

    signature = fingerprint(
        title + "\n" + body
    )

    return {
        "url": page.url,
        "title": title,
        "signature": signature,
        "controls": controls,
        "observed_at": timestamp(),
    }


async def explore(url, max_steps, revisit):
    memory = LearningMemory()

    queue = deque([normalize(url)])
    queued = {normalize(url)}
    visited = set()
    steps = 0

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            accept_downloads=False,
            service_workers="block",
            java_script_enabled=False,
        )

        async def restrict_requests(route):
            request = route.request

            if request.method != "GET":
                await route.abort()
                return

            if not same_origin(url, request.url):
                await route.abort()
                return

            if BLOCKED.search(urlparse(request.url).path):
                await route.abort()
                return

            await route.continue_()

        await context.route("**/*", restrict_requests)

        page = await context.new_page()

        try:
            while queue and steps < max_steps:
                target = queue.popleft()

                if target in visited:
                    continue

                if not same_origin(url, target):
                    continue

                if (
                    not revisit
                    and target != normalize(url)
                    and memory.known_destination(url, target)
                ):
                    continue

                visited.add(target)

                try:
                    response = await page.goto(
                        target,
                        wait_until="domcontentloaded",
                        timeout=15000,
                    )

                    if response is None:
                        continue

                    if not same_origin(url, page.url):
                        continue

                    state = await observe(page)

                    memory.record_state(url, state)

                    memory.record_outcome(
                        url,
                        target,
                        state["signature"],
                        state["title"],
                    )

                    print(
                        f"observed: {state['title']} "
                        f"[{state['signature']}]"
                    )

                    for control in state["controls"]:
                        destination = safe_navigation(
                            control, page.url
                        )

                        if destination is None:
                            continue

                        memory.record_transition(
                            url,
                            state["signature"],
                            control["text"],
                            destination,
                        )

                        if destination in visited:
                            continue

                        if destination in queued:
                            continue

                        if (
                            not revisit
                            and memory.known_destination(
                                url, destination
                            )
                        ):
                            continue

                        queue.append(destination)
                        queued.add(destination)

                    memory.record_event(
                        "interface_observation",
                        url,
                        state["signature"],
                    )

                    steps += 1
                    memory.save()

                except Exception as error:
                    print(
                        "navigation failed: "
                        f"{type(error).__name__}"
                    )

        finally:
            await browser.close()

    stats = memory.statistics(url)

    print(f"pages observed this run: {steps}")
    print(f"known states: {stats['states']}")
    print(
        f"known transitions: "
        f"{stats['transitions']}"
    )
    print(
        f"known destinations: "
        f"{stats['known_destinations']}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="syntools interface learning engine"
    )

    parser.add_argument("url")
    parser.add_argument(
        "--steps", type=int, default=10
    )
    parser.add_argument(
        "--authorized", action="store_true"
    )
    parser.add_argument(
        "--revisit", action="store_true",
        help="Reobserve previously discovered pages",
    )

    args = parser.parse_args()

    if not args.authorized:
        parser.error(
            "Explicit authorization is required"
        )

    parsed = urlparse(args.url)

    if parsed.scheme != "https" or not parsed.hostname:
        parser.error("A valid HTTPS URL is required")

    if parsed.username or parsed.password:
        parser.error("URL credentials are not permitted")

    if parsed.query or parsed.fragment:
        parser.error(
            "Query strings and fragments are not permitted"
        )

    if not 1 <= args.steps <= 100:
        parser.error("Steps must be between 1 and 100")

    asyncio.run(
        explore(args.url, args.steps, args.revisit)
    )


if __name__ == "__main__":
    main()
