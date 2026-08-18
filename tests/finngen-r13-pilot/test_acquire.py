#!/usr/bin/env python3
"""Public-CLI integration test for resumable FinnGen artifact acquisition."""
from __future__ import annotations

import csv
import hashlib
import http.server
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import ClassVar

ROOT = Path(__file__).resolve().parents[2]


class RangeHandler(http.server.BaseHTTPRequestHandler):
    payload = b""
    ranges: ClassVar[list[str]] = []

    def do_GET(self) -> None:
        if self.path != "/fixture.gz":
            self.send_error(404)
            return
        range_header = self.headers.get("Range")
        start = 0
        if range_header:
            self.ranges.append(range_header)
            start = int(range_header.removeprefix("bytes=").removesuffix("-"))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(self.payload) - 1}/{len(self.payload)}")
        else:
            self.send_response(200)
        body = self.payload[start:]
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", '"fixture-etag"')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        return


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> None:
    payload = (b"FinnGen fixture association bytes\n" * 8192) + b"done\n"
    RangeHandler.payload = payload
    RangeHandler.ranges = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RangeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            release = tmp / "release"
            source_dir = tmp / "artifacts" / "source"
            release.mkdir()
            source_dir.mkdir(parents=True)
            target = source_dir / "finngen_R13_FIXTURE.gz"
            part = target.with_name(target.name + ".part")
            part.write_bytes(payload[: len(payload) // 3])

            columns = [
                "analysis_id", "source_url", "source_file", "checksum",
                "checksum_algorithm", "size_bytes",
            ]
            with (release / "analyses.tsv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerow({
                    "analysis_id": "finngen-r13-FIXTURE",
                    "source_url": f"http://127.0.0.1:{server.server_port}/fixture.gz",
                    "source_file": str(target),
                    "checksum": "",
                    "checksum_algorithm": "sha256",
                    "size_bytes": "",
                })
            (release / "validation.yaml").write_text(
                "checks:\n  files: not_run\nreports: {}\nwarnings: []\nerrors: []\n",
                encoding="utf-8",
            )

            command = [
                sys.executable,
                "resources/generators/finngen-r13-dense/acquire.py",
                f"--release-dir={release}",
            ]
            first = subprocess.run(
                command, cwd=ROOT, text=True, capture_output=True, check=False
            )
            assert first.returncode == 0, first.stdout + first.stderr
            assert target.read_bytes() == payload
            assert not part.exists()
            assert RangeHandler.ranges == [f"bytes={len(payload) // 3}-"]

            row = read_rows(release / "analyses.tsv")[0]
            assert row["checksum_algorithm"] == "sha256"
            assert row["checksum"] == hashlib.sha256(payload).hexdigest()
            assert int(row["size_bytes"]) == len(payload)
            download = read_rows(release / "sidecars" / "downloads.tsv")[0]
            assert download["status"] == "resumed"
            assert download["source_etag"] == '"fixture-etag"'
            assert "files: passed" in (release / "validation.yaml").read_text(encoding="utf-8")

            before = target.stat().st_mtime_ns
            second = subprocess.run(
                command, cwd=ROOT, text=True, capture_output=True, check=False
            )
            assert second.returncode == 0, second.stdout + second.stderr
            assert target.stat().st_mtime_ns == before
            assert read_rows(release / "sidecars" / "downloads.tsv")[0]["status"] == "cached"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    print("ALL 13 CHECKS PASSED")


if __name__ == "__main__":
    main()
