import KpiCard from '@/components/KpiCard'
import Section from '@/components/Section'

export default function Page() {
  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-[var(--dim)]">Your growth cockpit — CRM, audits, and poach-finding in one place.</p>
        </div>
      </div>

      <Section title="This Week">
        <div className="grid md:grid-cols-4 gap-4">
          <KpiCard label="Hot Leads" value="8" sub="Score ≥ 60"/>
          <KpiCard label="Audits Generated" value="5" sub="2 awaiting approval"/>
          <KpiCard label="Poachables Found" value="17" sub="FMCG focus"/>
          <KpiCard label="Meetings Booked" value="4" sub="Target: 10/week"/>
        </div>
      </Section>

      <Section title="Quick Start">
        <div className="grid md:grid-cols-3 gap-4">
          <a className="card p-6 hover:bg-white/5" href="/crm">
            <div className="text-lg font-semibold">Open CRM</div>
            <div className="text-[var(--dim)]">Import leads, score them, and move deals.</div>
          </a>
          <a className="card p-6 hover:bg-white/5" href="/audit">
            <div className="text-lg font-semibold">Run an Audit</div>
            <div className="text-[var(--dim)]">Generate a client-ready teardown with quick wins.</div>
          </a>
          <a className="card p-6 hover:bg-white/5" href="/poach">
            <div className="text-lg font-semibold">Find Poachables</div>
            <div className="text-[var(--dim)]">Spot brands unhappy with current agencies.</div>
          </a>
        </div>
      </Section>
    </div>
  )
}
