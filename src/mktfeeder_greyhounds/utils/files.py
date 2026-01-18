from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, Mapping, Sequence

import pandas as pd

from src.mktfeeder_greyhounds.config import settings


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Mapping[str, object]], *, columns: Sequence[str] | None = None) -> None:
    ensure_dir(path.parent)
    rows_list = list(rows)
    if columns:
        df = pd.DataFrame(rows_list, columns=columns)
    else:
        df = pd.DataFrame(rows_list)
    df.to_csv(path, index=False, encoding=settings.CSV_ENCODING)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def atomic_write_text(path: Path, content: str, *, encoding: str | None = None) -> None:
    """Escreve arquivo de forma segura via tmp + replace."""
    encoding = encoding or settings.CSV_ENCODING
    ensure_dir(path.parent)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding=encoding, newline="") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        if path.exists():
            path.unlink()
        tmp_path.replace(path)
    finally:
        if tmp_path.exists() and tmp_path != path:
            tmp_path.unlink(missing_ok=True)


def write_dataframe(df: pd.DataFrame, csv_path: Path) -> None:
    ensure_dir(csv_path.parent)
    df.to_csv(csv_path, index=False, encoding=settings.CSV_ENCODING)


__all__ = ["ensure_dir", "write_csv", "read_csv", "atomic_write_text", "write_dataframe"]

