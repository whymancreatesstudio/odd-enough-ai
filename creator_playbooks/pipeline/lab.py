#!/usr/bin/env python3
"""Per-creator pipeline. Every stage skips finished work, so re-running resumes.

  python3 lab.py <n|slug> collect|transcribe|translate|label|analyse|all [--cap 500]

Keys: GROQ_API_KEY (whisper-large-v3 + translation), ~/.config/typesafe/api_key (Jev),
APIFY_TOKEN (Instagram only). Nothing here prints a key."""
import argparse, base64, concurrent.futures as cf, datetime as dt, json, os, pathlib, random, re, statistics, subprocess, sys, threading, time, uuid
import httpx

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
sys.path.insert(0, str(HERE.parent.parent / "content-lab"))
import questions  # Jev question wording, shared with Content Lab

CAP = 500
GROQ = "https://api.groq.com/openai/v1"
STT_MODEL, TR_MODEL = "whisper-large-v3", "openai/gpt-oss-120b"
JEV = "https://api.typesafe.ai/v1/systemone"
JEV_PRICE_PER_M = 0.042
YT_VIEWS_CHANGE = "2025-03-31"  # Shorts count every play from this date
LOW_LOGPROB = -0.8  # mean avg_logprob below this = low-confidence transcript
REFUSALS = ("429", "403", "too many requests", "sign in to confirm", "not a bot", "rate limit", "login required", "checkpoint")


def groq_key():
    return os.environ.get("GROQ_API_KEY", "proxy-injected")


def jev_key():
    f = pathlib.Path.home() / ".config/typesafe/api_key"
    return f.read_text().strip() if f.exists() else os.environ.get("TYPESAFE_API_KEY", "proxy-injected")


def rj(p): return json.loads(pathlib.Path(p).read_text())


def wj(p, o):
    p = pathlib.Path(p); t = p.with_suffix(p.suffix + ".tmp")
    t.write_text(json.dumps(o, ensure_ascii=False, indent=1)); t.replace(p)


def backoff(a, ra=None):
    try:
        if ra: return float(ra) + random.random()
    except ValueError:
        pass
    return min(60, 2 ** a) + random.random()


def post(client, url, retries=8, **kw):
    """POST with wait-and-retry on 429/5xx. An API error is raised, never turned into an answer."""
    for a in range(retries):
        try:
            r = client.post(url, **kw)
        except httpx.TransportError:
            time.sleep(backoff(a)); continue
        if r.status_code == 200: return r.json()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(backoff(a, r.headers.get("retry-after"))); continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    raise RuntimeError("gave up after retries")


