import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { useState } from 'react'
import { ShieldAlert, ShieldCheck, Trash2, Ban, RotateCcw, Users as UsersIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface AdminUserRow {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

interface AdminUserDetail extends AdminUserRow {
  document_count: number
  conversation_count: number
  message_count: number
  query_log_count: number
  recent_conversations: { id: number; title: string; message_count: number }[]
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function Users() {
  const { user: me } = useAuth()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<AdminUserRow | null>(null)

  const usersQuery = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const { data } = await api.get<{ items: AdminUserRow[] }>('/admin/users')
      return data.items
    },
    retry: false,
  })

  const detailQuery = useQuery({
    queryKey: ['admin-user-detail', selectedId],
    enabled: selectedId !== null,
    queryFn: async () => {
      const { data } = await api.get<AdminUserDetail>(`/admin/users/${selectedId}`)
      return data
    },
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    void queryClient.invalidateQueries({ queryKey: ['admin-user-detail'] })
  }

  const statusMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      await api.patch(`/admin/users/${id}/status`, { is_active })
    },
    onSuccess: (_data, variables) => {
      toast.success(variables.is_active ? 'User unbanned' : 'User banned')
      invalidate()
      setDeleteTarget(null)
    },
    onError: (err) => {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(typeof detail === 'string' ? detail : 'Action failed.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/admin/users/${id}`)
    },
    onSuccess: () => {
      toast.success('User and all their data deleted')
      setSelectedId(null)
      setDeleteTarget(null)
      invalidate()
    },
    onError: (err) => {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(typeof detail === 'string' ? detail : 'Delete failed.')
    },
  })

  if (usersQuery.isError) {
    return (
      <div className="space-y-6">
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
          <h1 className="text-3xl font-bold tracking-tight">Users</h1>
        </div>
        <Card className="shadow-card">
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <span className="bg-warning/15 text-warning-foreground flex size-14 items-center justify-center rounded-2xl">
              <ShieldAlert className="size-7" />
            </span>
            <div>
              <p className="font-semibold">Administrator access required</p>
              <p className="text-muted-foreground mt-1 text-sm">
                Sign in with an admin account to manage users.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const users = usersQuery.data ?? []

  return (
    <div className="space-y-8">
      <div>
        <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
        <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
          <UsersIcon className="size-7" /> User management
        </h1>
        <p className="text-muted-foreground mt-1">
          Inspect accounts, review activity, ban abusive users, or remove them entirely.
        </p>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>All users</CardTitle>
          <CardDescription>{users.length} registered accounts.</CardDescription>
        </CardHeader>
        <CardContent>
          {usersQuery.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-xl" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((row) => {
                  const isSelf = me?.id === row.id
                  const isAdminRow = row.role === 'admin'
                  return (
                    <TableRow key={row.id}>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => setSelectedId(row.id)}
                          className="hover:text-primary cursor-pointer text-left"
                        >
                          <span className="block font-medium">
                            {row.full_name || 'Unnamed user'}
                          </span>
                          <span className="text-muted-foreground block text-xs">
                            {row.email}
                          </span>
                        </button>
                      </TableCell>
                      <TableCell>
                        {isAdminRow ? (
                          <Badge variant="default">Admin</Badge>
                        ) : (
                          <Badge variant="secondary">User</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {row.is_active ? (
                          <Badge variant="success">Active</Badge>
                        ) : (
                          <Badge variant="destructive">Banned</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(row.created_at)}
                      </TableCell>
                      <TableCell className="space-x-2 text-right whitespace-nowrap">
                        {!isSelf && !isAdminRow && (
                          <>
                            {row.is_active ? (
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={statusMutation.isPending}
                                onClick={() =>
                                  statusMutation.mutate({ id: row.id, is_active: false })
                                }
                              >
                                <Ban /> Ban
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={statusMutation.isPending}
                                onClick={() =>
                                  statusMutation.mutate({ id: row.id, is_active: true })
                                }
                              >
                                <RotateCcw /> Unban
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={deleteMutation.isPending}
                              onClick={() => setDeleteTarget(row)}
                            >
                              <Trash2 /> Delete
                            </Button>
                          </>
                        )}
                        {(isSelf || isAdminRow) && (
                          <span className="text-muted-foreground text-xs">
                            {isSelf ? 'This is you' : 'Protected'}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {selectedId !== null && (
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>User activity</CardTitle>
            {detailQuery.data ? (
              <CardDescription>
                {detailQuery.data.full_name || detailQuery.data.email} · joined{' '}
                {formatDate(detailQuery.data.created_at)}
              </CardDescription>
            ) : null}
          </CardHeader>
          <CardContent>
            {detailQuery.isLoading ? (
              <div className="grid gap-4 sm:grid-cols-4">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 rounded-xl" />
                ))}
              </div>
            ) : detailQuery.data ? (
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-4">
                  {[
                    ['Documents', detailQuery.data.document_count],
                    ['Conversations', detailQuery.data.conversation_count],
                    ['Messages', detailQuery.data.message_count],
                    ['Queries', detailQuery.data.query_log_count],
                  ].map(([label, count]) => (
                    <div key={label} className="rounded-xl border p-4 text-center">
                      <p className="text-muted-foreground text-sm">{label}</p>
                      <p className="mt-1 text-2xl font-bold tracking-tight">{count}</p>
                    </div>
                  ))}
                </div>
                <div>
                  <p className="mb-3 text-sm font-medium">Recent conversations</p>
                  {detailQuery.data.recent_conversations.length ? (
                    <div className="space-y-2">
                      {detailQuery.data.recent_conversations.map((conversation) => (
                        <div
                          key={conversation.id}
                          className="flex items-center justify-between rounded-xl border px-4 py-2.5 text-sm"
                        >
                          <span className="truncate font-medium">{conversation.title}</span>
                          <span className="text-muted-foreground shrink-0">
                            {conversation.message_count} messages
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-sm">
                      This user has not started any conversations yet.
                    </p>
                  )}
                </div>
                <Button variant="outline" onClick={() => setSelectedId(null)}>
                  Close details
                </Button>
              </div>
            ) : (
              <p className="text-destructive text-sm">Failed to load user details.</p>
            )}
          </CardContent>
        </Card>
      )}

      {deleteTarget && (
        <div className="bg-black/50 fixed inset-0 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md shadow-card-hover">
            <CardHeader>
              <CardTitle>Delete this user?</CardTitle>
              <CardDescription>
                {deleteTarget.full_name || deleteTarget.email} and all their documents,
                conversations, uploads, and vector indexes will be permanently removed.
                This cannot be undone.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
              >
                <Trash2 /> Delete permanently
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
        <ShieldCheck className="size-3.5" />
        Admins cannot be modified by other admins. Deleting a user also cleans their
        MinIO blobs, Qdrant chunks, and Neo4j graph nodes.
      </div>
    </div>
  )
}
