from __future__ import annotations

import sys


package = sys.modules.get(
    __name__
)

if package is not None:
    sys.modules.setdefault(
        "providers",
        package,
    )
