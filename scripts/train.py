"""Guard the training step until validated object-level labels are available."""
from __future__ import annotations

import sys


def main() -> None:
    message = (
        "Fine-tuning is intentionally blocked: the staged DRC asset has no verified "
        "object-level annotation artifact. Obtain legally reusable target coordinates, "
        "then implement a site-separated RT-DETR training pipeline."
    )
    print(message, file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
