#!/usr/bin/env python3
"""Build one creator's playbook (Markdown + PDF + charts) from its shorts_full.json.

  python3 playbook.py <folder-or-number> [--no-pdf]

Numbers, tables, charts, swipe files, appendices and the full register are computed.
Qualitative parts (why a family worked, narrative for formats/languages) come from
<folder>/editorial.json, written after reading the numbers. If a key is missing the page says so."""
import argparse, collections, datetime as dt, html, json, math, pathlib, re, statistics, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
MIN_GROUP = 8          # smallest group shown in style x hook / shapes tables
BIG, FLOP = 3.0, 0.5
STYLES = ["storytelling", "tactical", "opinion", "qa", "mindset"]
HOOKS = ["question", "claim", "story", "callout", "number"]
COL = {"storytelling": "#d55e00", "tactical": "#0072b2", "opinion": "#cc79a7", "qa": "#009e73", "mindset": "#b8a000"}
YT_CHANGE = "2025-03-31"


# ---------------------------------------------------------------- helpers
def med(x): x = [v for v in x if v is not None]; return statistics.median(x) if x else None
def mean(x): x = [v for v in x if v is not None]; return sum(x) / len(x) if x else None
def f0(x): return "n/a" if x is None else f"{x:,.0f}"
def f2(x): return "n/a" if x is None else f"{x:.2f}"
def pct(x): return "n/a" if x is None else f"{x * 100:.0f}%"
def short(n):
    if n is None: return "n/a"
    return f"{n/1e9:.1f}B" if n >= 1e9 else f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.0f}K" if n >= 1e3 else f"{n:.0f}"
def esc(s): return str(s).replace("|", "\\|").replace("\n", " ")
def words(s): return len(re.findall(r"\S+", s))


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def lifts(vs): return [v["lift"] for v in vs if v["lift"] is not None]


def stats(vs):
    L = lifts(vs)
    return {"n": len(vs), "n_lift": len(L), "views": med([v["views"] for v in vs]), "lift": med(L), "mean_lift": mean(L),
            "big": sum(l >= BIG for l in L) / len(L) if L else None, "flop": sum(l <= FLOP for l in L) / len(L) if L else None}


def stat_row(label, vs):
    s = stats(vs)
    return [label, s["n"], f0(s["views"]), f2(s["lift"]), f2(s["mean_lift"]), pct(s["big"]), pct(s["flop"])]


STAT_H = ["Group", "n", "Median views", "Median lift", "Mean lift", "Big-win %", "Flop %"]


def by(vs, key, order=None, min_n=1):
    g = collections.defaultdict(list)
    for v in vs:
        k = key(v)
        if k is not None: g[k].append(v)
    keys = order or sorted(g, key=lambda k: -(med(lifts(g[k])) or 0))
    return [(k, g[k]) for k in keys if len(g.get(k, [])) >= min_n]


def group_table(vs, key, order=None, min_n=1, sort_lift=True):
    items = by(vs, key, order, min_n)
    if sort_lift: items.sort(key=lambda kv: -(med(lifts(kv[1])) or 0))
    return table(STAT_H, [stat_row(k, g) for k, g in items]), items


def tag(n, consistent=True, effect=1.0):
    """Confidence tag: Strong = big sample, clear effect, same direction in both halves of time."""
    if n >= 100 and consistent and abs(math.log(max(effect, 1e-6))) >= math.log(1.15): return "[Strong]"
    if n >= 20: return "[Moderate]"
    return "[Anecdotal]"


def consistent(vs_with, all_vs, split_date):
    """Does the group's median lift sit on the same side of 1.0 in both halves of the timeline?"""
    sides = []
    for part in ([v for v in vs_with if v["date"] < split_date], [v for v in vs_with if v["date"] >= split_date]):
        m = med(lifts(part)); sides.append(None if m is None or len(part) < 5 else m > 1)
    return None not in sides and sides[0] == sides[1]


def half(v): return f"{v['date'][:4]} H{1 if int(v['date'][5:7]) <= 6 else 2}"
def year(v): return v["date"][:4]
def link(v): return v["url"]


# ---------------------------------------------------------------- features
GREET = re.compile(r"^\W*(hi|hello|hey|welcome|namaste|namaskaram|vanakkam|good (morning|evening)|guys|friends)\b", re.I)
FEATURES = [
    ("Contains a digit", lambda s: bool(re.search(r"\d", s))),
    ("Contains a ?", lambda s: "?" in s),
    ("Starts with a greeting", lambda s: bool(GREET.search(s))),
    ("Starts Stop / Don't / Never / Avoid", lambda s: bool(re.match(r"^\W*(stop|don'?t|do not|never|avoid)\b", s, re.I))),
    ("Starts Why / How / What / Who", lambda s: bool(re.match(r"^\W*(why|how|what|who|when|where)\b", s, re.I))),
    ("Starts Do you / Did you know / Have you", lambda s: bool(re.match(r"^\W*(do you|did you|have you|can you|would you)\b", s, re.I))),
    ("Starts If you", lambda s: bool(re.match(r"^\W*if you\b", s, re.I))),
    ("Starts This is / This", lambda s: bool(re.match(r"^\W*this\b", s, re.I))),
    ("Contains biggest / most / best / worst / only", lambda s: bool(re.search(r"\b(biggest|most|best|worst|top|only|ultimate|greatest)\b", s, re.I))),
    ("Contains you / your", lambda s: bool(re.search(r"\b(you|your|you're)\b", s, re.I))),
    ("First person (I / my / we)", lambda s: bool(re.search(r"\b(i|i'm|i've|my|we|our)\b", s, re.I))),
    ("Money amount (\u20b9 / $ / lakh / crore / million)", lambda s: bool(re.search(r"[\u20b9$]|\b(rs\.?|rupees?|lakhs?|crores?|dollars?|million|billion|thousand)\b", s, re.I))),
    ("Mentions mistake / scam / lie / secret / truth", lambda s: bool(re.search(r"\b(mistakes?|scams?|lies?|lied|secrets?|truth|myths?|fraud|trap)\b", s, re.I))),
    ("Contains 'without'", lambda s: bool(re.search(r"\bwithout\b", s, re.I))),
    ("Contains a name (2+ capitalised words mid-sentence)", lambda s: bool(re.search(r"(?<!^)(?<![.!?] )\b[A-Z][a-z]+ [A-Z][a-z]+", s))),
]
ELEMENTS = [
    ("Checklist (make sure / check, 3+ times)", lambda t: len(re.findall(r"\b(make sure|check)\b", t, re.I)) >= 3),
    ("Personal experience (I've / in my / years ago)", lambda t: bool(re.search(r"\b(i've|i have|in my (career|life|experience)|years ago|when i|my experience)\b", t, re.I))),
    ("Countdown / numbered list", lambda t: bool(re.search(r"\b(number (one|two|three|1|2|3)|first.*second.*third|#\d)\b", t, re.I | re.S))),
    ("'Imagine\u2026'", lambda t: bool(re.search(r"\bimagine\b", t, re.I))),
    ("Story markers (once / one day / story)", lambda t: bool(re.search(r"\b(once|one day|story|years ago|back then)\b", t, re.I))),
    ("Many numerals (5+)", lambda t: len(re.findall(r"\d+", t)) >= 5),
    ("For example / for instance", lambda t: bool(re.search(r"\bfor (example|instance)\b", t, re.I))),
    ("Two or more questions inside", lambda t: t.count("?") >= 2),
    ("Show-and-tell (look at / watch / let me show)", lambda t: bool(re.search(r"\b(look at|watch|let me show|see this|check this out)\b", t, re.I))),
    ("Myth / lie / truth framing", lambda t: bool(re.search(r"\b(myth|lie|truth|fake|scam)\b", t, re.I))),
]
CTA_KINDS = [
    ("Follow / subscribe", r"\b(follow|subscribe)\b"), ("Like", r"\blike\b"), ("Comment", r"\bcomment\b"),
    ("Share / send", r"\b(share|send)\b"), ("Link / bio / description", r"\b(link|bio|description)\b"),
    ("Watch next / part 2 / full video", r"\b(part 2|next|full (video|episode)|watch)\b"),
]
STOP = set("the a an and or but of to in on at for with is are was were be been it this that these those i you he she we they my your our his her their me him them as by from so if then than not no yes do does did have has had will would can could should just very really also about into out up down over more most some any all one two what who how why when where which there here its it's i'm you're don't can't won't don't let's s t ll re ve d m".split())


def prep(res):
    V = res["videos"]
    for v in V:
        v["first"] = v["sentences"][0]["text"] if v["sentences"] else ""
        v["fw"] = words(v["first"])
        v["text"] = " ".join(s["text"] for s in v["sentences"])
        roles = [s["role"] for s in v["sentences"]]
        v["roles"] = roles
        shape = []
        for r in roles:
            if not shape or shape[-1] != r: shape.append(r)
        v["shape"] = " > ".join(x for x in shape if x)
        v["last_role"] = roles[-1] if roles else None
        v["first_role"] = roles[0] if roles else None
        v["n_hook"] = roles.count("hook"); v["n_setup"] = roles.count("setup")
        v["cta_flag"] = v["has_cta"] >= 0.7
        v["wps"] = words(v["text"]) / max(1, len(roles))
        v["like_rate"] = (v["likes"] / v["views"]) if v.get("likes") is not None and v["views"] else None
        lb = v.get("latin_frac", 1.0)
        v["lang_mix"] = "mostly Latin script (English / romanised)" if lb >= 0.8 else "mostly native script" if lb <= 0.2 else "mixed scripts (Hinglish / Tenglish style)"
        v["h"], v["y"] = half(v), year(v)
        v["title_key"] = " ".join(re.sub(r"(#\w+|\b(pt|part|ep|episode|day|vlog)\.?\s*#?\d+\b|\d+)", " ", (v["title"] or "").lower()).replace("'", "").split()[:3])
    V.sort(key=lambda v: -v["views"])
    return V


