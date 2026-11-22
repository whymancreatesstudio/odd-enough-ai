#!/usr/bin/env python3
"""Run a whole round in order, one creator at a time. Failures stop that creator only.
  python3 run_round.py round1            # everything
  python3 run_round.py round1 --stage collect   # just one stage for the whole round
Re-running resumes: every stage skips finished work."""
import json, pathlib, subprocess, sys
H = pathlib.Path(__file__).resolve().parent
name = sys.argv[1]
stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "all"
rnd = json.loads((H / "rounds.json").read_text())[name]
for g in rnd["order"]:
    print(f"\n######## {g['group']} ########")
    for n in g["creators"]:
        r = subprocess.run([sys.executable, str(H / "lab.py"), str(n), stage])
        if r.returncode: print(f"!! creator {n} stopped (exit {r.returncode}); continuing with the next")
