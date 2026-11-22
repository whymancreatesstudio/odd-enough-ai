# Creator playbooks pipeline

Round 1 order (rounds.json): English creators, then Hindi/Hinglish, then Telugu. Unconfirmed creators and Instagram are round 2.

On a machine with a normal internet connection (YouTube blocks cloud IPs), with `ffmpeg` installed:

    pip install yt-dlp httpx matplotlib markdown
    export GROQ_API_KEY=...                       # whisper-large-v3 + translation
    echo -n "$TYPESAFE_KEY" > ~/.config/typesafe/api_key   # Jev
    python3 run_round.py round1                   # collect > transcribe > translate > label > analyse, per creator
    git add creator_playbooks/*/shorts_full.json && git commit && git push

Each stage skips finished work, so an interrupted run resumes. Downloads stop after 5 refusals in a row.
Playbooks are built from `shorts_full.json` (no audio needed): `python3 playbook.py <n>`; `python3 index.py` refreshes INDEX.md.
Qualitative sections (content families, why things failed, language/format narrative, thesis) come from `<folder>/editorial.json`, written after reading the numbers.