def cat_len(n): return "8 or fewer" if n <= 8 else "9\u201312" if n <= 12 else "13\u201316" if n <= 16 else "17\u201322" if n <= 22 else "23 or more"
def cat_dur(d): return None if d is None else "<30 s" if d < 30 else "30\u201345 s" if d < 45 else "45\u201360 s" if d < 60 else "60\u201375 s" if d < 75 else "75\u201390 s" if d < 90 else "90 s+"
def cat_fw(n): return "5 words or fewer" if n <= 5 else "6\u20139" if n <= 9 else "10\u201314" if n <= 14 else "15\u201320" if n <= 20 else "21+"
DUR_ORDER = ["<30 s", "30\u201345 s", "45\u201360 s", "60\u201375 s", "75\u201390 s", "90 s+"]
LEN_ORDER = ["8 or fewer", "9\u201312", "13\u201316", "17\u201322", "23 or more"]
FW_ORDER = ["5 words or fewer", "6\u20139", "10\u201314", "15\u201320", "21+"]


def feature_lifts(universe, getter, feats, min_n=8):
    rows = []
    for name, fn in feats:
        w = [v for v in universe if fn(getter(v))]; wo = [v for v in universe if not fn(getter(v))]
        lw, lo = med(lifts(w)), med(lifts(wo))
        if len(w) >= min_n and len(wo) >= min_n and lw is not None and lo:
            sw = stats(w)
            rows.append({"name": name, "n": len(w), "with": lw, "without": lo, "ratio": lw / lo if lo else None, "big": sw["big"], "flop": sw["flop"]})
    rows.sort(key=lambda r: -(r["ratio"] or 0))
    return rows


def feat_table(rows):
    return table(["Feature", "n", "Lift with", "Lift without", "Ratio", "Big-win %", "Flop %"],
                 [[r["name"], r["n"], f2(r["with"]), f2(r["without"]), f"x{r['ratio']:.2f}", pct(r["big"]), pct(r["flop"])] for r in rows])


# ---------------------------------------------------------------- series / formats
def detect_series(V, min_n):
    g = collections.defaultdict(list)
    for v in V:
        if v["title_key"] and len(v["title_key"].split()) >= 2: g[v["title_key"]].append(v)
    ser = [(k, sorted(x, key=lambda v: v["date"])) for k, x in g.items() if len(x) >= min_n]
    ser.sort(key=lambda kx: -len(kx[1]))
    return ser[:15]


def series_effect(V, name_vs):
    """Channel median views in the 90 days before vs after a series' first (and last) episode, for the creator's OTHER shorts."""
    ids = {v["id"] for v in name_vs}; d = lambda s: dt.date.fromisoformat(s).toordinal()
    first, last = d(name_vs[0]["date"]), d(name_vs[-1]["date"]); latest = max(d(v["date"]) for v in V)
    others = [v for v in V if v["id"] not in ids]
    win = lambda a, b: med([v["views"] for v in others if a <= d(v["date"]) < b])
    return {"first": name_vs[0]["date"], "last": name_vs[-1]["date"], "dropped": latest - last > 120,
            "before_add": win(first - 90, first), "after_add": win(first, first + 90),
            "before_drop": win(last - 90, last) if latest - last > 120 else None, "after_drop": win(last, last + 90) if latest - last > 120 else None}


# ---------------------------------------------------------------- charts
def savefig(path):
    plt.tight_layout(); plt.savefig(path, dpi=110); plt.savefig(path.with_suffix(".svg")); plt.close()


