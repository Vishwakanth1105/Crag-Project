import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { useState } from 'react'
import { LifeBuoy, Send, CheckCircle2, Plus } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

type TicketStatus = 'open' | 'pending' | 'resolved'

interface SupportMessage {
  id: number
  sender_id: number
  sender_role: string
  content: string
  created_at: string
}

interface SupportThread {
  id: number
  subject: string
  status: TicketStatus
  user_email?: string
  messages: SupportMessage[]
}

function statusBadge(status: TicketStatus) {
  if (status === 'open') return <Badge variant="warning">Open</Badge>
  if (status === 'pending') return <Badge variant="default">Pending</Badge>
  return <Badge variant="success">Resolved</Badge>
}

const statusFilters: TicketStatus[] = ['open', 'pending', 'resolved']

export function Support() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const queryClient = useQueryClient()

  const [activeThread, setActiveThread] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<TicketStatus>('open')
  const [reply, setReply] = useState('')
  const [newSubject, setNewSubject] = useState('')
  const [newMessage, setNewMessage] = useState('')

  const threadsQuery = useQuery({
    queryKey: ['support-threads', isAdmin, statusFilter],
    queryFn: async () => {
      const path = isAdmin
        ? `/support/admin/threads?status=${statusFilter}`
        : '/support/mine'
      const { data } = await api.get<{ items: SupportThread[] }>(path)
      return data.items
    },
    refetchInterval: 5000,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['support-threads'] })
  }

  const onError = (err: unknown) => {
    const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
    toast.error(typeof detail === 'string' ? detail : 'Action failed.')
  }

  const replyMutation = useMutation({
    mutationFn: async ({ id, content }: { id: number; content: string }) => {
      await api.post(`/support/${id}/messages`, { content })
    },
    onSuccess: () => {
      setReply('')
      invalidate()
    },
    onError,
  })

  const resolveMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.patch(`/support/admin/${id}/status`, { status: 'resolved' })
    },
    onSuccess: () => {
      toast.success('Ticket resolved')
      invalidate()
    },
    onError,
  })

  const reopenMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.patch(`/support/admin/${id}/status`, { status: 'open' })
    },
    onSuccess: () => {
      toast.success('Ticket reopened')
      invalidate()
    },
    onError,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      await api.post('/support', { subject: newSubject, message: newMessage })
    },
    onSuccess: () => {
      toast.success('Support ticket created')
      setNewSubject('')
      setNewMessage('')
      invalidate()
    },
    onError,
  })

  const threads = threadsQuery.data ?? []
  const current = threads.find((thread) => thread.id === activeThread) ?? null

  return (
    <div className="space-y-8">
      <div>
        <p className="text-muted-foreground mb-1 text-sm font-medium">
          {isAdmin ? 'Admin' : 'Help'}
        </p>
        <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
          <LifeBuoy className="size-7" /> {isAdmin ? 'Support inbox' : 'Support'}
        </h1>
        <p className="text-muted-foreground mt-1">
          {isAdmin
            ? 'Review tickets from users, respond, and resolve them.'
            : 'Stuck on something? Open a ticket and our team will help.'}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <Card className="shadow-card h-fit">
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle>{isAdmin ? 'Tickets' : 'Your tickets'}</CardTitle>
              {!isAdmin && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setActiveThread(null)}
                  className={cn(activeThread === null && 'bg-accent')}
                >
                  <Plus /> New
                </Button>
              )}
            </div>
            {isAdmin && (
              <div className="flex gap-1 pt-1">
                {statusFilters.map((status) => (
                  <button
                    key={status}
                    type="button"
                    onClick={() => setStatusFilter(status)}
                    className={cn(
                      'rounded-full px-3 py-1 text-xs capitalize transition-colors',
                      statusFilter === status
                        ? 'bg-card shadow-sm font-medium'
                        : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {status}
                  </button>
                ))}
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            {threadsQuery.isLoading ? (
              [0, 1].map((i) => <Skeleton key={i} className="h-14 w-full rounded-xl" />)
            ) : threads.length === 0 ? (
              <p className="text-muted-foreground py-4 text-sm">
                No {isAdmin ? `${statusFilter} ` : ''}tickets.
              </p>
            ) : (
              threads.map((thread) => (
                <button
                  key={thread.id}
                  type="button"
                  onClick={() => setActiveThread(thread.id)}
                  className={cn(
                    'w-full rounded-xl border p-3 text-left transition-colors',
                    activeThread === thread.id
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-accent/50',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">{thread.subject}</span>
                    {statusBadge(thread.status)}
                  </div>
                  <span className="text-muted-foreground mt-1 block truncate text-xs">
                    {isAdmin ? thread.user_email : `#${thread.id}`} ·{' '}
                    {thread.messages.length} messages
                  </span>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="shadow-card">
          {!isAdmin && activeThread === null ? (
            <>
              <CardHeader>
                <CardTitle>Open a new ticket</CardTitle>
                <CardDescription>Describe the problem in as much detail as you can.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  placeholder="Subject (e.g. Document upload fails)"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                />
                <Textarea
                  rows={6}
                  placeholder="What happened? What did you expect instead?"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                />
                <Button
                  disabled={
                    createMutation.isPending ||
                    newSubject.trim().length < 4 ||
                    newMessage.trim().length < 10
                  }
                  onClick={() => createMutation.mutate()}
                >
                  <Send /> Submit ticket
                </Button>
              </CardContent>
            </>
          ) : current ? (
            <>
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <CardTitle>{current.subject}</CardTitle>
                    <CardDescription>
                      {current.user_email ?? `Ticket #${current.id}`}
                    </CardDescription>
                  </div>
                  {isAdmin && (
                    <div className="space-x-2">
                      {current.status !== 'resolved' ? (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={resolveMutation.isPending}
                          onClick={() => resolveMutation.mutate(current.id)}
                        >
                          <CheckCircle2 /> Resolve
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={reopenMutation.isPending}
                          onClick={() => reopenMutation.mutate(current.id)}
                        >
                          Reopen
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
                  {current.messages.map((message) => {
                    const mine = isAdmin
                      ? message.sender_role === 'admin'
                      : message.sender_role === 'user'
                    return (
                      <div
                        key={message.id}
                        className={cn('flex', mine ? 'justify-end' : 'justify-start')}
                      >
                        <div
                          className={cn(
                            'max-w-[75%] rounded-2xl px-4 py-2.5 text-sm',
                            mine
                              ? 'rounded-br-md bg-primary text-primary-foreground'
                              : 'bg-muted rounded-bl-md',
                          )}
                        >
                          <p className={cn('mb-0.5 text-xs opacity-70')}>
                            {message.sender_role === 'admin' ? 'Support team' : 'User'} ·{' '}
                            {new Date(message.created_at).toLocaleString()}
                          </p>
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
                <div className="flex gap-2 border-t pt-4">
                  <Textarea
                    rows={2}
                    placeholder={
                      current.status === 'resolved' && !isAdmin
                        ? 'Sending a reply reopens the ticket…'
                        : 'Write a reply…'
                    }
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                  />
                  <Button
                    size="icon"
                    className="size-10 shrink-0 self-end"
                    disabled={
                      reply.trim().length === 0 || replyMutation.isPending
                    }
                    onClick={() => replyMutation.mutate({ id: current.id, content: reply })}
                  >
                    <Send />
                  </Button>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setActiveThread(null)}>
                  ← Back to list
                </Button>
              </CardContent>
            </>
          ) : (
            <CardContent className="py-16 text-center">
              <p className="text-muted-foreground text-sm">Select a ticket to view it.</p>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  )
}
