#!/usr/bin/env python3
"""Step 3. One Jev call per video (jev-latest, with the thumbnail as an image asset).
Saves jev.json = {sentences, answers (with probabilities), usage}. Skips finished ones.
Prints the total input-token cost at $0.042 per million tokens."""
import base64, concurrent.futures as cf, re, sys, time, uuid
import httpx
from common import *
import questions

URL = "https://api.typesafe.ai/v1/systemone"
PRICE_PER_M = 0.042
MAX_SENTENCES = 40
client = httpx.Client(timeout=120)
HEADERS = {"Authorization": f"Bearer {typesafe_key()}", "TypeSafe-Danger-Zone-Images": "true"}


def split_sentences(tr):
    text = re.sub(r"\s+", " ", tr["text"]).strip()
    parts = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]
    if len(parts) == 1 and len(tr.get("segments", [])) > 1 and len(text) > 200:
        parts = [s["text"] for s in tr["segments"] if s["text"]]  # no punctuation: fall back to timed segments
    return parts[:MAX_SENTENCES]


def call(payload):
    for attempt in range(8):
        try:
            r = client.post(URL, json=payload, headers=HEADERS)
        except httpx.TransportError:
            time.sleep(backoff(attempt)); continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(backoff(attempt, r.headers.get("retry-after"))); continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")  # an API error is an error, never an answer
    raise RuntimeError("gave up after repeated 429/5xx")


def work(vid):
    d = DATA / vid
    out = d / "jev.json"
    if out.exists():
        return vid, "skip"
    if not (d / "transcript.json").exists():
        return vid, "no transcript"
    info, tr = read_json(d / "info.json"), read_json(d / "transcript.json")
    sentences = split_sentences(tr)
    if not sentences:
        return vid, "empty transcript"
    ref = str(uuid.uuid4())
    state, qs = questions.build(info["title"], sentences, ref)
    thumb = base64.b64encode((d / "thumb.jpg").read_bytes()).decode()
    payload = {"model": "jev-latest", "state": state, "questions": qs,
               "assets": {ref: {"type": "image", "format": "jpg", "data_base64": thumb}}}
    try:
        res = call(payload)
    except Exception as e:
        return vid, f"error: {e}"
    write_json(out, {"model": res["model"], "sentences": sentences, "answers": res["answers"], "usage": res["usage"]})
    return vid, "ok"


if __name__ == "__main__":
    ids = all_videos()
    counts = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for i, (vid, r) in enumerate(ex.map(work, ids), 1):
            k = r.split(":")[0]; counts[k] = counts.get(k, 0) + 1
            if r not in ("ok", "skip"):
                print(f"  {vid}: {r}")
            if i % 25 == 0:
                print(f"  {i}/{len(ids)}  {counts}")
    tok = sum(read_json(p)["usage"]["input_tokens"] for p in DATA.glob("*/jev.json"))
    n = len(list(DATA.glob("*/jev.json")))
    print("done:", counts)
    print(f"Jev total: {n} videos, {tok:,} input tokens -> ${tok * PRICE_PER_M / 1e6:.4f} (at ${PRICE_PER_M}/M)")
