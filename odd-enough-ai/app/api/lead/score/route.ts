import { NextRequest } from 'next/server'

export async function POST(req: NextRequest) {
  const { name, website } = await req.json()

  const industry = guessIndustry(name || '', website || '')
  let score = 40
  if (/(farm|foods|beverage|milk|dairy|snack|fmcg|d2c)/i.test(`${name} ${website}`)) score += 20
  if (/(estate|builders|infra|homes|villa|apartments)/i.test(`${name} ${website}`)) score += 20
  if (/(lab|diagnostic|health|med|clinic)/i.test(`${name} ${website}`)) score += 20

  const stage = score >= 60 ? 'Qualified' : 'New Lead'

  return Response.json({ name, website, industry, score, stage })
}

function guessIndustry(name: string, website: string) {
  const s = (name + ' ' + website).toLowerCase()
  if (s.match(/farm|milk|foods|snack|fmcg|d2c/)) return 'FMCG/D2C'
  if (s.match(/estate|builders|infra|homes|villa|apartments/)) return 'Real Estate'
  if (s.match(/lab|diagnostic|health|med|clinic/)) return 'Diagnostics/Medtech'
  return '—'
}
