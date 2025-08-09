import { NextRequest } from 'next/server'
import { generateAuditMarkdown } from '@/lib/openai'

export async function POST(req: NextRequest) {
  const { website, socials = [], service = 'Strategy' } = await req.json()
  const markdown = await generateAuditMarkdown({ website, socials, service })
  return Response.json({ markdown })
}
