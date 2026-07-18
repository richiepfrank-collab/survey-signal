"""Download a model during preparation; Survey Signal never downloads at runtime."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Hugging Face model repository")
    parser.add_argument("--out", required=True, type=Path, help="Local model directory")
    parser.add_argument("--revision", default="main")
    args = parser.parse_args()

    from huggingface_hub import snapshot_download

    path = snapshot_download(repo_id=args.repo, revision=args.revision, local_dir=args.out)
    print(f"Staged {args.repo}@{args.revision} at {path}")


if __name__ == "__main__":
    main()