class Creator:
    def __init__(self, c, cap):
        self.c, self.cap = c, cap
        self.dir = OUT / c["folder"]; self.data = self.dir / "data"; self.data.mkdir(parents=True, exist_ok=True)
        self.failures = self.dir / "failures.log"

    def log_fail(self, vid, stage, msg):
        with open(self.failures, "a") as f: f.write(f"{vid}\t{stage}\t{msg[:300]}\n")

    def ids(self, need=None):
        return sorted(p.name for p in self.data.iterdir() if (p / "info.json").exists() and (need is None or (p / need).exists()))

    # ---- 1+2. collect: list, then info + thumbnail + audio ---------------------------------------
    def collect(self):
        c = self.c
        if c["platform"] == "instagram":
            return self.collect_instagram()
        import yt_dlp
        listing = self.dir / "listing.json"
        if not listing.exists():
            r = subprocess.run(["yt-dlp", "--flat-playlist", "-J", "--playlist-items", f"1-{self.cap}", c["url"]], capture_output=True, text=True)
            if r.returncode or not r.stdout.strip(): sys.exit("listing failed: " + r.stderr[-400:])
            listing.write_text(r.stdout)
        entries = [e for e in json.loads(listing.read_text())["entries"] if e][: self.cap]
        print(f"{c['name']}: {len(entries)} shorts (most recent {self.cap})")
        st = {"ref": 0, "stop": False}; lock = threading.Lock()

        def one(e):
            vid = e["id"]; d = self.data / vid; d.mkdir(exist_ok=True)
            if (d / "info.json").exists() and (d / "thumb.jpg").exists() and list(d.glob("audio.*")): return "skip"
            with lock:
                if st["stop"]: return "stopped"
            time.sleep(random.uniform(1, 3))
            url = f"https://www.youtube.com/shorts/{vid}"
            try:
                o = {"quiet": True, "no_warnings": True, "noplaylist": True, "retries": 1}
                with yt_dlp.YoutubeDL({**o, "skip_download": True}) as y: info = y.extract_info(url, download=False)
                with yt_dlp.YoutubeDL({**o, "format": "ba[ext=m4a]/ba/b", "writethumbnail": True,
                                       "outtmpl": {"default": str(d / "audio.%(ext)s"), "thumbnail": str(d / "thumb")},
                                       "postprocessors": [{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}]}) as y:
                    y.process_ie_result(info, download=True)
                up = info.get("upload_date") or ""
                wj(d / "info.json", {"id": vid, "platform": "youtube", "url": url, "date": f"{up[:4]}-{up[4:6]}-{up[6:]}",
                    "views": info.get("view_count"), "likes": info.get("like_count"), "comments": info.get("comment_count"),
                    "duration": info.get("duration"), "title": info.get("title"), "caption": info.get("description"),
                    "thumbnail_url": info.get("thumbnail")})
                with lock: st["ref"] = 0
                return "ok"
            except Exception as ex:
                m = str(ex); refused = any(k in m.lower() for k in REFUSALS)
                self.log_fail(vid, "collect", m.splitlines()[-1] if m else "?")
                with lock:
                    st["ref"] = st["ref"] + 1 if refused else 0
                    if st["ref"] >= 5: st["stop"] = True
                return "refused" if refused else "error"
        self._run(one, entries, 2, lambda e: e["id"])
        if st["stop"]: print("!! 5 refusals in a row: stopped. Re-run later to resume.")

    def collect_instagram(self):
        tok = os.environ.get("APIFY_TOKEN")
        if not tok: sys.exit("Instagram needs APIFY_TOKEN (apify/instagram-reel-scraper). Not set.")
        items = []
        r = httpx.post("https://api.apify.com/v2/acts/apify~instagram-reel-scraper/run-sync-get-dataset-items",
                       params={"token": tok}, timeout=900,
                       json={"username": [self.c["url"].rstrip("/").split("/")[-1]], "resultsLimit": self.cap})
        r.raise_for_status(); items = r.json()
        wj(self.dir / "listing.json", items)
        for it in items:
            vid = it.get("shortCode") or str(it.get("id")); d = self.data / vid; d.mkdir(exist_ok=True)
            if (d / "info.json").exists(): continue
            ts = (it.get("timestamp") or "")[:10]
            wj(d / "info.json", {"id": vid, "platform": "instagram", "url": it.get("url"), "date": ts,
                "views": it.get("videoPlayCount") or it.get("videoViewCount"), "likes": it.get("likesCount"),
                "comments": it.get("commentsCount"), "duration": it.get("videoDuration"), "title": (it.get("caption") or "")[:100],
                "caption": it.get("caption"), "thumbnail_url": it.get("displayUrl"), "video_url": it.get("videoUrl")})
            for kind, u in (("thumb.jpg", it.get("displayUrl")), ("audio.mp4", it.get("videoUrl"))):
                if u and not (d / kind).exists():
                    try: (d / kind).write_bytes(httpx.get(u, timeout=120, follow_redirects=True).content)
                    except Exception as ex: self.log_fail(vid, "download", str(ex))
        print(f"{self.c['name']}: {len(items)} reels saved")

    def _run(self, fn, items, workers, key):
        counts = {}
        with cf.ThreadPoolExecutor(workers) as ex:
            for i, (it, r) in enumerate(zip(items, ex.map(fn, items)), 1):
                k = r.split(":")[0]; counts[k] = counts.get(k, 0) + 1
                if i % 50 == 0: print(f"  {i}/{len(items)} {counts}")
        print("  done:", counts)

    # ---- 3. transcribe: whisper-large-v3 on Groq --------------------------------------------------
    def transcribe(self):
        cli = httpx.Client(timeout=180); H = {"Authorization": f"Bearer {groq_key()}"}

        def one(vid):
            d = self.data / vid
            if (d / "transcript.json").exists(): return "skip"
            au = next(iter(sorted(d.glob("audio.*"))), None)
            if not au: return "no audio"
            data = {"model": STT_MODEL, "response_format": "verbose_json", "temperature": "0"}
            if self.c.get("lang"): data["language"] = self.c["lang"]
            try:
                j = post(cli, f"{GROQ}/audio/transcriptions", headers=H, files={"file": (au.name, au.read_bytes())}, data=data)
            except Exception as ex:
                self.log_fail(vid, "transcribe", str(ex)); return "error"
            segs = [{"start": s["start"], "end": s["end"], "text": s["text"].strip(), "avg_logprob": s.get("avg_logprob"),
                     "no_speech_prob": s.get("no_speech_prob")} for s in j.get("segments", [])]
            lp = [s["avg_logprob"] for s in segs if s["avg_logprob"] is not None]
            mean_lp = sum(lp) / len(lp) if lp else None
            wj(d / "transcript.json", {"model": STT_MODEL, "language": j.get("language"), "text": j["text"].strip(), "segments": segs,
                "duration": j.get("duration"), "mean_logprob": mean_lp,
                "low_confidence": bool(mean_lp is not None and mean_lp < LOW_LOGPROB)})
            return "ok"
        self._run(one, self.ids(), 8, None)

    # ---- 4. translate non-English to English ------------------------------------------------------
    def translate(self):
        cli = httpx.Client(timeout=120); H = {"Authorization": f"Bearer {groq_key()}"}

        def one(vid):
            d = self.data / vid; out = d / "english.json"
            if out.exists(): return "skip"
            if not (d / "transcript.json").exists(): return "no transcript"
            tr = rj(d / "transcript.json")
            sents = split_sentences(tr)
            if (tr.get("language") or "").lower() in ("english", "en"):
                wj(out, {"translated": False, "model": None, "sentences": sents}); return "ok"
            prompt = ("Translate each numbered sentence to natural English. Keep numbering and one sentence per line. "
                      "Output only the numbered translation.\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(sents, 1)))
            try:
                j = post(cli, f"{GROQ}/chat/completions", headers=H,
                         json={"model": TR_MODEL, "temperature": 0, "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]})
            except Exception as ex:
                self.log_fail(vid, "translate", str(ex)); return "error"
            lines = [re.sub(r"^\s*\d+[.)]\s*", "", l).strip() for l in j["choices"][0]["message"]["content"].splitlines() if l.strip()]
            if len(lines) != len(sents):
                self.log_fail(vid, "translate", f"line mismatch {len(lines)} vs {len(sents)}"); return "mismatch"
            wj(out, {"translated": True, "model": TR_MODEL, "source_language": tr.get("language"), "sentences": lines,
                     "original_sentences": sents}); return "ok"
        self._run(one, self.ids("transcript.json"), 8, None)

    # ---- 5. Jev labels, on the English sentences --------------------------------------------------
    def label(self):
        cli = httpx.Client(timeout=120); H = {"Authorization": f"Bearer {jev_key()}", "TypeSafe-Danger-Zone-Images": "true"}

        def one(vid):
            d = self.data / vid
            if (d / "jev.json").exists(): return "skip"
            if not (d / "english.json").exists() or not (d / "thumb.jpg").exists(): return "missing input"
            info, en = rj(d / "info.json"), rj(d / "english.json")
            sents = en["sentences"][:40]
            if not sents: return "empty"
            ref = str(uuid.uuid4())
            state, qs = questions.build(info.get("title") or "", sents, ref)
            payload = {"model": "jev-latest", "state": state, "questions": qs,
                       "assets": {ref: {"type": "image", "format": "jpg", "data_base64": base64.b64encode((d / "thumb.jpg").read_bytes()).decode()}}}
            try:
                j = post(cli, JEV, headers=H, json=payload)
            except Exception as ex:
                self.log_fail(vid, "label", str(ex)); return "error"
            wj(d / "jev.json", {"model": j["model"], "on_english_translation": en["translated"], "sentences": sents,
                                "answers": j["answers"], "usage": j["usage"]}); return "ok"
        self._run(one, self.ids("english.json"), 6, None)
        tok = sum(rj(p)["usage"]["input_tokens"] for p in self.data.glob("*/jev.json"))
        print(f"  Jev so far for {self.c['name']}: {tok:,} tokens = ${tok * JEV_PRICE_PER_M / 1e6:.4f}")

    # ---- 6. analyse: lift, classes, distribution -> shorts_full.json ------------------------------
    def analyse(self):
        V = []
        for vid in self.ids("jev.json"):
            d = self.data / vid; i, j = rj(d / "info.json"), rj(d / "jev.json"); t = rj(d / "transcript.json")
            a = j["answers"]; n = len(j["sentences"])
            if not i.get("date") or i.get("views") is None: continue
            V.append({"id": vid, "date": i["date"], "views": i["views"], "likes": i.get("likes"), "comments": i.get("comments"),
                "duration": i.get("duration"), "title": i.get("title"), "caption": i.get("caption"), "url": i.get("url"),
                "language": t.get("language"), "stt_model": t["model"], "low_confidence": t["low_confidence"],
                "labelled_on_translation": j["on_english_translation"],
                "style": a["style"]["choice"], "style_p": max(a["style"]["probabilities"].values()),
                "hook": a["hook"]["choice"], "hook_p": max(a["hook"]["probabilities"].values()),
                "has_cta": a["has_cta"]["noul"], "n_sentences": n,
                "kind": "talking" if n >= 5 else "text_music" if n <= 2 else "in_between",
                "pre_view_change": i["date"] < YT_VIEWS_CHANGE if i["platform"] == "youtube" else None,
                "sentences": [{"text": s, "role": a.get(f"role_{k}", {}).get("choice")} for k, s in enumerate(j["sentences"], 1)]})
        if not V: sys.exit("nothing labelled yet")
        days = lambda s: dt.date.fromisoformat(s).toordinal()
        for v in V:  # lift = views / median views of the creator's OTHER shorts within +-45 days
            nb = [w["views"] for w in V if w is not v and abs(days(w["date"]) - days(v["date"])) <= 45]
            v["lift"] = v["views"] / statistics.median(nb) if len(nb) >= 3 and statistics.median(nb) > 0 else None
            v["big_win"] = v["lift"] is not None and v["lift"] >= 3.0
            v["flop"] = v["lift"] is not None and v["lift"] <= 0.5
        def agg(key):
            g = {}
            for v in V:
                if v["lift"] is not None: g.setdefault(key(v), []).append(v)
            return sorted(({"group": k, "n": len(x), "median_lift": round(statistics.median(y["lift"] for y in x), 3),
                            "big_win_rate": round(sum(y["big_win"] for y in x) / len(x), 3),
                            "flop_rate": round(sum(y["flop"] for y in x) / len(x), 3),
                            "median_views": statistics.median(y["views"] for y in x)} for k, x in g.items()), key=lambda r: -r["median_lift"])
        views = sorted((v["views"] for v in V), reverse=True)
        share = lambda f: sum(views[: max(1, int(len(views) * f))]) / sum(views)
        half = lambda v: f"{v['date'][:4]}-H{1 if int(v['date'][5:7]) <= 6 else 2}"
        res = {"creator": self.c["name"], "platform": self.c["platform"], "n_videos": len(V), "cap": self.cap,
               "distribution": {"median": statistics.median(views), "mean": sum(views) / len(views),
                                "top10pct_share": share(0.10), "top1pct_share": share(0.01),
                                "by_half_year": {h: {"n": len(x), "median": statistics.median(y["views"] for y in x)}
                                                 for h in sorted({half(v) for v in V}) for x in [[y for y in V if half(y) == h]]}},
               "by_style": agg(lambda v: v["style"]), "by_hook": agg(lambda v: v["hook"]),
               "by_style_x_hook": agg(lambda v: f"{v['style']} x {v['hook']}"), "by_kind": agg(lambda v: v["kind"]),
               "by_language": agg(lambda v: v["language"]), "by_cta": agg(lambda v: v["has_cta"] >= 0.7),
               "low_confidence_transcripts": sum(v["low_confidence"] for v in V),
               "view_definition_note": f"YouTube Shorts count every play from {YT_VIEWS_CHANGE}; compare across that date with care.",
               "videos": V}
        wj(self.dir / "shorts_full.json", res)
        print(f"{self.c['name']}: {len(V)} videos -> shorts_full.json (median {res['distribution']['median']:,.0f}, top-10% share {res['distribution']['top10pct_share']:.0%})")


def split_sentences(tr):
    text = re.sub(r"\s+", " ", tr["text"]).strip()
    parts = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]
    if len(parts) == 1 and len(tr.get("segments", [])) > 1 and len(text) > 200:
        parts = [s["text"] for s in tr["segments"] if s["text"]]
    return parts[:40]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("who"); ap.add_argument("stage"); ap.add_argument("--cap", type=int, default=CAP)
    a = ap.parse_args()
    cs = json.loads((HERE / "creators.json").read_text())
    c = next((c for c in cs if str(c["n"]) == a.who or a.who in c["folder"]), None) or sys.exit("unknown creator")
    cr = Creator(c, a.cap)
    for st in (["collect", "transcribe", "translate", "label", "analyse"] if a.stage == "all" else [a.stage]):
        print(f"== {c['name']}: {st}"); getattr(cr, st)()
