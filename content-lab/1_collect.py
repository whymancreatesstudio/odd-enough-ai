"""Step 1. Collect: list every video, then save info.json, thumbnail and audio for those in range.
Re-runnable: anything already on disk is skipped.

  python 1_collect.py https://www.youtube.com/@hormozi/shorts --since 2y
"""
import argparse
import datetime as dt
import json
import random
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from common import DATA, load_json, parse_since, save_json, CONFIG

REFUSAL = re.compile(
    r"HTTP Error (403|429)|Too Many Requests|rate.?limit|Sign in to confirm|not a bot|"
    r"login required|checkpoint|Requested content is not available", re.I)
MAX_REFUSALS = 5   # stop after this many refusals in a row
OLD_STREAK_STOP = 3  # feeds are newest-first: stop after this many out-of-range videos in a row

lock = threading.Lock()
stop = threading.Event()
state = {"refusals": 0, "old": 0}


def ytdlp(args, instagram):
    cmd = ["yt-dlp", "--no-warnings"] + (["--cookies-from-browser", "chrome"] if instagram else []) + args
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def flatten(entries):
    for e in entries or []:
        if e.get("entries"):
            yield from flatten(e["entries"])
        elif e.get("id"):
            yield e


def trim(raw):
    desc = (raw.get("description") or "").strip()
    title = (raw.get("title") or "").strip() or desc.split("\n")[0][:120]
    date = raw.get("upload_date")
    if not date and raw.get("timestamp"):
        date = dt.datetime.fromtimestamp(raw["timestamp"], dt.timezone.utc).strftime("%Y%m%d")
    return {"id": raw["id"], "title": title, "upload_date": date, "views": raw.get("view_count"),
            "likes": raw.get("like_count"), "comments": raw.get("comment_count"),
            "duration": raw.get("duration"), "url": raw.get("webpage_url"), "uploader": raw.get("uploader")}


def refused(err):
    with lock:
        state["refusals"] += 1
        n = state["refusals"]
    print(f"  refusal {n}/{MAX_REFUSALS}: {err.strip().splitlines()[-1][:140] if err.strip() else ''}")
    if n >= MAX_REFUSALS:
        print(f"STOP: {MAX_REFUSALS} refusals in a row. Wait a while (or change network), then re-run; finished work is kept.")
        stop.set()


def work(entry, cutoff, instagram):
    if stop.is_set():
        return "skipped"
    vid = entry["id"]
    url = entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/shorts/{vid}"
    info_path = DATA / "info" / f"{vid}.json"
    thumb, audio = DATA / "thumbs" / f"{vid}.jpg", DATA / "audio" / f"{vid}.mp3"
    info = load_json(info_path)
    if info is None:
        rc, out, err = ytdlp(["-j", "--no-playlist", url], instagram)
        time.sleep(random.uniform(1, 3))
        if rc != 0:
            if REFUSAL.search(err):
                refused(err)
            else:
                print(f"  {vid}: unavailable ({err.strip().splitlines()[-1][:100] if err.strip() else 'error'})")
            return "failed"
        with lock:
            state["refusals"] = 0
        info = trim(json.loads(out))
        info["in_range"] = (not info["upload_date"]) or dt.datetime.strptime(info["upload_date"], "%Y%m%d").date() >= cutoff
        save_json(info_path, info)
    if not info["in_range"]:
        with lock:
            state["old"] += 1
            if state["old"] >= OLD_STREAK_STOP:
                stop.set()
        return "old"
    with lock:
        state["old"] = 0
    if thumb.exists() and audio.exists():
        return "done"
    rc, out, err = ytdlp([
        "--no-playlist", "-f", "bestaudio/best", "-x", "--audio-format", "mp3", "--audio-quality", "9",
        "--write-thumbnail", "--convert-thumbnails", "jpg",
        "-o", f"thumbnail:{DATA}/thumbs/%(id)s.%(ext)s", "-o", f"{DATA}/audio/%(id)s.%(ext)s", url], instagram)
    time.sleep(random.uniform(1, 3))
    if rc != 0:
        if REFUSAL.search(err):
            refused(err)
        else:
            print(f"  {vid}: download failed ({err.strip().splitlines()[-1][:100] if err.strip() else 'error'})")
        return "failed"
    with lock:
        state["refusals"] = 0
    print(f"  saved {vid}  {info['upload_date']}  {info['views']} views  {info['title'][:60]}")
    return "saved"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="YouTube Shorts tab URL or Instagram profile URL")
    ap.add_argument("--since", help="how far back: 2y, 18m, 90d or YYYY-MM-DD")
    ap.add_argument("--limit", type=int, help="only look at the newest N videos (for a trial run)")
    a = ap.parse_args()
    cfg = load_json(CONFIG, {})
    url, since = a.url or cfg.get("url"), a.since or cfg.get("since")
    if not url or not since:
        ap.error("give a URL and --since the first time")
    save_json(CONFIG, {"url": url, "since": since})
    cutoff = parse_since(since)
    instagram = "instagram.com" in url
    workers = 1 if instagram else 2

    print(f"Listing {url} (videos from {cutoff} on, {workers} at a time)...")
    rc, out, err = ytdlp(["--flat-playlist", "-J", url], instagram)
    if rc != 0:
        raise SystemExit("Could not list the profile:\n" + err[-600:])
    entries = list(flatten(json.loads(out).get("entries")))
    if a.limit:
        entries = entries[: a.limit]
    print(f"Found {len(entries)} videos.")
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda e: work(e, cutoff, instagram), entries))
    tally = {k: results.count(k) for k in set(results)}
    print("Done:", tally)


if __name__ == "__main__":
    main()
