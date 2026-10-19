"""CI check of the in-app self-update on Windows.

Copies the built one-file exe into a scratch folder, serves a second copy over HTTP, and runs
`<exe> --apply-update <url>`. That process must rename itself to .old, put the download in its
place and start it with --self-test; the relaunched copy writes selftest.log.

    python packaging/update_check.py "dist/KeptSpec Proposal Builder.exe"
"""

from __future__ import annotations

import functools
import http.server
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


def main() -> int:
    built = Path(sys.argv[1]).resolve()
    work = Path(tempfile.mkdtemp(prefix="updcheck_"))
    app_dir, srv_dir = work / "app", work / "srv"
    app_dir.mkdir()
    srv_dir.mkdir()
    exe = app_dir / built.name
    shutil.copy2(built, exe)
    shutil.copy2(built, srv_dir / "new.exe")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(srv_dir))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_port}/new.exe"

    r = subprocess.run([str(exe), "--apply-update", url], timeout=300)
    print("apply-update exit code", r.returncode, flush=True)
    log = app_dir / "selftest.log"
    deadline = time.time() + 600
    while time.time() < deadline and not (log.exists() and "SELF-TEST" in log.read_text(errors="ignore")):
        time.sleep(3)
    httpd.shutdown()
    old = exe.with_name(exe.name + ".old")
    ok = (r.returncode == 0 and exe.exists() and old.exists() and log.exists()
          and "SELF-TEST PASSED" in log.read_text(errors="ignore"))
    print("files:", sorted(p.name for p in app_dir.iterdir()), flush=True)
    if log.exists():
        print(log.read_text(errors="ignore")[-2000:], flush=True)
    print("UPDATE CHECK", "PASSED" if ok else "FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
