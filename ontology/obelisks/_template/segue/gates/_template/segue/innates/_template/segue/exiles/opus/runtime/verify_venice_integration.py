#!/usr/bin/env python3

from __future__ import annotations

import json

import environment

from providers import venice_uncensored_text
from router import policy, provider, route


def main() -> None:
    environment.load_environment(
        force=True
    )

    active_route = route(
        "text_inference_route"
    )

    active_policy = policy(
        active_route[
            "policy_ref"
        ]
    )

    behavior_policy = policy(
        active_policy[
            "behavior_policy_ref"
        ]
    )

    venice_provider = provider(
        "venice_uncensored_text"
    )

    result = venice_uncensored_text.infer(
        {
            "message":
                "Reply with exactly: opus-ok",
            "model":
                "venice-uncensored-1-2",
            "temperature":
                0,
        },
        venice_provider,
    )

    output = {
        "route":
            active_route[
                "id"
            ],
        "default_provider":
            active_route[
                "default_provider"
            ],
        "active_policy":
            active_policy[
                "id"
            ],
        "behavior_policy":
            behavior_policy[
                "id"
            ],
        "provider":
            result.get(
                "provider"
            ),
        "provider_profile":
            result.get(
                "provider_profile"
            ),
        "model":
            result.get(
                "model"
            ),
        "text":
            result.get(
                "text"
            ),
        "inference_latitude":
            result.get(
                "inference_latitude"
            ),
        "provider_content_filtering":
            result.get(
                "provider_content_filtering"
            ),
        "authority_effect":
            result.get(
                "authority_effect"
            ),
    }

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
