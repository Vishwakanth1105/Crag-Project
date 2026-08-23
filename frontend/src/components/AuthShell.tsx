import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Logo } from '@/components/Layout'

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            'radial-gradient(ellipse_at_top_left, oklch(0.85 0.08 264 / 0.35), transparent 55%), radial-gradient(ellipse_at_bottom_right, oklch(0.85 0.1 320 / 0.3), transparent 55%)',
        }}
      />
      <div className="animate-fade-in-up relative w-full max-w-md">
        <div className="mb-6 flex flex-col items-center gap-4 text-center">
          <Logo />
          <Link
            to="/"
            className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm transition-colors"
          >
            <ArrowLeft className="size-3.5" /> Back to home
          </Link>
        </div>
        {children}
      </div>
    </div>
  )
}