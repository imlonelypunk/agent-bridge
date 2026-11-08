"""Build a portable Agent Bridge Desktop extension without external dependencies."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    root = source.parent
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if args.out.suffix != ".mcpb":
        parser.error("--out must have the .mcpb extension")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.out, "x", compression=ZIP_DEFLATED) as bundle:
        for name in ("manifest.json", "launch.cjs", "README.md", "PRIVACY.md"):
            bundle.write(source / name, name)
        for name in ("bridge.py", "bridge_runner.py", "LICENSE", "plugin/__init__.py", "plugin/mailbox_server.py"):
            bundle.write(root / name, name)
    print(f"Built {manifest['display_name']} {manifest['version']} at {args.out.resolve()}")


if __name__ == "__main__":
    main()