def make_charts(res, V, T, cd):
    cd.mkdir(exist_ok=True); n = {}
    D = lambda v: dt.date.fromisoformat(v["date"])
    halves = sorted({v["h"] for v in V})
    # 1 every short over time
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for s in STYLES:
        xs = [v for v in V if v["style"] == s]
        ax.scatter([D(v) for v in xs], [v["views"] for v in xs], s=9, c=COL[s], alpha=.7, label=f"{s} ({len(xs)})", linewidths=0)
    ax.plot([dt.date(int(h[:4]), 3 if h.endswith("1") else 9, 15) for h in halves], [med([v["views"] for v in V if v["h"] == h]) for h in halves], "k-", lw=2, label="median per half-year")
    if any(v.get("pre_view_change") is not None for v in V): ax.axvline(dt.date.fromisoformat(YT_CHANGE), color="grey", ls="--", lw=1)
    ax.set_yscale("log"); ax.set_ylabel("views (log)"); ax.legend(fontsize=7, ncol=3); ax.set_title("Every short: upload date vs views, coloured by Jev style")
    savefig(cd / "chart01_over_time.png")
    n[1] = table(["Half-year", "Shorts", "Median views"], [[h, len([v for v in V if v["h"] == h]), f0(med([v["views"] for v in V if v["h"] == h]))] for h in halves])
    # 2 distribution + concentration
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6)); ax[0].hist([math.log10(max(v["views"], 1)) for v in V], bins=30, color="#0072b2"); ax[0].set_xlabel("log10 views"); ax[0].set_title("Distribution")
    sv = sorted((v["views"] for v in V), reverse=True); cum = [sum(sv[:i + 1]) / sum(sv) for i in range(len(sv))]
    ax[1].plot([(i + 1) / len(sv) * 100 for i in range(len(sv))], [c * 100 for c in cum], color="#d55e00"); ax[1].set_xlabel("top x% of shorts"); ax[1].set_ylabel("% of all views"); ax[1].set_title("Concentration")
    savefig(cd / "chart02_distribution.png")
    n[2] = table(["Top share of shorts", "Share of all views"], [[f"{p}%", pct(sum(sv[:max(1, int(len(sv) * p / 100))]) / sum(sv))] for p in (1, 5, 10, 25, 50)])
    # 3 talking vs text/music
    fig, ax = plt.subplots(figsize=(8, 3.6)); rows = []
    for k, c in (("talking", "#0072b2"), ("text_music", "#d55e00"), ("in_between", "#999999")):
        pts = [(h, med([v["views"] for v in V if v["h"] == h and v["kind"] == k]), len([v for v in V if v["h"] == h and v["kind"] == k])) for h in halves]
        pts = [p for p in pts if p[2] >= 3]
        if pts: ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=c, label=k)
        rows += [[k, p[0], p[2], f0(p[1])] for p in pts]
    ax.set_yscale("log"); ax.legend(); ax.tick_params(axis="x", rotation=60); ax.set_title("Median views by format kind, half-year by half-year"); savefig(cd / "chart03_kinds.png")
    n[3] = table(["Kind", "Half-year", "n", "Median views"], rows)
    # 4 style and hook lift
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6)); rows = []
    for a, (lab, key, order) in zip(ax, (("style", "style", STYLES), ("hook", "hook", HOOKS))):
        its = by(T, lambda v: v[key], order); a.bar([k for k, _ in its], [med(lifts(g)) or 0 for _, g in its], color="#0072b2"); a.axhline(1, color="k", lw=.8); a.set_title(f"{lab}: median lift"); a.tick_params(axis="x", rotation=30)
        rows += [[lab, k, len(g), f2(med(lifts(g)))] for k, g in its]
    savefig(cd / "chart04_style_hook.png"); n[4] = table(["Type", "Value", "n", "Median lift"], rows)
    # 5 first-sentence length, duration, sentence count
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.4)); rows = []
    for a, (lab, key, order) in zip(ax, (("first-sentence words", lambda v: cat_fw(v["fw"]), FW_ORDER), ("duration", lambda v: cat_dur(v["duration"]), DUR_ORDER), ("sentences", lambda v: cat_len(v["n_sentences"]), LEN_ORDER))):
        its = by(T, key, order); a.bar(range(len(its)), [med(lifts(g)) or 0 for _, g in its], color="#009e73"); a.set_xticks(range(len(its))); a.set_xticklabels([k for k, _ in its], rotation=45, fontsize=7); a.axhline(1, color="k", lw=.8); a.set_title(lab, fontsize=9)
        rows += [[lab, k, len(g), f2(med(lifts(g)))] for k, g in its]
    savefig(cd / "chart05_lengths.png"); n[5] = table(["Cut", "Bucket", "n", "Median lift"], rows)
    # 6 how it ends
    its = by(T, lambda v: v["last_role"], ["hook", "setup", "body", "payoff", "cta"]); fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar([k for k, _ in its], [med(lifts(g)) or 0 for _, g in its], color="#cc79a7"); ax.axhline(1, color="k", lw=.8); ax.set_title("Median lift by role of the last sentence"); savefig(cd / "chart06_endings.png")
    n[6] = table(["Last-sentence role", "n", "Median lift", "Flop %"], [[k, len(g), f2(med(lifts(g))), pct(stats(g)["flop"])] for k, g in its])
    # 7 roles by position
    fig, ax = plt.subplots(figsize=(7, 3.6)); roles = ["hook", "setup", "body", "payoff", "cta"]; cnt = [collections.Counter() for _ in range(10)]
    for v in T:
        L = len(v["roles"])
        for i, r in enumerate(v["roles"]): cnt[min(9, int(i / L * 10))][r] += 1
    bottom = [0] * 10; rows = []
    for r, c in zip(roles, ["#d55e00", "#999999", "#0072b2", "#009e73", "#cc79a7"]):
        vals = [cnt[i][r] / max(1, sum(cnt[i].values())) for i in range(10)]; ax.bar(range(10), vals, bottom=bottom, color=c, label=r); bottom = [b + v for b, v in zip(bottom, vals)]; rows.append([r] + [pct(x) for x in vals])
    ax.legend(fontsize=7); ax.set_xlabel("position in script (decile)"); savefig(cd / "chart07_roles.png"); n[7] = table(["Role"] + [f"D{i+1}" for i in range(10)], rows)
    # 8 what the first sentence contains
    fr = feature_lifts(T, lambda v: v["first"], FEATURES, 5); fig, ax = plt.subplots(figsize=(8, 4.2))
    if fr: ax.barh([r["name"][:40] for r in fr][::-1], [r["ratio"] for r in fr][::-1], color="#0072b2"); ax.axvline(1, color="k", lw=.8); ax.set_title("First sentence: lift ratio with vs without")
    savefig(cd / "chart08_first_sentence.png"); n[8] = feat_table(fr) if fr else "(too few shorts)\n"
    # 9 formats over time
    ser = detect_series(V, 5)[:6]; fig, ax = plt.subplots(figsize=(8, 3.6)); rows = []
    for k, vs in ser:
        ax.plot(halves, [len([v for v in vs if v["h"] == h]) for h in halves], "o-", label=k[:28]); rows.append([k, len(vs), vs[0]["date"], vs[-1]["date"], f2(med(lifts(vs)))])
    if ser: ax.legend(fontsize=7)
    ax.tick_params(axis="x", rotation=60); ax.set_title("Recurring formats (by title pattern): shorts per half-year"); savefig(cd / "chart09_formats.png")
    n[9] = table(["Title pattern", "n", "First", "Last", "Median lift"], rows) if rows else "(no recurring title pattern with 5+ shorts)\n"
    # 10 top 40
    top = V[:40]; fig, ax = plt.subplots(figsize=(8, 8)); ax.barh([f"{v['title'][:38]}" for v in top][::-1], [v["views"] for v in top][::-1], color=[COL[v["style"]] for v in top][::-1]); ax.set_xscale("log"); ax.tick_params(axis="y", labelsize=6)
    savefig(cd / "chart10_top40.png"); n[10] = table(["#", "ID", "Date", "Views", "Style/hook", "Title"], [[i + 1, v["id"], v["date"], f0(v["views"]), f"{v['style']}/{v['hook']}", v["title"][:60]] for i, v in enumerate(top)])
    # 11 like rate by reach decile + concentration by year
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4)); sv = sorted(V, key=lambda v: v["views"]); k = max(1, len(sv) // 10); rows = []
    dec = [med([v["like_rate"] for v in sv[i * k:(i + 1) * k] if v["like_rate"] is not None]) for i in range(10)]
    ax[0].bar(range(10), [(d or 0) * 100 for d in dec], color="#d55e00"); ax[0].set_title("Like rate (%) by views decile")
    yrs = sorted({v["y"] for v in V}); conc = []
    for y in yrs:
        vv = sorted((v["views"] for v in V if v["y"] == y), reverse=True); conc.append(sum(vv[:max(1, int(len(vv) * .1))]) / sum(vv)); rows.append([y, len(vv), pct(conc[-1])])
    ax[1].bar(yrs, [c * 100 for c in conc], color="#0072b2"); ax[1].set_title("Top-10% share of the year's views (%)"); savefig(cd / "chart11_like_rate.png")
    n[11] = table(["Year", "Shorts", "Top-10% share"], rows) + "\n" + table(["Views decile", "Median like rate"], [[i + 1, pct(d)] for i, d in enumerate(dec)])
    # 12 style and hook mix by year
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4)); rows = []
    for a, (lab, key, order) in zip(ax, (("style", "style", STYLES), ("hook", "hook", HOOKS))):
        bottom = [0] * len(yrs)
        for o in order:
            vals = [len([v for v in V if v["y"] == y and v[key] == o]) / max(1, len([v for v in V if v["y"] == y])) for y in yrs]; a.bar(yrs, vals, bottom=bottom, label=o); bottom = [b + x for b, x in zip(bottom, vals)]; rows.append([lab, o] + [pct(x) for x in vals])
        a.legend(fontsize=6); a.set_title(f"{lab} mix by year")
    savefig(cd / "chart12_mix_by_year.png"); n[12] = table(["Type", "Value"] + yrs, rows)
    # 13 duration vs lift
    fig, ax = plt.subplots(figsize=(7, 3.8)); pts = [(v["duration"], v["lift"]) for v in T if v["duration"] and v["lift"]]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=8, alpha=.5); ax.set_yscale("log"); ax.axhline(1, color="k", lw=.8); ax.set_xlabel("duration (s)"); ax.set_ylabel("lift"); savefig(cd / "chart13_duration_lift.png")
    n[13] = table(["Duration", "n", "Median lift", "Big-win %", "Flop %"], [[k, len(g), f2(med(lifts(g))), pct(stats(g)["big"]), pct(stats(g)["flop"])] for k, g in by(T, lambda v: cat_dur(v["duration"]), DUR_ORDER)])
    # 14 subjects and script elements
    er = feature_lifts(T, lambda v: v["text"], ELEMENTS, 5); wr = word_lifts(T); fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    if er: ax[0].barh([r["name"][:34] for r in er][::-1], [r["ratio"] for r in er][::-1], color="#009e73"); ax[0].axvline(1, color="k", lw=.8); ax[0].set_title("Script elements: lift ratio", fontsize=9)
    if wr: sel = wr[:8] + wr[-8:]; ax[1].barh([w["word"] for w in sel][::-1], [w["with"] for w in sel][::-1], color="#0072b2"); ax[1].axvline(1, color="k", lw=.8); ax[1].set_title("Words in script: median lift of shorts containing", fontsize=9)
    savefig(cd / "chart14_subjects.png"); n[14] = (feat_table(er) if er else "") + "\n" + (table(["Word", "n", "Lift with"], [[w["word"], w["n"], f2(w["with"])] for w in wr]) if wr else "")
    # 15 language mix
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6)); mixes = sorted({v["lang_mix"] for v in V}); rows = []
    bottom = [0] * len(halves)
    for m in mixes:
        vals = [len([v for v in V if v["h"] == h and v["lang_mix"] == m]) / max(1, len([v for v in V if v["h"] == h])) for h in halves]; ax[0].bar(halves, vals, bottom=bottom, label=m[:28]); bottom = [b + x for b, x in zip(bottom, vals)]
    ax[0].legend(fontsize=6); ax[0].tick_params(axis="x", rotation=60); ax[0].set_title("Language-script mix over time", fontsize=9)
    its = by(T, lambda v: v["lang_mix"]); ax[1].bar([k[:18] for k, _ in its], [med(lifts(g)) or 0 for _, g in its], color="#cc79a7"); ax[1].axhline(1, color="k", lw=.8); ax[1].set_title("Median lift by language mix", fontsize=9); ax[1].tick_params(axis="x", rotation=20, labelsize=7)
    savefig(cd / "chart15_language.png"); n[15] = table(STAT_H, [stat_row(k, g) for k, g in its])
    # 16 series lift
    ser = detect_series(V, 5)[:10]; fig, ax = plt.subplots(figsize=(8, 3.6))
    if ser: ax.barh([k[:28] for k, _ in ser][::-1], [med(lifts(vs)) or 0 for _, vs in ser][::-1], color="#d55e00"); ax.axvline(1, color="k", lw=.8)
    ax.set_title("Median lift by recurring title pattern"); savefig(cd / "chart16_series_lift.png"); n[16] = table(STAT_H, [stat_row(k, vs) for k, vs in ser]) if ser else "(none)\n"
    return n


def word_lifts(T, min_n=15):
    cnt = collections.defaultdict(list)
    for v in T:
        for w in set(re.findall(r"[a-z][a-z']{3,}", (v["title"] + " " + v["text"]).lower())):
            if w not in STOP: cnt[w].append(v)
    rows = [{"word": w, "n": len(vs), "with": med(lifts(vs))} for w, vs in cnt.items() if len(vs) >= min_n and med(lifts(vs)) is not None]
    rows.sort(key=lambda r: -r["with"]); return rows[:25] + rows[-25:] if len(rows) > 50 else rows


# ---------------------------------------------------------------- the document
CHART_TITLES = ["Every short over time", "Distribution and concentration of views", "Talking vs text/music shorts, half-year by half-year", "Style and hook, era-adjusted",
    "First-sentence length, duration and sentence count", "How the short ends", "Sentence roles by position in the script", "What the first sentence contains",
    "Recurring formats over time", "Top 40 by raw views", "Like rate by reach, and concentration by year", "Style and hook mix by year", "Duration vs lift for every talking short",
    "Subjects and script elements", "Language mix (new)", "Series lift (new)"]


