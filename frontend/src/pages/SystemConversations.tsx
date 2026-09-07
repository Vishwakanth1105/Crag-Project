import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { Link } from 'react-router-dom'
import { ArrowLeft, MessageSquare } from 'lucide-react'
import { api } from '@/lib/api'
import { AdminAccessCard } from '@/components/AdminAccessCard'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDate } from '@/lib/utils'
import type { AdminConversation } from '@/lib/types'

export function SystemConversations() {
  const conversations = useQuery({
    queryKey: ['admin-conversations'],
    queryFn: async () => {
      const { data } = await api.get<{ items: AdminConversation[] }>('/admin/conversations')
      return data.items
    },
    retry: false,
  })

  if (conversations.isError) {
    const status =
      conversations.error instanceof AxiosError ? conversations.error.response?.status : undefined
    return (
      <div className="space-y-6">
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
          <h1 className="text-3xl font-bold tracking-tight">Conversations</h1>
        </div>
        {status === 403 ? (
          <AdminAccessCard resource="conversations" />
        ) : (
          <p className="text-destructive text-sm">Failed to load conversations.</p>
        )}
      </div>
    )
  }

  const items = conversations.data ?? []

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
          <MessageSquare className="size-7" /> Conversations
        </h1>
        <p className="text-muted-foreground mt-1">
          Every chat thread across the platform and its owner.
        </p>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>All conversations</CardTitle>
          <CardDescription>{items.length} chat threads.</CardDescription>
        </CardHeader>
        <CardContent>
          {conversations.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-xl" />
              ))}
            </div>
          ) : items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead className="text-right">Messages</TableHead>
                  <TableHead>Last activity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((conversation) => (
                  <TableRow key={conversation.id}>
                    <TableCell>
                      <span className="block max-w-96 truncate font-medium">
                        {conversation.title || 'New conversation'}
                      </span>
                      <span className="text-muted-foreground block text-xs">
                        {conversation.document_id ? `Document ${conversation.document_id}` : 'General chat'}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {conversation.owner_email}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-right">
                      {conversation.message_count}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(conversation.updated_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground py-4 text-sm">
              No conversations have been started yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}