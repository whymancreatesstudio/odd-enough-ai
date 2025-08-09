# Odd Enough AI — Web App (MVP)

A single, beautiful web app for **CRM**, **Audit Generator**, and **Poach Finder**, built with **Next.js 14 + Tailwind**.  
Backed by **Notion (optional)** and **OpenAI (optional)**. Works out-of-the-box with mock logic if keys are missing.

## Features
- Dashboard with KPIs
- CRM pipeline (add & score leads)
- Audit Generator (Odd Enough-style, export via browser print-to-PDF)
- Poach Finder (mocked signals; wire real data later)
- Clean, dark UI in Odd Enough aesthetic

## Quick Start
```bash
# 1) Install deps
npm i

# 2) Run dev server
npm run dev

# 3) Open
http://localhost:3000
```

## Environment (optional)
Create a `.env.local` with any of these:
```
OPENAI_API_KEY=sk-...
NOTION_TOKEN=secret_...
NOTION_DB_COMPANIES=...
NOTION_DB_AUDITS=...
```

If you leave them blank, the app still runs with mock logic.

## Where to add real integrations
- **OpenAI Audit**: `lib/openai.ts` (replace mock with real API call & prompt)
- **Notion CRUD**: `lib/notion.ts` (implement @notionhq/client to persist Companies/Audits)
- **Poach signals**: `app/api/poach/route.ts` (call your scrapers/APIs)

## Build
```bash
npm run build
npm start
```

## Tech
- Next.js 14 App Router
- TailwindCSS
- lucide-react icons
- TypeScript
# odd-enough-ai
# odd-enough-ai
# odd-enough-ai
# odd-enough-ai
# odd-enough-ai
