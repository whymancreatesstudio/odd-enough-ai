"""Step 2. Transcribe each audio file with OpenAI whisper-1 (verbose_json), 8 at a time.
Saves the text and the timed segments. Re-runnable: finished transcripts are skipped."""
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from common import DATA, openai_headers, save_json

URL = "https://api.openai.com/v1/audio/transcriptions"
bad_key = False


def transcribe(audio_path):
    global bad_key
    vid = audio_path.stem
    out = DATA / "transcripts" / f"{vid}.json"
    if out.exists() or bad_key:
        return "skipped"
    for attempt in range(6):
        try:
            with open(audio_path, "rb") as f:
                r = httpx.post(URL, headers=openai_headers(), timeout=180,
                               data={"model": "whisper-1", "response_format": "verbose_json"},
                               files={"file": (audio_path.name, f, "audio/mpeg")})
        except httpx.HTTPError as e:
            r = None
            print(f"  {vid}: network error ({type(e).__name__}), retrying")
        if r is not None and r.status_code == 200:
            j = r.json()
            save_json(out, {"id": vid, "language": j.get("language"), "duration": j.get("duration"),
                            "text": (j.get("text") or "").strip(),
                            "segments": [{"start": s["start"], "end": s["end"], "text": s["text"].strip()}
                                         for s in j.get("segments", [])]})
            return "saved"
        if r is not None and r.status_code == 401:
            bad_key = True
            print("STOP: OpenAI rejected the API key (401). Set a valid OPENAI_API_KEY and re-run.")
            return "failed"
        if r is not None and r.status_code not in (429, 500, 502, 503, 504):
            print(f"  {vid}: HTTP {r.status_code} {r.text[:160]}")
            return "failed"
        wait = float(r.headers.get("retry-after", 0)) if r is not None else 0
        time.sleep(max(wait, 2 ** attempt))
    print(f"  {vid}: gave up after retries")
    return "failed"


def main():
    files = sorted((DATA / "audio").glob("*.mp3"))
    todo = [f for f in files if not (DATA / "transcripts" / f"{f.stem}.json").exists()]
    print(f"{len(files)} audio files, {len(todo)} still to transcribe (8 at a time).")
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(transcribe, todo))
    print("Done:", {k: results.count(k) for k in set(results)})


if __name__ == "__main__":
    main()
