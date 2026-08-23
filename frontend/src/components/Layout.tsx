import { NavLink, Outlet, Link } from 'react-router-dom'
import {
  LogOut,
  MessageSquare,
  FileText,
  Gauge,
  User as UserIcon,
  Server,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <span className="bg-gradient-to-br from-indigo-600 to-violet-600 shadow-lg shadow-indigo-600/25 flex size-8 items-center justify-center rounded-lg">
        <Sparkles className="size-4 text-white" />
      </span>
      <span className="text-base font-semibold tracking-tight">
        Agentic <span className="text-primary">RAG</span>
      </span>
    </div>
  )
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function Layout() {
  const { user, logout } = useAuth()

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: Gauge },
    { to: '/chat', label: 'Chat', icon: MessageSquare },
    { to: '/documents', label: 'Documents', icon: FileText },
    ...(user?.role === 'admin'
      ? [{ to: '/system', label: 'System', icon: Server }]
      : []),
  ]

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/dashboard">
            <Logo />
          </Link>

          <nav className="bg-muted/60 flex items-center gap-1 rounded-full p-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm transition-colors',
                    isActive
                      ? 'bg-card text-foreground font-medium shadow-sm'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                }
              >
                <Icon className="size-4" />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-full p-1 pr-2 transition-colors hover:bg-accent focus-visible:ring-ring focus-visible:ring-[3px] focus-visible:outline-none"
                >
                  <Avatar>
                    <AvatarFallback>
                      {initials(user.full_name || user.email)}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-muted-foreground hidden max-w-[140px] truncate text-sm lg:inline">
                    {user.full_name || user.email}
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="flex flex-col">
                  <span className="truncate text-sm font-medium">
                    {user.full_name || 'User'}
                  </span>
                  <span className="text-muted-foreground truncate text-xs font-normal">
                    {user.email}
                  </span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/profile">
                    <UserIcon /> Profile
                  </Link>
                </DropdownMenuItem>
                {user.role === 'admin' && (
                  <DropdownMenuItem asChild>
                    <Link to="/system">
                      <Server /> System status
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onClick={() => void logout()}>
                  <LogOut /> Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </header>

      <main className="animate-fade-in mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>

      <footer className="border-t bg-card/50">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:px-6">
          <span>
            © {new Date().getFullYear()} Agentic RAG · Corrective RAG on
            LangGraph
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            All systems operational
          </span>
        </div>
      </footer>
    </div>
  )
}