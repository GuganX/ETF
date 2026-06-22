"""Load the list of ETFs to track from a YAML config file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = "etfs.yaml"


@dataclass(frozen=True)
class Config:
    etfids: list[str]
    db_path: str


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    etfids = [str(e).strip() for e in data.get("etfids", []) if str(e).strip()]
    if not etfids:
        raise ValueError(f"No etfids configured in {path}")
    db_path = str(data.get("db_path", "etf_holdings.db"))
    return Config(etfids=etfids, db_path=db_path)
