(() => {
    "use strict";

    const schema = "savant.niche.atlas-static-bridge.v1";
    const authorityEffect = "none";
    const projectionOnly = true;
    const mutationAuthority = false;

    const nativeFetch = window.fetch.bind(window);

    function resolveUrl(input) {
        if (typeof input === "string") {
            return input;
        }

        if (input instanceof URL) {
            return input.href;
        }

        if (
            typeof Request !== "undefined"
            && input instanceof Request
        ) {
            return input.url;
        }

        return null;
    }

    function isAtlasProjectionRequest(input) {
        const raw = resolveUrl(input);

        if (!raw) {
            return false;
        }

        let url;

        try {
            url = new URL(
                raw,
                window.location.href
            );
        } catch {
            return false;
        }

        return (
            url.origin === window.location.origin
            && (
                url.pathname === "/api/atlas"
                || url.pathname === "/api/atlas/"
            )
        );
    }

    window.fetch = function atlasStaticFetch(
        input,
        init
    ) {
        if (
            isAtlasProjectionRequest(input)
        ) {
            return nativeFetch(
                "/atlas.json",
                {
                    ...(init || {}),
                    method: "GET",
                    cache: "no-store"
                }
            );
        }

        return nativeFetch(
            input,
            init
        );
    };

    Object.defineProperty(
        window,
        "__savantAtlasStaticBridge",
        {
            configurable: false,
            enumerable: false,
            writable: false,
            value: Object.freeze({
                schema,
                authority_effect:
                    authorityEffect,
                projection_only:
                    projectionOnly,
                mutation_authority:
                    mutationAuthority,
                projection_source:
                    "/atlas.json"
            })
        }
    );
})();
