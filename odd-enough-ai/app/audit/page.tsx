import AuditEditor from '@/components/AuditEditor'

export default function Page({ searchParams }: { searchParams: { company?: string; website?: string } }) {
  const { website } = searchParams || {}
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Audit Generator</h1>
      <p className="text-[var(--dim)]">Odd Enough style. No fluff. Actionable. Client-ready.</p>
      <AuditEditor seedUrl={website || ''} />
    </div>
  )
}
