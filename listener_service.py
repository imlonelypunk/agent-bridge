"""Run the scheduled listener without a console, retaining diagnostic output."""
import os
from pathlib import Path
import sys
import traceback

import bridge


def main():
    log_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AgentBridge" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "codex-listener.log"
    if log_path.exists() and log_path.stat().st_size > 1024 * 1024:
        log_path.replace(log_path.with_suffix(".log.old"))
    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        sys.stdin = open(os.devnull, encoding="utf-8")
        sys.stdout = sys.stderr = log
        try:
            bridge.main()
        except BaseException:
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
