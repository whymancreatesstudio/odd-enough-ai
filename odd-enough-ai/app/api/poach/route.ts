import { NextRequest } from 'next/server'

export async function POST(req: NextRequest) {
  const { industry = 'FMCG/D2C', geo = 'India', seed = '' } = await req.json()

  const examples = [
    { brand: 'Brand A Foods', agency: 'XYZ Creative', signals: ['Posting gap 21d', 'Stale ads 45d'], angle: 'Creative refresh challenge (3 ads in 7 days)' },
    { brand: 'Health+ Diagnostics', agency: '', signals: ['Engagement drop 3m', 'Hiring “Head of Growth”'], angle: 'Free strategic audit + retargeting plan' },
    { brand: 'Nova Estates', agency: 'CityMktg', signals: ['Negative ad comments', 'Stale ads 30d'], angle: 'Storytelling makeover for site + launch ads' },
  ]

  let results = examples
  if (seed) {
    results = examples.filter(x => x.brand.toLowerCase().split(' ')[0] == seed.toLowerCase().split(' ')[0])
    if (!results.length) results = examples
  }

  return Response.json({ results })
}
