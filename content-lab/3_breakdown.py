"""Step 3. Break every video down with Jev: one call per video, 6 at a time.
Saves every answer with its probabilities and the tokens used. Re-runnable.
Prints the total Jev cost at $0.042 per million input tokens."""
import base64
import random
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx

from common import (DATA, JEV_PRICE_PER_M_INPUT, JEV_URL, jev_headers, load_json, save_json,
                    split_sentences, video_ids)

STYLE = {
    "storytelling": "tells a story with a lesson at the end",
    "tactical": "teaches a how-to, steps, a framework or a tactic",
    "opinion": "a hot take or contrarian opinion",
    "qa": "answers a question someone asked",
    "mindset": "motivation, mindset or discipline advice",
}
HOOK = {
    "question": "the first sentence asks the viewer a question",
    "claim": "the first sentence makes a bold or surprising claim",
    "story": "the first sentence drops you into a story",
    "callout": "the first sentence calls out a kind of person",
    "number": "the first sentence leads with a number or a result",
}
ROLE = {
    "hook": "opens the video and grabs attention",
    "setup": "sets up the context, the problem or the situation",
    "body": "the main content: steps, points or the story developing",
    "payoff": "delivers the lesson, punchline, result or conclusion",
    "cta": "asks the viewer to do something (follow, comment, click, subscribe, buy)",
}
MAX_SENTENCES = 60
lock = threading.Lock()
fatal = threading.Event()


def normalized_jpeg(path):
    """Jev rejects images that are too small or too large (270x480 and 1080x1920 both failed),
    so fit every thumbnail inside 540x960 (or 960x540 if landscape), up- or down-scaling as needed."""
    vf = "scale='if(gt(iw,ih),960,540)':'if(gt(iw,ih),540,960)':force_original_aspect_ratio=decrease"
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", vf, "-frames:v", "1",
                        "-f", "image2pipe", "-c:v", "mjpeg", "-q:v", "3", "pipe:1"], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(f"ffmpeg could not read {path}: {p.stderr.decode()[-200:]}")
    return p.stdout


def build_request(info, sentences, thumb_path):
    ph = str(uuid.uuid4())
    questions = {
        "style": {"type": "choice", "criteria": STYLE,
                  "instructions": "What kind of short-form video is this? Judge it from the title, the thumbnail and the whole script."},
        "hook": {"type": "choice", "criteria": HOOK,
                 "instructions": "How does the first sentence of the script (`script[0].text`) hook the viewer?"},
        "has_cta": {"type": "noul",
                    "instructions": "Does the script end with a call to action, i.e. does it ask the viewer to follow, subscribe, comment, click a link, buy or join something?"},
    }
    for i in range(len(sentences)):
        questions[f"role_{i}"] = {
            "type": "choice", "criteria": ROLE,
            "instructions": f"What role does sentence {i + 1} of the script (`script[{i}].text`) play in the video?"}
    return {
        "model": "jev-latest",
        "state": {"title": info["title"], "thumbnail": ph,
                  "script": [{"n": i + 1, "text": s} for i, s in enumerate(sentences)]},
        "questions": questions,
        "assets": {ph: {"type": "image", "format": "jpg",
                        "data_base64": base64.b64encode(normalized_jpeg(thumb_path)).decode()}},
    }


def call(body, vid):
    for attempt in range(8):
        try:
            r = httpx.post(JEV_URL, headers=jev_headers(), json=body, timeout=180)
        except httpx.HTTPError as e:
            print(f"  {vid}: network error ({type(e).__name__}), retrying")
            time.sleep(2 ** min(attempt, 5))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (401, 403):
            fatal.set()
            print(f"STOP: Jev rejected the key (HTTP {r.status_code}). Check ~/.config/typesafe/api_key.")
            return None
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("retry-after") or 0) or min(60, 2 ** attempt)
            time.sleep(wait + random.uniform(0, 1))
            continue
        print(f"  {vid}: HTTP {r.status_code} {r.text[:200]}")
        return None
    print(f"  {vid}: gave up after retries")
    return None


def process(vid):
    out = DATA / "jev" / f"{vid}.json"
    if out.exists() or fatal.is_set():
        return "skipped"
    info = load_json(DATA / "info" / f"{vid}.json")
    tr = load_json(DATA / "transcripts" / f"{vid}.json")
    thumb = DATA / "thumbs" / f"{vid}.jpg"
    if not info or not info.get("in_range") or not tr or not thumb.exists():
        return "not-ready"
    sentences = split_sentences(tr["text"])[:MAX_SENTENCES]
    if not sentences:
        save_json(out, {"id": vid, "skipped": "no speech in transcript"})
        return "no-speech"
    resp = call(build_request(info, sentences, thumb), vid)
    if resp is None:
        return "failed"
    save_json(out, {"id": vid, "model": resp["model"], "sentences": sentences,
                    "answers": resp["answers"], "usage": resp["usage"]})
    return "saved"


def total_cost():
    tokens = sum((load_json(p, {}).get("usage") or {}).get("input_tokens", 0) for p in (DATA / "jev").glob("*.json"))
    return tokens, tokens * JEV_PRICE_PER_M_INPUT / 1e6


def main():
    ids = [v for v in video_ids() if not (DATA / "jev" / f"{v}.json").exists()]
    print(f"{len(ids)} videos to break down (6 at a time).")
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(process, ids))
    print("Done:", {k: results.count(k) for k in set(results)})
    tokens, cost = total_cost()
    print(f"Total Jev usage: {tokens:,} input tokens = ${cost:.4f} at ${JEV_PRICE_PER_M_INPUT}/M")


if __name__ == "__main__":
    main()
