import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { Link } from 'react-router-dom'
import { ArrowLeft, FileText } from 'lucide-react'
import { api } from '@/lib/api'
import { AdminAccessCard } from '@/components/AdminAccessCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatBytes, formatDate } from '@/lib/utils'
import type { AdminDocument } from '@/lib/types'

type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'

const statusMeta: Record<string, { label: string; variant: BadgeVariant }> = {
  ready: { label: 'Ready', variant: 'success' },
  pending: { label: 'Pending', variant: 'warning' },
  queued: { label: 'Queued', variant: 'warning' },
  running: { label: 'Indexing', variant: 'warning' },
  failed: { label: 'Failed', variant: 'destructive' },
  deleted: { label: 'Deleted', variant: 'outline' },
}

export function SystemDocuments() {
  const documents = useQuery({
    queryKey: ['admin-documents'],
    queryFn: async () => {
      const { data } = await api.get<{ items: AdminDocument[] }>('/admin/documents')
      return data.items
    },
    retry: false,
  })

  if (documents.isError) {
    const status = documents.error instanceof AxiosError ? documents.error.response?.status : undefined
    return (
      <div className="space-y-6">
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-medium">Admin</p>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
        </div>
        {status === 403 ? (
          <AdminAccessCard resource="documents" />
        ) : (
          <p className="text-destructive text-sm">Failed to load documents.</p>
        )}
      </div>
    )
  }

  const items = documents.data ?? []

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
          <FileText className="size-7" /> Documents
        </h1>
        <p className="text-muted-foreground mt-1">Every upload on the platform and its owner.</p>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>All documents</CardTitle>
          <CardDescription>{items.length} uploaded files.</CardDescription>
        </CardHeader>
        <CardContent>
          {documents.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full rounded-xl" />
              ))}
            </div>
          ) : items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Uploaded</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((document) => {
                  const meta = statusMeta[document.status] ?? {
                    label: document.status,
                    variant: 'secondary',
                  }
                  return (
                    <TableRow key={document.id}>
                      <TableCell>
                        <span className="block max-w-72 truncate font-medium">
                          {document.file_name}
                        </span>
                        <span className="text-muted-foreground block text-xs">
                          {document.id}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {document.owner_email}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {document.content_type}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-right">
                        {formatBytes(document.size_bytes)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={meta.variant}>{meta.label}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(document.created_at)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground py-4 text-sm">
              No documents have been uploaded yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}