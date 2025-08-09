import './globals.css'
import Link from 'next/link'
import { ReactNode } from 'react'
import { LayoutGrid, Building2, FileText, ShieldHalf } from 'lucide-react'

export const metadata = {
  title: 'Odd Enough AI',
  description: 'Story-first, performance-driven growth OS',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen grid grid-cols-12">
          <aside className="col-span-12 md:col-span-2 p-4 md:p-6 space-y-3 sticky top-0 h-screen">
            <div className="card p-4">
              <div className="text-xl font-bold">Odd Enough <span className="text-[var(--primary)]">AI</span></div>
              <div className="text-sm text-[var(--dim)]">Growth OS</div>
            </div>
            <nav className="card p-2">
              <ul className="space-y-1">
                <li>
                  <Link className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5" href="/">
                    <LayoutGrid size={18}/> Dashboard
                  </Link>
                </li>
                <li>
                  <Link className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5" href="/crm">
                    <Building2 size={18}/> CRM
                  </Link>
                </li>
                <li>
                  <Link className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5" href="/audit">
                    <FileText size={18}/> Audit
                  </Link>
                </li>
                <li>
                  <Link className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5" href="/poach">
                    <ShieldHalf size={18}/> Poach Finder
                  </Link>
                </li>
              </ul>
            </nav>
            <div className="card p-4 text-xs text-[var(--dim)]">
              © {new Date().getFullYear()} Odd Enough. All Rights Reserved.
            </div>
          </aside>
          <main className="col-span-12 md:col-span-10 p-4 md:p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
