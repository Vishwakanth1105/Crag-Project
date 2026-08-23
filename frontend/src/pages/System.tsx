import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import {
  ShieldAlert,
  Activity,
  Users,
  FileText,
  MessageSquare,
  MessagesSquare,
  ScrollText,
} from 'lucide-react'
import { api } from '@/lib/api'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { SystemStats } from '@/lib/types'

const statCards = [
  { key: 'users', label: 'Users', icon: Users, accent: 'from-indigo-500 to-violet-600' },
  { key: 'documents', label: 'Documents', icon: FileText, accent: 'from-sky-500 to-cyan-600' },
  { key: 'conversations', label: 'Conversations', icon: MessageSquare, accent: 'from-fuchsia-500 to-pink-600' },
  { key: 'messages', label: 'Messages', icon: MessagesSquare, accent: 'from-emerald-500 to-teal-600' },
  { key: 'query_logs', label: 'Query logs', icon: ScrollText, accent: 'from-amber-500 to-orange-600' },
] as const

export function System() {
  const system = useQuery({
    queryKey: ['system'],
    queryFn: async () => {
      const { data } = await api.get<SystemStats>('/admin/system')
      return data
    },
    retry: false,
  })

  if (system.isError) {
    const status = system.error instanceof AxiosError ? system.error.response?.status : undefined
    if (status === 403) {
      return (
        <div className="space-y-6">
          <div>
            <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
            <h1 className="text-3xl font-bold tracking-tight">System</h1>
          </div>
          <Card className="shadow-card">
            <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
              <span className="bg-warning/15 text-warning-foreground flex size-14 items-center justify-center rounded-2xl">
                <ShieldAlert className="size-7" />
              </span>
              <div>
                <p className="font-semibold">Administrator access required</p>
                <p className="text-muted-foreground mt-1 text-sm">
                  Sign in with an admin account to view system status.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">System</h1>
        <p className="text-destructive text-sm">Failed to load system status.</p>
      </div>
    )
  }

  const stats = system.data

  return (
    <div className="space-y-8">
      <div>
        <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
        <h1 className="text-3xl font-bold tracking-tight">System</h1>
        <p className="text-muted-foreground mt-1">
          Platform statistics and dependency health at a glance.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {statCards.map(({ key, label, icon: Icon, accent }) => (
          <div
            key={key}
            className="shadow-card flex items-center gap-4 rounded-2xl border bg-card p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover"
          >
            <span
              className={cn(
                'flex size-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg',
                accent,
              )}
            >
              <Icon className="size-5" />
            </span>
            <div>
              <p className="text-muted-foreground text-sm">{label}</p>
              {system.isLoading ? (
                <Skeleton className="mt-1 h-7 w-12" />
              ) : (
                <p className="text-2xl font-bold tracking-tight">
                  {stats?.[key] ?? 0}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="size-5" /> Dependencies
            </CardTitle>
            <CardDescription>Live health of the backing services.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {system.isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-11 w-full rounded-xl" />
                ))}
              </div>
            ) : (
              stats?.dependencies.map((dependency) => {
                const ready = dependency.status === 'ready'
                return (
                  <div
                    key={dependency.name}
                    className="flex items-center justify-between rounded-xl border px-4 py-2.5 text-sm"
                  >
                    <div className="flex items-center gap-2.5">
                      <span
                        className={cn(
                          'size-2 rounded-full',
                          ready ? 'bg-emerald-500' : 'bg-rose-500',
                        )}
                      />
                      <span className="font-medium">{dependency.name}</span>
                    </div>
                    <Badge variant={ready ? 'success' : 'destructive'}>
                      {ready ? 'Ready' : dependency.status}
                    </Badge>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Ingestion jobs</CardTitle>
            <CardDescription>Distribution of background job states.</CardDescription>
          </CardHeader>
          <CardContent>
            {system.isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-6 w-full rounded-lg" />
                ))}
              </div>
            ) : Object.keys(stats?.ingestion_jobs ?? {}).length ? (
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats?.ingestion_jobs ?? {}).map(([status, count]) => (
                  <div
                    key={status}
                    className="shadow-card flex items-center gap-2 rounded-xl border bg-card px-3.5 py-2"
                  >
                    <Badge
                      variant={
                        status === 'done'
                          ? 'success'
                          : status === 'failed'
                            ? 'destructive'
                            : 'warning'
                      }
                    >
                      {status}
                    </Badge>
                    <span className="text-muted-foreground text-sm font-medium">
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground py-4 text-sm">
                No ingestion jobs have run yet.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}