from __future__ import annotations

import hashlib
from pathlib import Path


def fingerprint_for_file(path: Path) -> str:
    stat = path.stat()
    data = f"{path}|{stat.st_size}|{int(stat.st_mtime)}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()
