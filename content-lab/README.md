# Content Lab

Jev breaks down every Short of one creator and shows which kinds of videos win.
Each step is re-runnable: finished work is skipped.

    pip install yt-dlp openai httpx          # plus ffmpeg on PATH
    python3 1_collect.py --channel https://www.youtube.com/@thinkschool/shorts --since 2024-11-21
    python3 2_transcribe.py                   # needs OPENAI_API_KEY in the environment
    python3 3_jev.py                          # key in ~/.config/typesafe/api_key
    python3 4_show.py                         # writes report.html and opens it

* Step 1: 2 downloads at a time (1 for Instagram, with `--cookies-from-browser chrome`), random pauses, stops after 5 refusals in a row. Re-run to resume.
* Step 2: whisper-1, verbose_json, 8 at a time.
* Step 3: one `jev-latest` call per video, 6 at a time, retries on 429. Question wording is in `questions.py`.
* Step 4: `report.html` (static page). Groups with fewer than 10 videos are greyed out and never win.
* Data lands in `data/<video id>/` (thumb.jpg, info.json, audio.*, transcript.json, jev.json), which is git-ignored.
