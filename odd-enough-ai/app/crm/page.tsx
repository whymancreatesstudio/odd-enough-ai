import LeadTable from '@/components/LeadTable'

const seed = [
  { id: '1', name: 'Sid’s Farm', industry: 'FMCG/Dairy', score: 78, stage: 'Qualified', website: 'https://sidsfarm.com' },
  { id: '2', name: 'Vaishnaoi Group', industry: 'Real Estate', score: 66, stage: 'Research & Audit', website: 'https://vaishnaoigroup.com' },
  { id: '3', name: 'Redcliffe Labs', industry: 'Diagnostics', score: 62, stage: 'Outreach Sent', website: 'https://redcliffelabs.com' },
]

export default function Page() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">CRM</h1>
      <LeadTable initial={seed} />
    </div>
  )
}
