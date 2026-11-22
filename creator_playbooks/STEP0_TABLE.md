# Step 0: creator resolution, cost and time (estimates)

`*` = YouTube is the only platform I could measure; Instagram counts need an Apify token, so "primary platform" is provisional.

| # | Creator | Handle | Platform | Followers | Short-form count (YT) | Analysed (cap 1,000) | Language | Est. cost | Est. time | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Raw Talks with VK | @RawTalkswithVK | YouTube Shorts* | 2.61M subs | 1640 | 1000 | Telugu | $4 | 1.1 h | *IG not checked |
| 2 | Telugu Connects | @TeluguConnects_ (IG @teluguconnects_) | YouTube Shorts* | 380K subs | 1587 | 1000 | Telugu/Tenglish | $6 | 1.1 h | CONFIRM handle: only candidate found; it is the Growth Podcast channel |
| 3 | Prasad's Tech in Telugu | @PrasadTechInTelugu | YouTube Shorts* | 5.22M subs | 605 | 605 | Telugu | $3 | 0.8 h |  |
| 4 | Aye Jude | @AyeJude | YouTube Shorts* | 4.23M subs | 1091 | 1000 | Telugu/Tenglish (assumed) | $4 | 1.1 h | CONFIRM this is the Telugu educator |
| 5 | Think School | @thinkschool | YouTube Shorts* | 6.63M subs | 573 | 573 | Hinglish/English | $3 | 0.8 h |  |
| 6 | Dhruv Rathee Shorts | @drshorts (main @dhruvrathee: 38 Shorts, 33.4M) | YouTube Shorts | 5.36M subs | 336 | 336 | Hindi | $2 | 0.6 h | Main channel analysed as a note only |
| 7 | Abhi and Niyu | @AbhiandNiyu | YouTube Shorts* | 6.66M subs | 514 | 514 | Hinglish | $2 | 0.7 h | *IG not checked |
| 8 | Mohak Mangal | @mohak_mangal (4.43M subs, NO Shorts tab) | Instagram Reels (likely) | IG count not checked | ? | 1000? | Hinglish | $7 | 1.1 h | Needs Apify; I could not size IG |
| 9 | Samay Raina | @SamayRainaOfficial | Instagram Reels (likely) | YT 12.4M subs | 42 | 42 | Hinglish | $0 | 0.3 h | Only 42 YouTube Shorts, so IG is probably the real set |
| 10 | Tanmay Bhat | @TanmayBhat | YouTube Shorts* | 5.54M subs | 883 | 883 | Hinglish | $4 | 1.0 h | *IG not checked |
| 11 | Rebel Kid | IG @the.rebel.kid (YT @RebelKid is an unrelated 3-sub channel) | Instagram Reels | ~5M followers | ? | 1000? | Hinglish/English | $7 | 1.1 h | 509 IG posts (not all reels) |
| 12 | Ankur Warikoo | @warikoo | YouTube Shorts* | 7.18M subs | 1552 | 1000 | Hinglish/English | $5 | 1.1 h | *IG not checked |
| 13 | Raj Shamani | @RajShamani (+ @RajShamaniClips) | YouTube Shorts* | 22.9M subs | 1986 | 1000 | Hinglish | $6 | 1.1 h | Clips channel has only 14 Shorts / 1.88M subs: CONFIRM this is the clips channel you mean |
| 14 | CA Rachana Ranade | @CARachanaRanade | YouTube Shorts* | 5.42M subs | 401 | 401 | Hindi/Marathi/English | $2 | 0.6 h | Language per channel: she runs separate channels; CONFIRM which |
| 15 | Nas Daily | @nasdaily | YouTube Shorts* | 14.0M subs | 970 | 970 | English | $5 | 1.1 h |  |
| 16 | Zack D. Films | @ZackDFilms | YouTube Shorts* | 29.8M subs | 4215 | 1000 | English | $5 | 1.1 h |  |
| 17 | MrBeast (Shorts) | @MrBeast | YouTube Shorts | 527M subs | 208 | 208 | English | $1 | 0.5 h | Only 208 Shorts |
| 18 | Johnny Harris | @johnnyharris | YouTube Shorts* | 8.02M subs | 319 | 319 | English | $2 | 0.6 h |  |
| 19 | Jenny Hoyos | @JennyHoyos | YouTube Shorts* | 12.4M subs | 4647 | 1000 | English | $3 | 1.1 h |  |
| 20 | Ryan Serhant | @RyanSerhant | YouTube Shorts* | 1.49M subs | 303 | 303 | English | $2 | 0.6 h | *IG not checked |

**Total: about 14,154 videos, about $73 (range $58-$116), about 18 hours of machine time.**

Assumptions: transcription $0.006/min at the stated average length; Jev $0.042 per million input tokens (about 3-4K tokens per video, so about $0.0002); Instagram scraping about $2.6 per 1,000 reels on Apify (unverified, check your plan); YouTube listing is free; downloads about 3 s per video at 2 at a time.
