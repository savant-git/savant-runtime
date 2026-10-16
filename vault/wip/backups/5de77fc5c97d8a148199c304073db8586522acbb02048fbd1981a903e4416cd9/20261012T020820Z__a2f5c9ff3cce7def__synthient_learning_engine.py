
import argparse
import asyncio
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from synthient_learning_memory import LearningMemory


BLOCKED_ACTIONS = re.compile(
    r"submit|complete|claim|redeem|cash.?out|withdraw|"
    r"purchase|pay|buy|delete|remove|confirm|"
    r"accept|agree|consent|register|sign.?up|"
    r"login|log.?in|captcha|verify|upload|send",
    re.IGNORECASE,
)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def origin(url):
    parsed = urlparse(url)
    port = parsed.port

    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    return parsed.scheme, parsed.hostname, port


def same_origin(first, second):
    return origin(first) == origin(second)


def safe_navigation(control, base_url):
    if control["disabled"]:
        return None

    if control["tag"] != "a":
        return None

    label = control["text"]
    href = control["href"]

    if not label or not href:
        return None

    if BLOCKED_ACTIONS.search(label):
        return None

    destination = urljoin(base_url, href)
    parsed = urlparse(destination)

    if parsed.scheme != "https":
        return None

    if not same_origin(base_url, destination):
        return None

    if parsed.query or parsed.fragment:
        return None

    if BLOCKED_ACTIONS.search(parsed.path):
        return None

    return destination


async def observe(page):
    controls = await page.locator(
        "button, a[href], [role='button']"
    ).evaluate_all(
        """elements => elements.slice(0, 80).map((element, index) => ({
            index,
            tag: element.tagName.toLowerCase(),
            text: (
                element.innerText ||
                element.getAttribute('aria-label') ||
                ''
            ).trim().slice(0, 100),
            href: element.getAttribute('href'),
            disabled: Boolean(element.disabled)
        }))"""
    )

    body = (await page.locator("body").inner_text())[:5000]

    return {
        "url": page.url,
        "title": await page.title(),
        "signature": fingerprint(body),
        "controls": controls,
        "observed_at": timestamp(),
    }


async def explore(url, max_steps):
    memory = LearningMemory()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            accept_downloads=False,
            service_workers="block",
        )

        await context.route(
            "**/*",
            lambda route: (
                route.continue_()
                if route.request.method == "GET"
                else route.abort()
            ),
        )

        page = await context.new_page()

        queue = [url]
        visited = set()
        steps = 0

        try:
            while queue and steps < max_steps:
                target = queue.pop(0)

                if target in visited:
                    continue

                if not same_origin(url, target):
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

                    print(
                        f"observed: {state['title']} "
                        f"[{state['signature']}]"
                    )

                    for control in state["controls"]:
                        destination = safe_navigation(
                            control,
                            page.url,
                        )

                        if destination is None:
                            continue

                        if destination not in visited:
                            queue.append(destination)

                        memory.record_transition(
                            url,
                            state["signature"],
                            control["text"],
                            destination,
                        )

                    memory.record_event(
                        "interface_observation",
                        url,
                        state["signature"],
                    )

                    memory.save()
                    steps += 1

                except Exception as error:
                    print(
                        f"navigation failed: "
                        f"{type(error).__name__}"
                    )

        finally:
            await browser.close()

    print(f"finished: {steps} pages observed")


def main():
    parser = argparse.ArgumentParser(
        description="syntools autonomous interface explorer"
    )

    parser.add_argument("url")

    parser.add_argument(
        "--steps",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--authorized",
        action="store_true",
        help="Confirm permission to automate this website",
    )

    args = parser.parse_args()

    if not args.authorized:
        parser.error(
            "Explicit authorization is required."
        )

    parsed = urlparse(args.url)

    if parsed.scheme != "https" or not parsed.hostname:
        parser.error("A valid HTTPS URL is required.")

    if not 1 <= args.steps <= 100:
        parser.error("Steps must be between 1 and 100.")

    asyncio.run(explore(args.url, args.steps))


if __name__ == "__main__":
    main()
