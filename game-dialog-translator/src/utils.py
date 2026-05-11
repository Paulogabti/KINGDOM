from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def calc_lines_per_minute(translated: int, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 0.0
    return translated / elapsed_seconds * 60


def calc_eta_seconds(pending: int, lines_per_minute: float) -> float:
    if lines_per_minute <= 0:
        return 0.0
    return (pending / lines_per_minute) * 60


def calc_percent(done: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (done / total) * 100


def moving_average(values: Iterable[float]) -> float:
    vals = [v for v in values if v > 0]
    return sum(vals) / len(vals) if vals else 0.0


def eta_finish_time(eta_seconds: float) -> str:
    return (datetime.now() + timedelta(seconds=eta_seconds)).strftime("%H:%M:%S")


def now_ts() -> float:
    return time.time()
