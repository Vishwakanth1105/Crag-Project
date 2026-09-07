import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { Link } from 'react-router-dom'
import { ArrowLeft, ScrollText } from 'lucide-react'
import { api } from '@/lib/api'
import { AdminAccessCard } from '@/components/AdminAccessCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDate } from '@/lib/utils'
import type { AdminQueryLog } from '@/lib/types'

function formatLatency(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`
}

export function SystemQueryLogs() {
  const logs = useQuery({
    queryKey: ['admin-query-logs'],
    queryFn: async () => {
      const { data } = await api.get<{ items: AdminQueryLog[] }>('/admin/query-logs')
      return data.items
    },
    retry: false,
  })

  if (logs.isError) {
    const status = logs.error instanceof AxiosError ? logs.error.response?.status : undefined
    return (
      <div className="space-y-6">
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
          <h1 className="text-3xl font-bold tracking-tight">Query logs</h1>
        </div>
        {status === 403 ? (
          <AdminAccessCard resource="query logs" />
        ) : (
          <p className="text-destructive text-sm">Failed to load query logs.</p>
        )}
      </div>
    )
  }

  const items = logs.data ?? []

  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/system"
          className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1.5 text-sm font-medium"
        >
          <ArrowLeft className="size-4" /> Back to System
        </Link>
        <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
        <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
          <ScrollText className="size-7" /> Query logs
        </h1>
        <p className="text-muted-foreground mt-1">
          Every question asked, the answer given, and how it performed.
        </p>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>All queries</CardTitle>
          <CardDescription>{items.length} logged queries.</CardDescription>
        </CardHeader>
        <CardContent>
          {logs.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-xl" />
              ))}
            </div>
          ) : items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Question</TableHead>
                  <TableHead>Answer</TableHead>
                  <TableHead className="text-right">Confidence</TableHead>
                  <TableHead>Web</TableHead>
                  <TableHead>Retries</TableHead>
                  <TableHead className="text-right">Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {log.owner_email}
                    </TableCell>
                    <TableCell>
                      <span className="block max-w-72 text-sm font-medium">{log.query}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-muted-foreground block max-w-120 whitespace-pre-wrap text-sm">
                        {log.answer}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-right">
                      {(log.confidence_score * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell>
                      {log.web_search_used ? (
                        <Badge variant="success">Web</Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {log.retry_count}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-right">
                      {formatLatency(log.latency_ms)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground py-4 text-sm">
              No queries have been logged yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}