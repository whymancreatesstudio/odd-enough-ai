'use client'
import { useState } from 'react'

export type Lead = {
  id: string
  name: string
  industry: string
  score: number
  stage: string
  website?: string
}

export default function LeadTable({ initial }: { initial: Lead[] }) {
  const [rows, setRows] = useState(initial)
  const [q, setQ] = useState('')
  const filtered = rows.filter(r => r.name.toLowerCase().includes(q.toLowerCase()))
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-3 mb-3">
        <input className="input max-w-sm" placeholder="Search company..." value={q} onChange={e=>setQ(e.target.value)} />
        <button className="btn" onClick={async ()=>{
          const name = prompt('Company name?')
          const website = prompt('Website (optional)?') || ''
          if(!name) return
          const res = await fetch('/api/lead/score', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ name, website })})
          const data = await res.json()
          setRows([{ id: crypto.randomUUID(), name, industry: data.industry || '—', score: data.score, stage: data.stage, website }, ...rows])
        }}>Add Lead</button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Company</th>
            <th>Industry</th>
            <th>Score</th>
            <th>Stage</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(r => (
            <tr key={r.id}>
              <td className="font-medium">{r.name}</td>
              <td>{r.industry}</td>
              <td><span className={r.score>=60?'text-green-400':'text-yellow-300'}>{r.score}</span></td>
              <td>{r.stage}</td>
              <td className="space-x-2">
                <a className="btn" href={`/audit?company=${encodeURIComponent(r.name)}&website=${encodeURIComponent(r.website||'')}`}>Run Audit</a>
                <a className="btn" href={`/poach?seed=${encodeURIComponent(r.name)}`}>Find Poachables</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
