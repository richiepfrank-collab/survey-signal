"""`minemark serve` — run the local server."""
import argparse

import uvicorn


def main():
    p = argparse.ArgumentParser(prog="minemark")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the Survey Signal server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")
    args = p.parse_args()

    if args.cmd == "serve":
        uvicorn.run("backend.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
