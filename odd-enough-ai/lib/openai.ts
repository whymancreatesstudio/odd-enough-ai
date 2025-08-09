import { ODD } from './config'

export async function generateAuditMarkdown(input: {
  website: string
  socials?: string[]
  service: string
}) {
  if (!ODD.OPENAI_API_KEY) {
    return `# Snapshot
**Website:** ${input.website || 'N/A'}  
**Service Focus:** ${input.service}

---
# Quick Wins (0–7 days)
- Replace static hero with motion-first hook. Track 3s holds.
- Add UGC + proof ad in retargeting; aim +30% CTR.
- Tighten offer framing on hero: outcome + time + CTA.

# 30–60–90 Plan
**30:** Hook matrix (5 hooks × 3 formats), ship 12 posts.  
**60:** Paid creative sprint (6 ads), set testing cadence.  
**90:** Ad film concept + pre-viz; launch with landing page.

# Impact vs Effort
| Initiative | Impact | Effort |
|---|---|---|
| Hook matrix rollout | High | Low |
| UGC proof ads | High | Med |
| Website hero rewrite | Med | Low |
| Ad film | Very High | High |

# Before/After Copy
**Before:** Generic feature-led headline.  
**After:** “Cut CAC by 30% in 30 days — here’s the test plan.”

# Creative Swipes
1) Brand A’s founder-led demo (energy + sincerity)  
2) Brand B’s 6–9s motion loop hero  
3) Brand C’s testimonial carousel

# Budget Guidance
- Organic engine: ₹1–2L/mo  
- Perf creatives: ₹1.5–3L/mo + media  
- Ad film: ₹4–12L

# Why Odd Enough
- ₹195Cr pipeline for a villa project  
- +40% CTR with storytelling TVC  
- 3× engagement lifts; 50M+ organic views

# CTA
Reply “AUDIT” for the 3-page teardown.`
  }
  // TODO: call OpenAI with your detailed prompt if key is present.
  return await generateAuditMarkdown(input)
}
