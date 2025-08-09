type Props = { label: string; value: string | number; sub?: string }
export default function KpiCard({ label, value, sub }: Props) {
  return (
    <div className="card p-5">
      <div className="text-sm text-[var(--dim)]">{label}</div>
      <div className="text-3xl font-bold">{value}</div>
      {sub && <div className="text-xs text-[var(--dim)] mt-2">{sub}</div>}
    </div>
  )
}
