import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { Link } from 'react-router-dom'
import { ArrowLeft, MessagesSquare } from 'lucide-react'
import { api } from '@/lib/api'
import { AdminAccessCard } from '@/components/AdminAccessCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDate } from '@/lib/utils'
import type { AdminMessage } from '@/lib/types'

function formatConfidence(score: number | null): string {
  return score === null ? '—' : `${(score * 100).toFixed(0)}%`
}

export function SystemMessages() {
  const messages = useQuery({
    queryKey: ['admin-messages'],
    queryFn: async () => {
      const { data } = await api.get<{ items: AdminMessage[] }>('/admin/messages')
      return data.items
    },
    retry: false,
  })

  if (messages.isError) {
    const status = messages.error instanceof AxiosError ? messages.error.response?.status : undefined
    return (
      <div className="space-y-6">
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
          <h1 className="text-3xl font-bold tracking-tight">Messages</h1>
        </div>
        {status === 403 ? (
          <AdminAccessCard resource="messages" />
        ) : (
          <p className="text-destructive text-sm">Failed to load messages.</p>
        )}
      </div>
    )
  }

  const items = messages.data ?? []

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
          <MessagesSquare className="size-7" /> Messages
        </h1>
        <p className="text-muted-foreground mt-1">
          Every message exchanged across all chats.
        </p>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>All messages</CardTitle>
          <CardDescription>{items.length} messages total.</CardDescription>
        </CardHeader>
        <CardContent>
          {messages.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-xl" />
              ))}
            </div>
          ) : items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sent</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Conversation</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Content</TableHead>
                  <TableHead className="text-right">Confidence</TableHead>
                  <TableHead>Web</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((message) => (
                  <TableRow key={message.id}>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {formatDate(message.created_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {message.owner_email}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      <span className="block max-w-56 truncate">
                        {message.conversation_title || 'New conversation'}
                      </span>
                      <span className="text-xs">#{message.conversation_id}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={message.role === 'assistant' ? 'default' : 'secondary'}>
                        {message.role}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="block max-w-120 whitespace-pre-wrap text-sm">
                        {message.content}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-right">
                      {formatConfidence(message.confidence_score)}
                    </TableCell>
                    <TableCell>
                      {message.web_search_used ? (
                        <Badge variant="success">Web</Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground py-4 text-sm">
              No messages have been exchanged yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}