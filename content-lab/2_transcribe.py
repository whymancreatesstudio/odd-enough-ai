#!/usr/bin/env python3
"""Step 2. whisper-1 (verbose_json) on every audio file, 8 at a time.
Saves transcript.json = {text, language, duration, segments[{start,end,text}]}. Skips finished ones."""
import concurrent.futures as cf, time
from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError
from common import *

client = OpenAI(api_key=openai_key(), max_retries=0)


def work(vid):
    d = DATA / vid
    out = d / "transcript.json"
    if out.exists():
        return vid, "skip"
    audio = next(iter(sorted(d.glob("audio.*"))), None)
    if not audio:
        return vid, "no audio"
    for attempt in range(6):
        try:
            with open(audio, "rb") as fh:
                r = client.audio.transcriptions.create(model="whisper-1", file=fh, response_format="verbose_json")
            segs = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in (r.segments or [])]
            write_json(out, {"text": r.text.strip(), "language": getattr(r, "language", None),
                             "duration": getattr(r, "duration", None), "segments": segs})
            return vid, "ok"
        except (RateLimitError, APIConnectionError) as e:
            time.sleep(backoff(attempt, getattr(getattr(e, "response", None), "headers", {}).get("retry-after")))
        except APIStatusError as e:
            if e.status_code >= 500:
                time.sleep(backoff(attempt))
            else:
                return vid, f"error {e.status_code}: {str(e)[:120]}"
    return vid, "gave up"


ids = all_videos()
counts = {}
with cf.ThreadPoolExecutor(8) as ex:
    for i, (vid, r) in enumerate(ex.map(work, ids), 1):
        counts[r.split(":")[0]] = counts.get(r.split(":")[0], 0) + 1
        if r not in ("ok", "skip"):
            print(f"  {vid}: {r}")
        if i % 25 == 0:
            print(f"  {i}/{len(ids)}  {counts}")
print("done:", counts)