def build(folder, pdf=True):
    d = OUT / folder; res = json.loads((d / "shorts_full.json").read_text())
    ed = json.loads((d / "editorial.json").read_text()) if (d / "editorial.json").exists() else {}
    V = prep(res); name = res["creator"]; plat = "YouTube Shorts" if res["platform"] == "youtube" else "Instagram Reels"; unit = "Short" if res["platform"] == "youtube" else "reel"
    F = res.get("funnel", {}); meta = res.get("creator_meta", {})
    T = [v for v in V if v["kind"] == "talking"]; texty = [v for v in V if v["kind"] == "text_music"]
    Tl = [v for v in T if v["lift"] is not None]
    dmin, dmax = min(v["date"] for v in V), max(v["date"] for v in V); split = sorted(v["date"] for v in V)[len(V) // 2]
    views = sorted((v["views"] for v in V), reverse=True); tot = sum(views); share = lambda p: sum(views[:max(1, int(len(views) * p))]) / tot
    cd = d / "charts"; chart_nums = make_charts(res, V, T if T else V, cd)
    U = T if len(T) >= 30 else V  # analysis universe
    unit_note = "talking shorts (5+ sentences)" if U is T else "all shorts (too few talking shorts to split)"
    md = []; A = md.append
    pre = [v for v in V if v.get("pre_view_change")]; post = [v for v in V if v.get("pre_view_change") is False]
    # ---- findings
    F_ = []
    F_.append(f"**Views are a lottery with a fat tail.** The median {unit} got {short(med(views))} views but the mean was {short(mean(views))}. The top 10% delivered {pct(share(.1))} of all views and the top 1% delivered {pct(share(.01))}. Plan for a hit rate, not a typical {unit}. {tag(len(V))}")
    hs = [(h, med([v["views"] for v in V if v["h"] == h]), len([v for v in V if v["h"] == h])) for h in sorted({v["h"] for v in V})]; hs = [x for x in hs if x[2] >= 5]
    if len(hs) >= 3 and max(hs, key=lambda x: x[1]) is not hs[-1]:
        pk, last = max(hs, key=lambda x: x[1]), hs[-1]
        F_.append(f"**Reach over time.** The best half-year was {pk[0]} (median {short(pk[1])}); the latest, {last[0]}, is {short(last[1])} ({last[1] / pk[1]:.2f}x the peak). {tag(len(V))}")
    def best_worst(items, label, min_n=20):
        its = [(k, g) for k, g in items if len(lifts(g)) >= min_n]
        if len(its) >= 2:
            b, w = max(its, key=lambda kg: med(lifts(kg[1]))), min(its, key=lambda kg: med(lifts(kg[1])))
            return f"**Best {label}: {b[0]}** (median lift {f2(med(lifts(b[1])))}, n={len(b[1])}, {pct(stats(b[1])['big'])} big wins). Weakest: {w[0]} ({f2(med(lifts(w[1])))}, n={len(w[1])}, {pct(stats(w[1])['flop'])} flops). {tag(len(b[1]), consistent(b[1], U, split), med(lifts(b[1])) or 1)}"
    for label, key in (("style", "style"), ("hook", "hook")):
        t = best_worst(by(U, lambda v: v[key]), label)
        if t: F_.append(t)
    sh = [(k, g) for k, g in by(U, lambda v: f"{v['style']} + {v['hook']}") if len(lifts(g)) >= 15]
    if sh: k, g = max(sh, key=lambda kg: med(lifts(kg[1]))); F_.append(f"**Best style + hook pairing: {k}** (median lift {f2(med(lifts(g)))}, n={len(g)}, {pct(stats(g)['big'])} big wins). {tag(len(g), consistent(g, U, split), med(lifts(g)) or 1)}")
    c1, c0 = [v for v in U if v["cta_flag"]], [v for v in U if not v["cta_flag"]]
    if len(lifts(c1)) >= 10 and len(lifts(c0)) >= 10: F_.append(f"**Calls to action: {'help' if med(lifts(c1)) > med(lifts(c0)) else 'do not help'}.** Median lift {f2(med(lifts(c1)))} with a CTA (n={len(c1)}) vs {f2(med(lifts(c0)))} without (n={len(c0)}); flop rate {pct(stats(c1)['flop'])} vs {pct(stats(c0)['flop'])}. {tag(min(len(c1), len(c0)), True, (med(lifts(c1)) or 1) / (med(lifts(c0)) or 1))}")
    lb = [(k, g) for k, g in by(U, lambda v: cat_len(v["n_sentences"]), LEN_ORDER) if len(lifts(g)) >= 20]
    if len(lb) >= 2: b = max(lb, key=lambda kg: med(lifts(kg[1]))); F_.append(f"**Length sweet spot: {b[0]} sentences** (lift {f2(med(lifts(b[1])))}, n={len(b[1])}). {tag(len(b[1]), consistent(b[1], U, split), med(lifts(b[1])) or 1)}")
    fb = [(k, g) for k, g in by(U, lambda v: cat_fw(v["fw"]), FW_ORDER) if len(lifts(g)) >= 20]
    if len(fb) >= 2: b = max(fb, key=lambda kg: med(lifts(kg[1]))); F_.append(f"**First sentence length: {b[0]} {'' if 'word' in b[0] else 'words '}works best** (lift {f2(med(lifts(b[1])))}, n={len(b[1])}). {tag(len(b[1]), consistent(b[1], U, split), med(lifts(b[1])) or 1)}")
    fr = feature_lifts(U, lambda v: v["first"], FEATURES, 15)
    if fr: F_.append(f"**Strongest first-sentence feature: {fr[0]['name']}** (lift {f2(fr[0]['with'])} vs {f2(fr[0]['without'])}, n={fr[0]['n']}); weakest: {fr[-1]['name']} (x{fr[-1]['ratio']:.2f}, n={fr[-1]['n']}). {tag(fr[0]['n'], True, fr[0]['ratio'])}")
    lg = [(k, g) for k, g in by(U, lambda v: v["lang_mix"]) if len(lifts(g)) >= 15]
    if len(lg) >= 2: b, w = max(lg, key=lambda kg: med(lifts(kg[1]))), min(lg, key=lambda kg: med(lifts(kg[1]))); F_.append(f"**Language mix matters: {b[0]}** has median lift {f2(med(lifts(b[1])))} (n={len(b[1])}) vs {f2(med(lifts(w[1])))} for {w[0]} (n={len(w[1])}). Script-based heuristic, not a language label. {tag(len(w[1]))}")
    ser = detect_series(V, 6)
    if ser: sk, sv_ = max(ser, key=lambda kv: med(lifts(kv[1])) or 0); F_.append(f"**Most productive recurring format: \"{sk}\u2026\"** ({len(sv_)} {unit}s, median lift {f2(med(lifts(sv_)))}, {pct(stats(sv_)['big'])} big wins). {tag(len(sv_))}")
    if pre and post and len(pre) >= 20 and len(post) >= 20: F_.append(f"**View-definition change (31 Mar 2025).** Median views before: {short(med([v['views'] for v in pre]))} (n={len(pre)}); after: {short(med([v['views'] for v in post]))} (n={len(post)}). YouTube counts every play from that date, so raw views across it are not like-for-like; lift is computed within a 45-day window to soften this. [Moderate]")
    for extra in ed.get("findings_extra", []): F_.append(extra)
    # ---- header
    A(f"# {name}: {plat} Content Lab Playbook\n")
    A(f"**Source:** every {unit} on `{meta.get('url', '')}` ({F.get('listed', '?')} listed, capped at the most recent {res['cap']}; {len(V)} analysed), {dmin} to {dmax}. Each {unit} was transcribed, translated to English where needed, broken down by Jev (TypeSafe's decision model) and compared against views. **Built:** {F.get('built', dt.date.today().isoformat())}. **Use:** a knowledge base for planning, scripting and diagnosing short-form video on any topic. **This file is self-contained.** Parts II to VI hold everything else, so the `data/` folder is not needed to use it.\n")
    A(table(["Part", "What it contains"], [["I (this part, up to Appendix D)", "The playbook: findings, hook and script formulas, what failed, what to test next, top-25 list, example scripts"], ["II", "16 charts, each followed by its numbers"], ["III", f"Register of every analysed {unit} (ID, date, views, likes, duration, Jev answers, lift, headline)"], ["IV", "Every statistical table, unedited"], ["V", "The full script of each analysed short with Jev's role label on every sentence, caption, original-language transcript and Jev probabilities"], ["VI", "File inventory and what deleting `data/` would lose"]]))
    A("Readable playbook = Part I. Parts II\u2013VI are reference material, so search them rather than reading top to bottom. The machine-readable twin is `shorts_full.json`.\n")
    A("How to read the confidence tags:\n\n- **[Strong]**: large sample (100+), clear effect, same direction in both halves of the timeline.\n- **[Moderate]**: decent sample (20+) or consistent direction, but the effect is small or partly confounded.\n- **[Anecdotal]**: fewer than about 20 shorts. A pattern worth testing, not a rule.\n")
    A("\n---\n\n## 0. The 20-second version\n")
    for i, t in enumerate(F_[:10], 1): A(f"{i}. {t}")
    A("")
    # ---- 1
    A("\n---\n\n## 1. What was analysed and how\n\n### 1.1 The funnel\n")
    A(table(["Step", "Count", "Note"], [[f"{unit}s listed", F.get("listed", "?"), "yt-dlp `--flat-playlist` on the Shorts tab" if res["platform"] == "youtube" else "Apify reel scraper"], ["Kept (most recent)", min(F.get("listed") or res["cap"], res["cap"]), f"cap {res['cap']}"], ["Downloaded (info + thumbnail)", F.get("downloaded", "?"), f"failures by stage: {F.get('failures_by_stage') or 'none logged'}"], ["With audio", F.get("with_audio", "?"), ""], ["Transcribed", F.get("transcribed", "?"), f"model: {', '.join(F.get('stt_models', []))}"], ["English text ready", F.get("english_ready", "?"), f"translation model: {F.get('translation_model')} (only non-English transcripts translated)"], ["Broken down by Jev", F.get("labelled", "?"), f"{F.get('jev_tokens', 0):,} input tokens, ${F.get('jev_cost_usd', 0)}"]]))
    nt = len([v for v in V if v["labelled_on_translation"]]); lc = res.get("low_confidence_transcripts", 0)
    A(f"- **Date range:** {dmin} to {dmax}. **Views** are {plat} counts at scrape time.\n- **Transcription:** `whisper-large-v3` on Groq for every video (model recorded per video in `shorts_full.json`). Original-language text is kept; {nt} of {len(V)} were translated to English and Jev labelled the English text. Hinglish, Tenglish and mixed-script transcripts are noisy.\n- **Low-confidence transcripts:** {lc} flagged (mean segment log-probability below -0.8). They are kept but treat their labels with extra care.\n- **Jev cost for the whole run:** ${F.get('jev_cost_usd', 0)} ({F.get('jev_tokens', 0):,} input tokens).\n")
    A("### 1.2 What Jev was asked, per short\n\nJev (`jev-latest`) got the title, the script split into numbered sentences, and the thumbnail (resized to at most 960 px tall). It answered:\n\n- **Style (choice):** storytelling (a story with a lesson at the end); tactical (a how-to, steps, framework or tactic); opinion (a hot take or contrarian view); qa (answers a question someone asked); mindset (motivation or discipline advice).\n- **Hook (choice), how the first sentence hooks the viewer:** question; claim (bold or surprising); story (drops you into a story); callout (calls out a kind of person); number (leads with a number or result).\n- **has_cta (yes/no probability):** does the script end with a call to action? Counted as a CTA at probability 0.7 or more.\n- **Sentence role (choice, one question per sentence):** hook; setup; body; payoff; cta.\n")
    A("### 1.3 The key analytic move: \"lift\"\n\nRaw views are misleading because channels grow, shrink and change format. So findings use **lift**:\n\n> **lift = a short's views \u00f7 the median views of the creator's other shorts posted within \u00b145 days.**\n\n- A lift of 1.0 means \"about as well as the channel normally did that month\".\n- A **big win** is lift 3.0 or more; a **flop** is lift 0.5 or less.\n- Shorts with fewer than 3 neighbours in the window have no lift and are left out of lift tables.\n")
    A(f"### 1.4 The three kinds of short (and why they are separated)\n")
    A(table(["Group", "n", "Median views", "What it is"], [["Talking (5+ sentences)", len(T), f0(med([v["views"] for v in T])), "Scripted or spoken. **The main analysis universe for script and hook findings**" if U is T else "Scripted or spoken"], ["In between (3\u20134 sentences)", len([v for v in V if v["kind"] == "in_between"]), f0(med([v["views"] for v in V if v["kind"] == "in_between"])), "Too small to study alone"], ["Text/music (2 or fewer sentences)", len(texty), f0(med([v["views"] for v in texty])), "Mostly on-screen text or music; the caption does the work"]]))
    A(f"Findings below use {unit_note} and **lift**, not raw views.\n")
    A("### 1.5 Caveats, stated plainly\n\n- **Correlation, not experiment.** Nothing here proves a hook or structure causes views. Topic, timing, thumbnail, audio and the algorithm all vary.\n- **Small groups.** Many patterns rest on 8\u201320 shorts. Check the tag.\n- **Medians near 1.0 by construction.** Lift is relative; differences of 0.05\u20130.15 are noise-sized.\n- **Jev labels are judgments, not truth.** In dialogue-style or interview shorts, Jev tags lines as hook/setup/body line by line.\n- **Translation.** For non-English videos the labels come from the English translation, which can flatten wordplay and tone.\n")
    if pre and post: A(f"- **View-definition change.** {plat} counts every play from {YT_CHANGE}. {len(pre)} shorts were posted before and {len(post)} after; compare raw views across that date with care.\n")
    A("- **Recency.** The newest shorts have had less time to collect views.\n- **Duplicate-looking opens.** Some shorts share first sentences, so they are not independent samples.\n")
    # ---- 2
    A("\n---\n\n## 2. The shape of the distribution\n")
    A(table(["Measure", "Value"], [[f"{unit}s analysed", len(V)], ["Minimum / median / mean / maximum views", f"{f0(min(views))} / **{f0(med(views))}** / **{f0(mean(views))}** / {f0(max(views))}"], ["25th / 75th percentile (approx.)", f"{f0(views[int(len(views) * .75)])} / {f0(views[int(len(views) * .25)])}"], ["90th / 99th percentile (approx.)", f"{f0(views[int(len(views) * .1)])} / {f0(views[int(len(views) * .01)])}"], ["Share of all views from the top 10%", pct(share(.1))], [f"Share from the top 1% ({max(1, int(len(views) * .01))} {unit}s)", pct(share(.01))], ["Total views", f0(tot)]]))
    A("### 2.1 By year\n")
    yrs = sorted({v["y"] for v in V})
    A(table(["Year", "n", "Median views", "Total views", "Share of all", "Median duration", "Median sentences", "Best"], [[y, len(g), f0(med([v["views"] for v in g])), short(sum(v["views"] for v in g)), pct(sum(v["views"] for v in g) / tot), f"{f0(med([v['duration'] for v in g]))} s", f0(med([v["n_sentences"] for v in g])), short(max(v["views"] for v in g))] for y in yrs for g in [[v for v in V if v["y"] == y]]]))
    A("### 2.2 Concentration by year\n")
    A("Share of a year's views taken by that year's top 10%: " + ", ".join(f"**{y} {pct(sum(sorted((v['views'] for v in V if v['y'] == y), reverse=True)[:max(1, int(len([v for v in V if v['y'] == y]) * .1))]) / sum(v['views'] for v in V if v['y'] == y))}**" for y in yrs) + ".\n")
    A(f"### 2.3 Half-year by half-year ({'talking shorts' if T else 'all shorts'})\n")
    base = T or V
    A(table(["Period", "n", "Median views", "Median lift", "Big-win %", "Flop %", "Median duration"], [[h, len(g), f0(med([v["views"] for v in g])), f2(med(lifts(g))), pct(stats(g)["big"]), pct(stats(g)["flop"]), f"{f0(med([v['duration'] for v in g]))} s"] for h in sorted({v["h"] for v in base}) for g in [[v for v in base if v["h"] == h]] if len(g) >= 3]))
    A("### 2.4 Likes per view fall as reach rises\n")
    lr = sorted([v for v in V if v["like_rate"] is not None], key=lambda v: v["views"])
    if len(lr) >= 20: k = max(1, len(lr) // 10); A(f"Median likes \u00f7 views is **{pct(med([v['like_rate'] for v in lr[:k]]))}** in the lowest-view tenth and **{pct(med([v['like_rate'] for v in lr[-k:]]))}** in the highest tenth. Do not use the like rate as a quality signal for reach.\n")
    # ---- 3
    A("\n---\n\n## 3. Styles: what the data says\n\n### 3.1 The raw ranking, and why not to trust it\n")
    A(table(["Style", "n", "Median views", "Mean views", "Flop-rate (bottom quartile)"], [[k, len(g), f0(med([v["views"] for v in g])), f0(mean([v["views"] for v in g])), pct(sum(v["views"] <= views[int(len(views) * .75)] for v in g) / len(g))] for k, g in sorted(by(V, lambda v: v["style"]), key=lambda kg: -med([v["views"] for v in kg[1]]))]))
    A("Raw ranking is confounded by when each style was used and by audience growth or decline.\n")
    A(f"### 3.2 The fair ranking: {unit_note}, lift vs neighbours\n")
    t, items = group_table(U, lambda v: v["style"]); A(t)
    if items: b = items[0]; A(f"**What this means {tag(len(b[1]), consistent(b[1], U, split), med(lifts(b[1])) or 1)}:** {b[0]} has the best median lift ({f2(med(lifts(b[1])))}); compare the mean lift column: a high mean with a low median means a few monsters, not a reliable style.\n")
    A(f"### 3.3 Style \u00d7 hook combinations ({unit_note}; n \u2265 {MIN_GROUP})\n")
    t, items = group_table(U, lambda v: f"{v['style']} + {v['hook']}", min_n=MIN_GROUP); A(t)
    A("### 3.4 Style and hook before and after the 31 Mar 2025 view-definition change\n" if pre and post else "")
    if pre and post:
        rows = []
        for key in ("style", "hook"):
            for k, g in by(U, lambda v: v[key], STYLES if key == "style" else HOOKS):
                a_, b_ = [v for v in g if v.get("pre_view_change")], [v for v in g if v.get("pre_view_change") is False]
                if len(lifts(a_)) >= 8 and len(lifts(b_)) >= 8: rows.append([key, k, len(a_), f2(med(lifts(a_))), len(b_), f2(med(lifts(b_)))])
        A(table(["Type", "Value", "n before", "Lift before", "n after", "Lift after"], rows) if rows else "Too few shorts on both sides of the date for a before/after cut.\n")
    # ---- 4 hooks
    A("\n---\n\n## 4. Hooks: the first sentence\n\n### 4.1 Jev's five hook types\n\n**Raw (era-confounded):**\n")
    A(table(["Hook", "n", "Median views"], [[k, len(g), f0(med([v["views"] for v in g]))] for k, g in sorted(by(V, lambda v: v["hook"]), key=lambda kg: -med([v["views"] for v in kg[1]]))]))
    A(f"**Fair ({unit_note}, lift):**\n"); t, items = group_table(U, lambda v: v["hook"]); A(t)
    A("### 4.2 Hook anatomy: what the first sentence looks like\n\nMedian lift of shorts **with** a feature in the first sentence vs **without**, sorted by ratio. Features with fewer than 8 on either side are omitted.\n")
    fr = feature_lifts(U, lambda v: v["first"], FEATURES, 8); A(feat_table(fr) if fr else "Too few shorts for feature cuts.\n")
    if fr:
        A("**Takeaways:**\n")
        for r in fr[:3]: A(f"- {tag(r['n'], True, r['ratio'])} **{r['name']}** helps (x{r['ratio']:.2f}, n={r['n']}).")
        for r in fr[-3:]: A(f"- {tag(r['n'], True, r['ratio'])} **{r['name']}** hurts (x{r['ratio']:.2f}, n={r['n']}).")
        A("")
    A("### 4.3 First-sentence length\n"); t, _ = group_table(U, lambda v: cat_fw(v["fw"]), FW_ORDER, sort_lift=False); A(t)
    A("### 4.4 Hook swipe file, by Jev hook type (best and worst real first sentences)\n\nViews in parentheses. Best and worst are by lift, so a hook is judged against its own period.\n")
    for h in HOOKS:
        g = sorted([v for v in U if v["hook"] == h and v["lift"] is not None], key=lambda v: -v["lift"])
        if len(g) < 4: continue
        A(f"**{h.capitalize()}**\n"); A("- Best: " + " \u00b7 ".join(f"\u201c{v['first'][:140]}\u201d ({short(v['views'])}, {v['lift']:.1f}x)" for v in g[:6])); A("- Worst: " + " \u00b7 ".join(f"\u201c{v['first'][:140]}\u201d ({short(v['views'])}, {v['lift']:.2f}x)" for v in g[-4:]) + "\n")
    # ---- 5 structure
    A("\n---\n\n## 5. Structure: what a winning script is made of\n\n### 5.1 Role mix (Jev's per-sentence labels, all analysed)\n")
    rc = collections.Counter(r for v in V for r in v["roles"]); tr = sum(rc.values())
    A("Share of all sentences: " + " \u00b7 ".join(f"{r} {rc[r] / tr * 100:.1f}%" for r in ["body", "setup", "hook", "cta", "payoff"] if r in rc) + ".\n")
    A(f"### 5.2 Length and pacing ({unit_note})\n"); t, _ = group_table(U, lambda v: cat_dur(v["duration"]), DUR_ORDER, sort_lift=False); A(t); t, _ = group_table(U, lambda v: cat_len(v["n_sentences"]), LEN_ORDER, sort_lift=False); A(t)
    sh_, lg_ = [v for v in U if v["wps"] <= 11 and v["lift"] is not None], [v for v in U if v["wps"] >= 18 and v["lift"] is not None]
    if len(sh_) >= 8 and len(lg_) >= 8: A(f"- **Short sentences:** shorts averaging 11 words or fewer per sentence had {pct(stats(sh_)['big'])} big wins (n={len(sh_)}) vs {pct(stats(lg_)['big'])} for those averaging 18 or more (n={len(lg_)}).\n")
    A("### 5.3 Openings: hook first\n"); t, _ = group_table(U, lambda v: v["first_role"], ["hook", "setup", "body", "payoff", "cta"]); A(t)
    t, _ = group_table(U, lambda v: str(min(3, v["n_hook"])) + ("+" if v["n_hook"] >= 3 else ""), ["0", "1", "2", "3+"]); A("Hook-role sentences in the script (re-hooks):\n\n" + t)
    A("### 5.4 Endings: the CTA question\n"); t, _ = group_table(U, lambda v: v["last_role"], ["hook", "setup", "body", "payoff", "cta"]); A(t)
    t, _ = group_table(U, lambda v: "CTA (p\u22650.7)" if v["cta_flag"] else "No CTA", ["No CTA", "CTA (p\u22650.7)"]); A(t)
    def cta_kind(v):
        last = " ".join(s["text"] for s in v["sentences"][-2:]).lower()
        for k, rx in CTA_KINDS:
            if re.search(rx, last): return k
        return "a question" if "?" in last else None
    t, _ = group_table(U, cta_kind, min_n=5); A("What the last two sentences ask:\n\n" + t)
    A(f"### 5.5 Role \"shapes\" ({unit_note}; n \u2265 {MIN_GROUP})\n"); t, _ = group_table(U, lambda v: v["shape"] or None, min_n=MIN_GROUP); A(t if _ else "No shape appears 8+ times.\n")
    A("### 5.6 Whole-script elements that correlate with wins or losses\n\n"); er = feature_lifts(U, lambda v: v["text"], ELEMENTS, 8); A(feat_table(er) if er else "Too few shorts for element cuts.\n")
    # ---- 6 families
    A("\n---\n\n## 6. Content families that worked, with annotated scripts\n")
    A(ed.get("families", "_Editorial notes pending: the families and \"why it worked\" annotations are written after reading this creator's numbers (see `editorial.json`)._\n"))
    A("### 6.A Auto-detected candidates (recurring title or opening patterns)\n")
    fam = collections.defaultdict(list)
    for v in V: fam[" ".join(re.findall(r"[a-z']+", v["first"].lower())[:3])].append(v)
    cand = sorted([(k, g) for k, g in fam.items() if len(g) >= 5 and len(lifts(g)) >= 5 and k], key=lambda kg: -(med(lifts(kg[1])) or 0))[:8]
    A(table(["Opening words", "n", "Median views", "Median lift", "Big-win %", "Flop %", "Best examples"], [[f"\u201c{k}\u2026\u201d", len(g), f0(med([v['views'] for v in g])), f2(med(lifts(g))), pct(stats(g)["big"]), pct(stats(g)["flop"]), " ".join(f"[{short(v['views'])}]({link(v)})" for v in sorted(g, key=lambda v: -v['views'])[:3])] for k, g in cand]) if cand else "No opening phrase repeats 5+ times.\n")
    # ---- 7 failed
    A("\n---\n\n## 7. What failed, and why it plausibly failed\n\n### 7.1 The lowest results by lift\n")
    lo = sorted([v for v in U if v["lift"] is not None], key=lambda v: v["lift"])[:15]
    A(table(["Date", "Views", "Lift", "Style/hook", "First sentence"], [[v["date"], short(v["views"]), f"{v['lift']:.2f}", f"{v['style']}/{v['hook']}", f"\u201c{v['first'][:110]}\u201d"] for v in lo]))
    A(ed.get("failed", "_Editorial notes pending: the reasons these failed are written after reading the scripts._\n"))
    A("### 7.3 Checklist of anti-patterns (from features with ratio below 0.85, n \u2265 8)\n")
    anti = [r for r in (fr + er) if r["ratio"] <= .85]
    A("\n".join(f"{i}. {r['name']} (x{r['ratio']:.2f}, n={r['n']}, {pct(r['flop'])} flops)" for i, r in enumerate(anti, 1)) + "\n" if anti else "No feature reached the threshold.\n")
    # ---- 8 captions
    A("\n---\n\n## 8. Captions and text\n\nCaption features (" + unit_note + "; lift with vs without):\n")
    capf = [("Short caption (under 80 characters)", lambda c: len(c or "") < 80), ("Long caption (over 500 characters)", lambda c: len(c or "") > 500), ("Has hashtags", lambda c: "#" in (c or "")), ("Has emoji", lambda c: bool(re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", c or ""))), ("Has a question mark", lambda c: "?" in (c or "")), ("Has an @mention", lambda c: "@" in (c or "")), ("Says follow / subscribe", lambda c: bool(re.search(r"\b(follow|subscribe)\b", c or "", re.I))), ("Says comment", lambda c: bool(re.search(r"\bcomment\b", c or "", re.I))), ("Says link / bio", lambda c: bool(re.search(r"\b(link|bio)\b", c or "", re.I)))]
    cr = feature_lifts(U, lambda v: v.get("caption"), capf, 8); A(feat_table(cr) if cr else "Too few shorts.\n")
    # ---- 9 topics
    A("\n---\n\n## 9. Topics and subjects\n\nWords in the title or script, median lift of shorts containing them (n \u2265 15). Topic words are confounded with period and format; treat as hints.\n")
    wr = word_lifts(U); A(table(["Word", "n", "Lift with"], [[w["word"], w["n"], f2(w["with"])] for w in wr]) if wr else "Too few shorts for word-level cuts.\n")
    # ---- 10 language
    A("\n---\n\n## 10. Language analysis (new)\n\nPerformance by language mix. Mix is a heuristic from the share of native-script letters in the original transcript (Whisper's language label is shown beside it). It cannot separate Hinglish from Hindi written in Latin script.\n")
    t, items = group_table(U, lambda v: v["lang_mix"]); A(t)
    t, _ = group_table(U, lambda v: v.get("language"), min_n=5); A("By Whisper's detected language:\n\n" + t)
    mix_h = {h: collections.Counter(v["lang_mix"] for v in V if v["h"] == h) for h in sorted({v["h"] for v in V})}
    A("Language-mix share over time:\n\n" + table(["Half-year"] + sorted({v["lang_mix"] for v in V}), [[h] + [pct(c[m] / max(1, sum(c.values()))) for m in sorted({v["lang_mix"] for v in V})] for h, c in mix_h.items()]))
    A(ed.get("language", "_Editorial notes pending: any switch in language over time and what it did to reach._\n"))
    # ---- 11 formats and series
    A("\n---\n\n## 11. Format and series analysis (new)\n\nRecurring formats are detected from repeated title patterns (first three words with numbers and hashtags removed; 6+ shorts). For each: its lift, and what happened to the channel's **other** shorts' median views in the 90 days before vs after the format first appeared (and, if it stopped, before vs after its last episode). Correlation only: the format may have been added because things were already changing.\n")
    ser = detect_series(V, 6)
    if ser:
        A(table(["Pattern", "n", "First", "Last", "Median lift", "Big-win %", "Flop %", "Others' median: 90d before add \u2192 after", "If dropped: before \u2192 after"], [[f"\u201c{k}\u2026\u201d", len(g), e["first"], e["last"], f2(med(lifts(g))), pct(stats(g)["big"]), pct(stats(g)["flop"]), f"{short(e['before_add'])} \u2192 {short(e['after_add'])}", f"{short(e['before_drop'])} \u2192 {short(e['after_drop'])}" if e["dropped"] else "still running"] for k, g in ser for e in [series_effect(V, g)]]))
    else: A("No title pattern repeats 6+ times.\n")
    t, _ = group_table(V, lambda v: v["kind"], ["talking", "in_between", "text_music"]); A("Format kind overall:\n\n" + t)
    A(ed.get("formats", "_Editorial notes pending: which formats are real series, and what changed when they were added or dropped._\n"))
    # ---- 12 playbook
    A("\n---\n\n## 12. Playbook: how to make the next short (works for any topic)\n")
    A(ed.get("playbook_thesis", "> _Thesis pending: one sentence summarising what the winners share, written after reading the numbers._\n"))
    A("### 12.1 Format picker\n")
    pick = [(k, g) for k, g in by(U, lambda v: f"{v['style']} + {v['hook']}") if len(lifts(g)) >= 8][:5]
    A(table(["If you want\u2026", "Use", "Evidence"], [["A reliable pick" if i else "Maximum lift", k, f"median lift {f2(med(lifts(g)))}, {pct(stats(g)['big'])} big wins, {pct(stats(g)['flop'])} flops (n={len(g)})"] for i, (k, g) in enumerate(pick)]) if pick else "Too few shorts for a format picker.\n")
    A("### 12.2 Hook formulas (from real winners)\n")
    win = sorted([v for v in U if v["big_win"]], key=lambda v: -v["lift"])[:10]
    A("\n".join(f"{i}. \u201c{v['first'][:150]}\u201d ({v['style']}/{v['hook']}, {short(v['views'])} views, {v['lift']:.1f}x) [{v['id']}]({link(v)})" for i, v in enumerate(win, 1)) + "\n" if win else "No big wins in scope.\n")
    A("### 12.3 Script blueprint (medians of the big wins)\n")
    if len(win) >= 5:
        W = [v for v in U if v["big_win"]]; A(f"- **Length:** median {f0(med([v['n_sentences'] for v in W]))} sentences, {f0(med([v['duration'] for v in W]))} seconds, first sentence {f0(med([v['fw'] for v in W]))} words.\n- **Most common shape among big wins:** {collections.Counter(v['shape'] for v in W).most_common(1)[0][0]}.\n- **Opens on:** {collections.Counter(v['first_role'] for v in W).most_common(1)[0][0]}; **ends on:** {collections.Counter(v['last_role'] for v in W).most_common(1)[0][0]}.\n- **Share with a CTA:** {pct(sum(v['cta_flag'] for v in W) / len(W))} of big wins (vs {pct(sum(v['cta_flag'] for v in U) / len(U))} of all).\n- **Typical style / hook among big wins:** {collections.Counter(v['style'] for v in W).most_common(1)[0][0]} / {collections.Counter(v['hook'] for v in W).most_common(1)[0][0]}.\n")
    else: A("Too few big wins for a blueprint.\n")
    A("### 12.4 Length and delivery\n"); lb = [(k, g) for k, g in by(U, lambda v: cat_dur(v["duration"]), DUR_ORDER) if len(lifts(g)) >= 10]
    A(f"- Best duration bucket by lift: **{max(lb, key=lambda kg: med(lifts(kg[1])))[0]}**.\n" if lb else "")
    A(ed.get("delivery", ""))
    A("### 12.5 Pre-publish checklist (generated from this creator's features)\n")
    chk = []
    if fb: chk.append(f"First sentence in the **{max(fb, key=lambda kg: med(lifts(kg[1])))[0]}** word range")
    if fr: chk.append(f"First sentence uses: {fr[0]['name'].lower()}")
    for r in (fr[-2:] if fr else []): chk.append(f"First sentence avoids: {r['name'].lower()} (x{r['ratio']:.2f})")
    if c1 and c0 and med(lifts(c1)) and med(lifts(c0)): chk.append("Ends on the payoff, not an ask" if med(lifts(c0)) > med(lifts(c1)) else "Ends with a single, clear call to action")
    if lb: chk.append(f"Duration in the **{max(lb, key=lambda kg: med(lifts(kg[1])))[0]}** band")
    A("\n".join(f"- [ ] {c}" for c in chk) + "\n")
    # ---- 13 test next
    A("\n---\n\n## 13. What to test next\n")
    tests = list(ed.get("tests_next", []))
    if best_worst(by(U, lambda v: v["hook"]), "hook", 8): tests.append("**A/B the hook type.** Same script, rewrite the first sentence in the best and the weakest hook type above; compare lift.")
    if c1 and c0: tests.append("**A/B the ending.** One version ends on the payoff, one on a call to action.")
    if ser: tests.append("**Re-run the best recurring format** with a fresh topic, and track big-win share against the baseline.")
    tests.append("**Re-run this analysis in 3 months** to see whether the latest half-year is a trend or noise.")
    A("\n".join(f"{i}. {t}" for i, t in enumerate(tests, 1)) + "\n")
    # ---- appendices
    A("\n---\n\n## Appendix A. Top 25 by raw views\n\n(ID | date | views | Jev style/hook | duration | first sentence)\n")
    A(table(["ID", "Date", "Views", "Style / hook", "Dur", "First sentence (trimmed)"], [[f"[{v['id']}]({link(v)})", v["date"], f0(v["views"]), f"{v['style']}/{v['hook']}", f"{f0(v['duration'])} s", f"\u201c{v['first'][:100]}\u201d"] for v in V[:25]]))
    A("## Appendix B. Best and worst by style (by lift)\n")
    for s in STYLES:
        g = sorted([v for v in U if v["style"] == s and v["lift"] is not None], key=lambda v: -v["lift"])
        if len(g) >= 6: A(f"**{s.capitalize()}, best:** " + " \u00b7 ".join(f"\u201c{v['first'][:70]}\u201d ({v['lift']:.1f}x)" for v in g[:4]) + f". **Worst:** " + " \u00b7 ".join(f"\u201c{v['first'][:70]}\u201d ({v['lift']:.2f}x)" for v in g[-3:]) + "\n")
    A("## Appendix C. Full winning scripts (top 6 by lift)\n")
    for v in sorted([v for v in U if v["lift"] is not None], key=lambda v: -v["lift"])[:6]:
        A(f"**{esc(v['title'][:80])}** ({short(v['views'])} views, lift {v['lift']:.1f}x, {f0(v['duration'])} s, {v['n_sentences']} sentences) [{v['id']}]({link(v)})\n")
        A("\n".join(f"{i}. ({s['role']}) {s['text']}" for i, s in enumerate(v["sentences"], 1)) + "\n")
    A("## Appendix D. Method notes and reproducibility\n")
    A(f"- Pipeline: `creator_playbooks/pipeline/lab.py` (collect, transcribe, translate, label, analyse) and `playbook.py` (this document). Every number is re-derivable from `shorts_full.json`.\n- Lift: other shorts within \u00b145 days, excluding the short itself; at least 3 neighbours required.\n- Confidence tags: see the top of this document.\n- Transcription `whisper-large-v3` (Groq); translation `{F.get('translation_model')}`; Jev `jev-latest`.\n- Percentiles in section 2 use index-based approximations; the median and mean are exact.\n- Dates: {YT_CHANGE} is when {plat} began counting every play as a view (YouTube only).\n")
    # ---- Part II charts
    A("\n\n<div class='pb'></div>\n\n# PART II. Charts\n\nEvery chart is also saved as PNG and SVG in `charts/`. Each is followed by its numbers, so nothing depends on the image rendering.\n")
    for i in range(1, 17):
        A(f"\n### Chart {i}. {CHART_TITLES[i - 1]}\n"); A(f"![chart {i}](charts/{sorted(p.name for p in cd.glob(f'chart{i:02d}_*.png'))[0]})\n"); A(chart_nums[i])
    # ---- Part III register
    A(f"\n\n<div class='pb'></div>\n\n# PART III. Register (all {len(V)} analysed)\n\n### III-A. The analysed {unit}s, by views\n")
    A(table(["Rank", "ID", "Date", "Views", "Likes", "Dur s", "Sents", "Style (p)", "Hook (p)", "CTA p", "Lift", "Headline"], [[i, f"[{v['id']}]({link(v)})", v["date"], f0(v["views"]), f0(v.get("likes")), f0(v["duration"]), v["n_sentences"], f"{v['style']} ({v['style_p']:.2f})", f"{v['hook']} ({v['hook_p']:.2f})", f"{v['has_cta']:.2f}", f2(v["lift"]), v["title"][:60]] for i, v in enumerate(V, 1)]))
    # ---- Part IV
    A("\n\n<div class='pb'></div>\n\n# PART IV. Complete statistical tables\n\nUnedited outputs. Lift tables use the analysis universe stated in section 1.4.\n")
    A("### IV-A. Raw-views tables (all analysed)\n")
    for lab, key in (("style", lambda v: v["style"]), ("hook", lambda v: v["hook"]), ("style \u00d7 hook", lambda v: f"{v['style']} + {v['hook']}"), ("CTA", lambda v: "cta" if v["cta_flag"] else "no cta"), ("duration", lambda v: cat_dur(v["duration"])), ("sentence count", lambda v: cat_len(v["n_sentences"])), ("first-sentence length", lambda v: cat_fw(v["fw"])), ("year", lambda v: v["y"]), ("half-year", lambda v: v["h"]), ("language mix", lambda v: v["lang_mix"]), ("format kind", lambda v: v["kind"])):
        its = by(V, key); A(f"**{lab}**\n"); A(table(["Group", "n", "Median views", "Mean views", "p25", "p75", "Like rate"], [[k, len(g), f0(med([v["views"] for v in g])), f0(mean([v["views"] for v in g])), f0(sorted(v["views"] for v in g)[int(len(g) * .25)]), f0(sorted(v["views"] for v in g)[int(len(g) * .75)]), pct(med([v["like_rate"] for v in g]))] for k, g in sorted(its, key=lambda kg: -med([v["views"] for v in kg[1]]))]))
    A("### IV-B. Era-adjusted tables (lift vs neighbours)\n")
    for lab, key in (("style", lambda v: v["style"]), ("hook", lambda v: v["hook"]), ("style \u00d7 hook", lambda v: f"{v['style']} + {v['hook']}"), ("duration", lambda v: cat_dur(v["duration"])), ("sentence count", lambda v: cat_len(v["n_sentences"])), ("first-sentence length", lambda v: cat_fw(v["fw"])), ("first-sentence role", lambda v: v["first_role"]), ("last-sentence role", lambda v: v["last_role"]), ("role shape", lambda v: v["shape"]), ("format kind", lambda v: v["kind"]), ("language mix", lambda v: v["lang_mix"])):
        t, _ = group_table(V if lab == "format kind" else U, key); A(f"**{lab}**\n"); A(t)
    A("**First-sentence features**\n"); A(feat_table(feature_lifts(U, lambda v: v["first"], FEATURES, 5)))
    A("**Whole-script elements**\n"); A(feat_table(feature_lifts(U, lambda v: v["text"], ELEMENTS, 5)))
    # ---- Part V
    A(f"\n\n<div class='pb'></div>\n\n# PART V. Every script, with captions\n\nOne entry per analysed {unit}, ordered by views (same rank as III-A). Each sentence carries Jev's role label. Non-English videos show the English translation (what Jev read) and the original-language transcript.\n")
    for i, v in enumerate(V, 1):
        sp = ", ".join(f"{k} {p:.2f}" for k, p in sorted(v["style_probs"].items(), key=lambda kp: -kp[1])[:3]); hp = ", ".join(f"{k} {p:.2f}" for k, p in sorted(v["hook_probs"].items(), key=lambda kp: -kp[1])[:3])
        A(f"**{i}. [{v['id']}]({link(v)}) \u00b7 {v['date']} \u00b7 {f0(v['views'])} views \u00b7 {f0(v.get('likes'))} likes \u00b7 {f0(v['duration'])} s \u00b7 lift {f2(v['lift'])}x**\n")
        A(f"Jev: style = \u201c{v['style']}\u201d [{sp}] \u00b7 hook = {v['hook']} [{hp}] \u00b7 CTA probability {v['has_cta']:.2f} \u00b7 language: {v.get('language')} \u00b7 transcript model: {v['stt_model']}{' \u00b7 **low-confidence transcript**' if v['low_confidence'] else ''}\n")
        A(f"**Title:** {v['title']}\n")
        if v.get("caption"): A("**Caption:**\n\n" + "\n".join("> " + l for l in v["caption"][:1500].splitlines() if l.strip()) + "\n")
        A("**Script:**\n"); A("\n".join(f"{k}. [{s['role']}] {s['text']}" for k, s in enumerate(v["sentences"], 1)) + "\n")
        if v["labelled_on_translation"]: A("**Original-language transcript:**\n\n> " + v["original_text"][:2500] + "\n")
    # ---- Part VI
    A("\n\n<div class='pb'></div>\n\n# PART VI. Inventory: what exists, and what deleting `data/` loses\n\n### Files\n")
    A(table(["Path", "What it holds", "Needed?"], [["`CONTENT_PLAYBOOK_*.md` / `.pdf` (this file)", "Findings, charts' numbers, register, every script and caption, all stats", "**Keep**"], ["`shorts_full.json`", "One record per short: stats, caption, original and English transcript with Jev answers and probabilities, lift", "**Keep**: the machine-readable twin"], ["`charts/*.png`, `*.svg`", "The 16 charts", "Keep"], ["`data/<id>/audio.*`", "Downloaded audio", "Safe to delete"], ["`data/<id>/thumb.jpg`, `thumb_small.jpg`", "Thumbnails (the only visual record of each cover; Jev read them)", "Keep if you want covers later"], ["`data/<id>/info.json`, `transcript.json`, `english.json`, `jev.json`", "Already inside `shorts_full.json`", "Safe to delete"], ["`listing.json`, `failures.log`", "Channel listing and failed steps", "Optional"]]))
    A("### Provenance\n\n- " + f"Listing: {'yt-dlp --flat-playlist' if res['platform'] == 'youtube' else 'Apify instagram-reel-scraper'}; built {F.get('built')}.\n- Transcription: {', '.join(F.get('stt_models', []))}. Translation: {F.get('translation_model')}. Jev: `jev-latest`, ${F.get('jev_cost_usd', 0)} for the whole breakdown.\n")
    text = "\n".join(md)
    base = "CONTENT_PLAYBOOK_" + re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    (d / f"{base}.md").write_text(text)
    print(f"wrote {d / (base + '.md')} ({len(text):,} chars, {len(V)} shorts)")
    if pdf: render_pdf(text, d, base, f"{name}: {plat} Content Lab Playbook")


CSS = """body{font-family:Helvetica,Arial,'Noto Sans','Noto Sans Telugu','Noto Sans Devanagari',sans-serif;font-size:10.5pt;line-height:1.45;color:#1b1b1b;margin:0}
h1{font-size:22pt;margin:.2em 0}h2{font-size:15pt;margin:1.4em 0 .4em;border-bottom:1px solid #ddd;padding-bottom:3px}h3{page-break-after:avoid;font-size:11pt;text-transform:uppercase;letter-spacing:.05em;color:#444}
table{border-collapse:collapse;width:100%;font-size:8.5pt;margin:.6em 0;page-break-inside:auto}tr{page-break-inside:avoid}th{text-align:left;border-bottom:2px solid #222;padding:4px 5px}td{border-bottom:1px solid #e3e3e3;padding:3px 5px;vertical-align:top}
blockquote{border-left:3px solid #888;margin:.5em 0;padding:.1em .8em;color:#333;background:#f6f6f6}code{font-size:9pt;background:#f1f1f1;padding:0 3px}img{max-width:100%}.pb{page-break-before:always}a{color:#0b5cad;text-decoration:none}
.cover{height:240mm;display:flex;flex-direction:column;justify-content:center}.cover h1{font-size:34pt;max-width:75%}"""


def render_pdf(md_text, d, base, title):
    import markdown
    import subprocess
    body = markdown.markdown(md_text, extensions=["tables", "toc", "fenced_code", "sane_lists"], extension_configs={"toc": {"toc_depth": "1-3"}})
    toc = markdown.Markdown(extensions=["toc"], extension_configs={"toc": {"toc_depth": "1-3"}}); toc.convert(md_text)
    page = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='cover'><h1>{html.escape(title)}</h1><hr style='width:60mm;margin:0'><p style='color:#555'>{dt.date.today().strftime('%B %d, %Y')}</p></div><div class='pb'></div><h3>Contents</h3>{toc.toc}<div class='pb'></div>{body}</body></html>"
    hp = d / f"{base}.html"; hp.write_text(page)
    r = subprocess.run(["node", str(HERE / "html2pdf.js"), str(hp), str(d / f"{base}.pdf"), title], capture_output=True, text=True, env={**__import__("os").environ, "NODE_PATH": subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()})
    if r.returncode: print("PDF step failed:", r.stderr[-400:]); return
    hp.unlink(); print(f"wrote {d / (base + '.pdf')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("who"); ap.add_argument("--no-pdf", action="store_true"); a = ap.parse_args()
    cs = json.loads((HERE / "creators.json").read_text())
    c = next((c for c in cs if str(c["n"]) == a.who or a.who in c["folder"]), None) or sys.exit("unknown creator")
    build(c["folder"], pdf=not a.no_pdf)
