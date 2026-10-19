import http.server
import threading
from functools import partial
from pathlib import Path

from proposal_builder import updater


def test_version_compare():
    assert updater.is_newer("1.3.0", "1.2.1")
    assert updater.is_newer("v1.10.0", "1.9.9")
    assert not updater.is_newer("1.2.1", "1.2.1")
    assert not updater.is_newer("1.2.0", "1.2.1")


def test_release_from_json_picks_exe():
    rel = updater.release_from_json({
        "tag_name": "v1.3.0", "html_url": "https://example/rel",
        "assets": [{"name": "KeptSpec-Proposal-Builder-folder.zip", "browser_download_url": "z", "size": 1},
                   {"name": "KeptSpec.Proposal.Builder.exe", "browser_download_url": "e", "size": 2}]})
    assert (rel.version, rel.exe_url, rel.exe_size, rel.page) == ("1.3.0", "e", 2, "https://example/rel")


def test_not_self_updating_from_source():
    assert updater.running_exe() is None


def test_download_and_swap(tmp_path: Path):
    serve = tmp_path / "srv"
    serve.mkdir()
    (serve / "app.exe").write_bytes(b"new version" * 1000)
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(serve))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        exe = tmp_path / "app" / "KeptSpec.exe"
        exe.parent.mkdir()
        exe.write_bytes(b"old")
        new = exe.with_name(exe.name + ".new")
        seen = []
        updater.download(f"http://127.0.0.1:{httpd.server_port}/app.exe", new, 11000, lambda g, t: seen.append(g))
        updater.swap_in(exe, new)
        assert exe.read_bytes() == b"new version" * 1000
        assert exe.with_name("KeptSpec.exe.old").read_bytes() == b"old"
        assert seen and seen[-1] == 11000
        updater.cleanup_old(exe)
        assert sorted(p.name for p in exe.parent.iterdir()) == ["KeptSpec.exe"]
    finally:
        httpd.shutdown()
