'use client'
import { useState } from 'react'

export default function AuditEditor({ seedUrl='', seedService='Strategy' }: { seedUrl?: string, seedService?: string }) {
  const [website, setWebsite] = useState(seedUrl)
  const [service, setService] = useState(seedService)
  const [socials, setSocials] = useState('')
  const [loading, setLoading] = useState(false)
  const [output, setOutput] = useState('')

  const run = async () => {
    setLoading(true)
    setOutput('')
    const res = await fetch('/api/audit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ website, socials: socials.split(/\s+/).filter(Boolean), service })
    })
    const data = await res.json()
    setOutput(data.markdown || 'No output.')
    setLoading(false)
  }

  return (
    <div className="grid gap-4">
      <div className="card p-4 grid gap-3">
        <div className="grid md:grid-cols-3 gap-3">
          <input className="input" placeholder="Company website (https://...)" value={website} onChange={e=>setWebsite(e.target.value)} />
          <select className="select" value={service} onChange={e=>setService(e.target.value)}>
            <option>Strategy</option>
            <option>Organic Content</option>
            <option>Performance Creatives</option>
            <option>Ad Film</option>
          </select>
          <input className="input" placeholder="Social links (space-separated)" value={socials} onChange={e=>setSocials(e.target.value)} />
        </div>
        <div className="flex gap-3">
          <button className="btn" onClick={run} disabled={loading}>{loading? 'Running…':'Run Audit'}</button>
          {output && <button className="btn" onClick={()=>window.print()}>Export (Print to PDF)</button>}
        </div>
      </div>
      <div className="card p-6">
        <article className="prose prose-invert max-w-none">
          <div dangerouslySetInnerHTML={{__html: output.replaceAll('\n','<br/>')}} />
        </article>
      </div>
    </div>
  )
}
