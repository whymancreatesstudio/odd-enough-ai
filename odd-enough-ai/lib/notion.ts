import { ODD } from './config'

export async function upsertCompany(data: any) {
  if (!ODD.NOTION_TOKEN || !ODD.NOTION_DB_COMPANIES) {
    return { ok: true, id: `local_${Date.now()}` }
  }
  // TODO: Implement with @notionhq/client
  return { ok: true, id: `notion_${Date.now()}` }
}
