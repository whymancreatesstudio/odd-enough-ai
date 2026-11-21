"""Shared helpers for the Content Lab scripts. Keys are read, never printed."""
import json, os, pathlib, time, random

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
CONFIG = ROOT / "config.json"


def load_config():
    if not CONFIG.exists():
        raise SystemExit("config.json missing - run 1_collect.py with --channel and --since first")
    return json.loads(CONFIG.read_text())


def vid_dir(vid):
    d = DATA / vid
    d.mkdir(parents=True, exist_ok=True)
    return d


def all_videos():
    """Video ids that have been collected and are inside the date range."""
    if not DATA.exists():
        return []
    return sorted(p.name for p in DATA.iterdir() if (p / "info.json").exists())


def read_json(p):
    return json.loads(pathlib.Path(p).read_text())


def write_json(p, obj):
    p = pathlib.Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    tmp.replace(p)  # atomic, so a killed run never leaves half a file


def typesafe_key():
    f = pathlib.Path.home() / ".config/typesafe/api_key"
    if f.exists():
        return f.read_text().strip()
    # Falls back to an env var (or a placeholder when a proxy injects the real key).
    return os.environ.get("TYPESAFE_API_KEY", "proxy-injected")


def openai_key():
    return os.environ.get("OPENAI_API_KEY", "proxy-injected")


def backoff(attempt, retry_after=None):
    if retry_after:
        try:
            return float(retry_after) + random.random()
        except ValueError:
            pass
    return min(60, 2 ** attempt) + random.random()
