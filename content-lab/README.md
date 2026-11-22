# Content Lab

Jev (TypeSafe) breaks down every short-form video of one creator and shows which kinds of videos win.

```bash
pip install -r requirements.txt            # needs ffmpeg on PATH
export OPENAI_API_KEY=...                  # transcripts; Jev key is read from ~/.config/typesafe/api_key
python 1_collect.py https://www.youtube.com/@CREATOR/shorts --since 2y   # or an Instagram profile URL
python 2_transcribe.py
python 3_breakdown.py
python 4_show.py                           # writes and opens report.html
```

Every step skips work already on disk, so re-running is safe. Run it from your own computer: YouTube blocks cloud IPs.
