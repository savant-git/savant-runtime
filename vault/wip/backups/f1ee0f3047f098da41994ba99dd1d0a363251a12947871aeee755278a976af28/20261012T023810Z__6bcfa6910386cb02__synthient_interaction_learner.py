
import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from synthient_learning_memory import LearningMemory


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:20]


def same_origin(first, second):
    a = urlparse(first)
    b = urlparse(second)

    def port(parsed):
        return parsed.port or (
            443 if parsed.scheme == "https" else 80
        )

    return (
        a.scheme == b.scheme
        and a.hostname == b.hostname
        and port(a) == port(b)
    )


async def observe(page):
    state = await page.evaluate(
        """() => ({
            title: document.title,
            text: (document.body?.innerText || '')
                .slice(0, 5000),
            controls: Array.from(
                document.querySelectorAll(
                    '[data-syntools-safe="true"]'
                )
            ).map(element => ({
                id: element.id,
                label: (
                    element.innerText ||
                    element.getAttribute('aria-label') ||
                    ''
                ).trim().slice(0, 100),
                tag: element.tagName.toLowerCase(),
                disabled: Boolean(element.disabled)
            }))
        })"""
    )

    signature = fingerprint({
        "url": page.url,
        "title": state["title"],
        "text": state["text"],
        "controls": state["controls"],
    })

    return {
        "url": page.url,
        "title": state["title"],
        "signature": signature,
        "controls": state["controls"],
        "observed_at": timestamp(),
    }


async def learn(url, max_actions):
    memory = LearningMemory()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            accept_downloads=False,
            service_workers="block",
        )

        async def restrict(route):
            request = route.request

            if (
                request.method != "GET"
                or not same_origin(url, request.url)
            ):
                await route.abort()
                return

            await route.continue_()

        await context.route("**/*", restrict)

        page = await context.new_page()
        completed = 0

        try:
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=15000,
            )

            if response is None or not same_origin(
                url, page.url
            ):
                raise RuntimeError(
                    "Initial navigation was not permitted"
                )

            initial = await observe(page)
            memory.record_state(url, initial)
            memory.record_outcome(
                url,
                page.url,
                initial["signature"],
                initial["title"],
            )
            memory.save()

            controls = initial["controls"]

            for control in controls:
                if completed >= max_actions:
                    break

                if (
                    not control["id"]
                    or control["disabled"]
                    or control["tag"] != "button"
                ):
                    continue

                # Reset before each independent experiment.
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                )

                before = await observe(page)

                selector = (
                    '[data-syntools-safe="true"]'
                    '[id=' + json.dumps(control["id"]) + ']'
                )

                button = page.locator(selector)

                if await button.count() != 1:
                    continue

                if not await button.is_enabled():
                    continue

                # Only explicit test controls are eligible.
                if await button.get_attribute("type") == "submit":
                    continue

                try:
                    await button.click(timeout=3000)
                    await page.wait_for_timeout(200)

                    if not same_origin(url, page.url):
                        raise RuntimeError(
                            "Interaction left authorized origin"
                        )

                    after = await observe(page)

                    memory.record_state(url, after)
                    memory.record_transition(
                        url,
                        before["signature"],
                        control["id"],
                        page.url,
                    )

                    memory.record_event(
                        "interaction_experiment",
                        url,
                        after["signature"],
                    )

                    memory.site(url).setdefault(
                        "experiments", []
                    ).append({
                        "action_id": control["id"],
                        "label": control["label"],
                        "before": before["signature"],
                        "after": after["signature"],
                        "changed": (
                            before["signature"]
                            != after["signature"]
                        ),
                        "observed_at": timestamp(),
                    })

                    memory.save()
                    completed += 1

                    print(
                        f"action={control['id']} "
                        f"changed={before['signature'] != after['signature']}"
                    )

                except Exception as error:
                    print(
                        f"action={control['id']} "
                        f"error={type(error).__name__}: {error}"
                    )

        finally:
            await browser.close()

    print(f"experiments completed: {completed}")


def main():
    parser = argparse.ArgumentParser(
        description="syntools controlled interaction learner"
    )

    parser.add_argument("url")
    parser.add_argument(
        "--actions", type=int, default=10
    )
    parser.add_argument(
        "--authorized", action="store_true"
    )

    args = parser.parse_args()
    parsed = urlparse(args.url)

    if not args.authorized:
        parser.error(
            "Explicit authorization is required"
        )

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        parser.error(
            "A plain HTTPS URL is required"
        )

    if not 1 <= args.actions <= 100:
        parser.error(
            "Actions must be between 1 and 100"
        )

    asyncio.run(
        learn(args.url, args.actions)
    )


if __name__ == "__main__":
    main()
