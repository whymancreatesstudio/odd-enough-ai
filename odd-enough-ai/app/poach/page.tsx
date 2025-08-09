'use client'
import { useEffect, useState } from 'react'

export default function Page({ searchParams }: { searchParams: { seed?: string } }) {
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState<any[]>([])
  const [industry, setIndustry] = useState('FMCG/D2C')
  const [geo, setGeo] = useState('India')
  const [seed, setSeed] = useState(searchParams?.seed || '')

  const run = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/poach', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ industry, geo, seed }) })
      const data = await res.json()
      setRows(data.results || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(()=>{ if(seed) run() },[])

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Poach Finder</h1>
      <div className="card p-4 grid md:grid-cols-4 gap-3">
        <select className="select" value={industry} onChange={e=>setIndustry(e.target.value)}>
          <option>FMCG/D2C</option>
          <option>Real Estate</option>
          <option>Diagnostics/Medtech</option>
        </select>
        <select className="select" value={geo} onChange={e=>setGeo(e.target.value)}>
          <option>India</option>
          <option>Hyderabad</option>
          <option>Bangalore</option>
          <option>Mumbai</option>
        </select>
        <input className="input" placeholder="Seed brand (optional)" value={seed} onChange={e=>setSeed(e.target.value)} />
        <button className="btn" onClick={run} disabled={loading}>{loading? 'Scanning…':'Find Prospects'}</button>
      </div>

      <div className="card p-4 overflow-auto">
        <table className="table min-w-[700px]">
          <thead>
            <tr>
              <th>Brand</th>
              <th>Detected Agency</th>
              <th>Signals</th>
              <th>Poach Angle</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i)=> (
              <tr key={i}>
                <td className="font-medium">{r.brand}</td>
                <td>{r.agency || '—'}</td>
                <td className="text-xs text-[var(--dim)]">{(r.signals||[]).join(', ')}</td>
                <td>{r.angle}</td>
                <td><a className="btn" href={`/crm`}>Add to CRM</a></td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={5} className="py-10 text-center text-[var(--dim)]">No results yet. Run a scan.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
