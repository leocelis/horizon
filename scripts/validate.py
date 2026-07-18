#!/usr/bin/env python
"""Repo-local entrypoint that defers to ``horizon_monitor.validate.main``.

This shim lets contributors run the validation harness without installing the
package globally. Equivalent to ``horizon-validate`` once installed.
"""

from __future__ import annotations

import sys

from horizon_monitor.validate import main

if __name__ == "__main__":
    sys.exit(main())
