"""All Jev question wording lives here, so it is easy to audit and edit."""

STYLE = {
    "storytelling": "Tells a story with a lesson at the end.",
    "tactical": "Teaches a how-to, steps, a framework or a tactic.",
    "opinion": "A hot take or contrarian opinion.",
    "qa": "Answers a question someone asked.",
    "mindset": "Motivation, mindset or discipline advice.",
}
HOOK = {
    "question": "The first sentence asks the viewer a question.",
    "claim": "The first sentence makes a bold or surprising claim.",
    "story": "The first sentence drops the viewer into a story.",
    "callout": "The first sentence calls out a kind of person.",
    "number": "The first sentence leads with a number or a result.",
}
ROLE = {
    "hook": "Grabs attention at the start of the video.",
    "setup": "Sets up the problem, context or story.",
    "body": "Delivers the main content: steps, points, details or the middle of the story.",
    "payoff": "Delivers the conclusion, lesson or answer the video was building to.",
    "cta": "Asks the viewer to do something: follow, subscribe, comment, share, click.",
}


def build(title, sentences, thumb_ref):
    n = len(sentences)
    qs = {
        "style": {"type": "choice", "instructions": "What kind of video is this?", "criteria": STYLE},
        "hook": {"type": "choice",
                 "instructions": "How does the first sentence of `script` (`script.sentence_1`) hook the viewer?",
                 "criteria": HOOK},
        "has_cta": {"type": "noul", "instructions": "Does the script end with a call to action?"},
    }
    for i in range(1, n + 1):
        qs[f"role_{i}"] = {"type": "choice",
                           "instructions": f"What role does `script.sentence_{i}` play in the video?",
                           "criteria": ROLE}
    state = {"title": title,
             "thumbnail": thumb_ref,
             "script": {f"sentence_{i}": s for i, s in enumerate(sentences, 1)}}
    return state, qs
