import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Users,
  FileText,
  MessageSquare,
  MessagesSquare,
  ScrollText,
  ArrowRight,
  ShieldCheck,
  LifeBuoy,
  Server,
  Activity,
} from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { SystemStats } from '@/lib/types'

const statCards = [
  {
    key: 'users',
    label: 'Users',
    icon: Users,
    to: '/users',
    accent: 'from-indigo-500 to-violet-600 shadow-indigo-500/30',
  },
  {
    key: 'documents',
    label: 'Documents',
    icon: FileText,
    to: '/system',
    accent: 'from-sky-500 to-cyan-600 shadow-sky-500/30',
  },
  {
    key: 'conversations',
    label: 'Conversations',
    icon: MessageSquare,
    to: '/system',
    accent: 'from-fuchsia-500 to-pink-600 shadow-fuchsia-500/30',
  },
  {
    key: 'messages',
    label: 'Messages',
    icon: MessagesSquare,
    to: '/system',
    accent: 'from-emerald-500 to-teal-600 shadow-emerald-500/30',
  },
  {
    key: 'query_logs',
    label: 'Query logs',
    icon: ScrollText,
    to: '/system',
    accent: 'from-amber-500 to-orange-600 shadow-amber-500/30',
  },
] as const

const quickLinks = [
  {
    to: '/users',
    icon: Users,
    title: 'User management',
    description: 'Inspect accounts, ban or remove users',
  },
  {
    to: '/support',
    icon: LifeBuoy,
    title: 'Support inbox',
    description: 'Respond to and resolve user tickets',
  },
  {
    to: '/system',
    icon: Server,
    title: 'System status',
    description: 'Platform statistics and dependency health',
  },
]

export function AdminDashboard() {
  const { user } = useAuth()

  const system = useQuery({
    queryKey: ['system'],
    queryFn: async () => {
      const { data } = await api.get<SystemStats>('/admin/system')
      return data
    },
    refetchInterval: 30_000,
  })

  const allReady =
    system.data?.dependencies.every((dependency) => dependency.status === 'ready') ?? false

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-medium">
            {new Date().toLocaleDateString(undefined, {
              weekday: 'long',
              month: 'long',
              day: 'numeric',
            })}
          </p>
          <h1 className="text-3xl font-bold tracking-tight">
            Admin console ·{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              {user?.full_name?.split(' ')[0] || user?.email}
            </span>
          </h1>
          <p className="text-muted-foreground mt-1 flex items-center gap-1.5 text-sm">
            <span
              className={cn(
                'size-2 rounded-full',
                system.isLoading ? 'bg-muted-foreground' : allReady ? 'bg-emerald-500' : 'bg-rose-500',
              )}
            />
            {system.isLoading
              ? 'Checking platform health…'
              : allReady
                ? 'All systems operational'
                : 'Some dependencies are unhealthy'}
          </p>
        </div>
        <Link to="/system">
          <span className="shadow-card inline-flex items-center gap-2 rounded-full border bg-card px-4 py-2 text-sm font-medium">
            <Activity className="size-4" /> Full status
          </span>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-5">
        {statCards.map(({ key, label, icon: Icon, to, accent }) => (
          <Link
            key={key}
            to={to}
            className="shadow-card hover:shadow-card-hover group rounded-2xl border bg-card p-5 transition-all duration-300 hover:-translate-y-0.5"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-muted-foreground text-sm">{label}</p>
                {system.isLoading ? (
                  <Skeleton className="mt-2 h-8 w-14" />
                ) : (
                  <p className="mt-1 text-3xl font-bold tracking-tight">
                    {system.data?.[key] ?? 0}
                  </p>
                )}
              </div>
              <span
                className={cn(
                  'group-hover:scale-110 inline-flex size-11 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg transition-transform',
                  accent,
                )}
              >
                <Icon className="size-5" />
              </span>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Manage</h2>
          <div className="grid gap-3">
            {quickLinks.map(({ to, icon: Icon, title, description }) => (
              <Link
                key={to}
                to={to}
                className="shadow-card group flex items-center gap-4 rounded-2xl border bg-card p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover"
              >
                <span className="bg-accent text-accent-foreground group-hover:bg-primary group-hover:text-primary-foreground flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors">
                  <Icon className="size-5" />
                </span>
                <div className="flex-1">
                  <p className="font-semibold">{title}</p>
                  <p className="text-muted-foreground text-sm">{description}</p>
                </div>
                <ArrowRight className="text-muted-foreground group-hover:text-foreground size-4 transition-colors" />
              </Link>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Dependencies</h2>
          <div className="shadow-card rounded-2xl border bg-card p-5">
            {system.isLoading ? (
              <div className="space-y-3">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-9 w-full rounded-xl" />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {system.data?.dependencies.map((dependency) => {
                  const ready = dependency.status === 'ready'
                  return (
                    <div
                      key={dependency.name}
                      className="flex items-center justify-between rounded-xl border px-4 py-2 text-sm"
                    >
                      <span className="font-medium capitalize">{dependency.name}</span>
                      <Badge variant={ready ? 'success' : 'destructive'}>
                        {ready ? 'Ready' : dependency.status}
                      </Badge>
                    </div>
                  )
                })}
              </div>
            )}
            <p className="text-muted-foreground mt-4 flex items-center gap-1.5 text-xs">
              <ShieldCheck className="size-3.5" /> Backing services powering the platform.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
