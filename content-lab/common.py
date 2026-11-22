"""Shared helpers for the Content Lab scripts. Never prints API keys."""
import datetime as dt
import json
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path(os.environ.get("LAB_DATA", ROOT / "data"))
for _d in ("info", "thumbs", "audio", "transcripts", "jev"):
    (DATA / _d).mkdir(parents=True, exist_ok=True)
CONFIG = DATA / "config.json"

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_PRICE_PER_M_INPUT = 0.042  # USD per million input tokens (output is free)


def load_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, obj):
    path = pathlib.Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False))
    tmp.replace(path)  # atomic, so a killed run never leaves half a file


def parse_since(text):
    """'2y', '18m', '90d' or 'YYYY-MM-DD' -> a date."""
    text = text.strip().lower()
    m = re.fullmatch(r"(\d+)\s*([ymd])", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"y": 365, "m": 30, "d": 1}[unit] * n
        return dt.date.today() - dt.timedelta(days=days)
    return dt.date.fromisoformat(text)


def jev_headers():
    """Key from ~/.config/typesafe/api_key if present; otherwise rely on a proxy that injects it."""
    h = {"content-type": "application/json", "TypeSafe-Danger-Zone-Images": "true"}
    key_file = pathlib.Path.home() / ".config" / "typesafe" / "api_key"
    if key_file.exists() and key_file.read_text().strip():
        h["Authorization"] = "Bearer " + key_file.read_text().strip()
    return h


def openai_headers():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return {"Authorization": "Bearer " + (key or "proxy-supplied")}


def split_sentences(text, max_words=35):
    """Split a transcript into sentences; hard-wrap run-ons so no 'sentence' is huge."""
    out = []
    for part in re.split(r"(?<=[.!?…])\s+", text.strip()):
        words = part.split()
        while len(words) > int(max_words * 1.5):
            out.append(" ".join(words[:max_words]))
            words = words[max_words:]
        if words:
            out.append(" ".join(words))
    return out


def video_ids():
    return sorted(p.stem for p in (DATA / "info").glob("*.json"))
