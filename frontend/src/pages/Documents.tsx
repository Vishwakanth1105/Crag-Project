import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  Cpu,
  FileText,
  MessageSquare,
  Trash2,
  UploadCloud,
  Upload,
  Loader2,
  FileUp,
} from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn, formatBytes, formatDate } from '@/lib/utils'
import type { DocumentRecord, ModelsInfo } from '@/lib/types'

type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'

const statusMeta: Record<string, { label: string; variant: BadgeVariant; pulse?: boolean }> = {
  ready: { label: 'Ready', variant: 'success' },
  pending: { label: 'Pending', variant: 'warning', pulse: true },
  queued: { label: 'Queued', variant: 'warning', pulse: true },
  running: { label: 'Indexing', variant: 'warning', pulse: true },
  failed: { label: 'Failed', variant: 'destructive' },
  deleted: { label: 'Deleted', variant: 'outline' },
}

const ACTIVE_STATUSES = new Set(['pending', 'queued', 'running'])

export function Documents() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const documents = useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      const { data } = await api.get<{ items: DocumentRecord[] }>('/documents')
      return data.items
    },
    // Poll while any document is still being ingested; stop when all settle.
    refetchInterval: (query) =>
      query.state.data?.some((doc) => ACTIVE_STATUSES.has(doc.status)) ? 5000 : false,
  })

  const modelsInfo = useQuery({
    queryKey: ['models-info'],
    queryFn: async () => {
      const { data } = await api.get<ModelsInfo>('/info/models')
      return data
    },
  })

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post<DocumentRecord>('/documents/upload', form)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Document uploaded — indexing started')
    },
    onError: (err) => {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(typeof detail === 'string' ? detail : 'Upload failed')
    },
  })

  const remove = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/documents/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Document deleted')
    },
    onError: (err) => {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(typeof detail === 'string' ? detail : 'Delete failed')
    },
  })

  const onFiles = (files: FileList | null) => {
    const file = files?.[0]
    if (file) upload.mutate(file)
  }

  const onDrop = (event: React.DragEvent) => {
    event.preventDefault()
    setDragOver(false)
    onFiles(event.dataTransfer.files)
  }

  const isBusy = upload.isPending || remove.isPending

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-medium">Knowledge base</p>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
        </div>
        <span className="text-muted-foreground hidden text-sm sm:block">
          {documents.data?.length ?? 0} file{documents.data?.length === 1 ? '' : 's'}
        </span>
      </div>

      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') fileInputRef.current?.click()
        }}
        className={cn(
          'group relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-all',
          dragOver
            ? 'border-primary bg-primary/5 shadow-card-hover'
            : 'hover:shadow-card border-muted-foreground/25 hover:border-primary/60',
        )}
      >
        <span
          className={cn(
            'bg-accent text-accent-foreground group-hover:bg-primary group-hover:text-primary-foreground flex size-14 items-center justify-center rounded-2xl shadow-lg transition-all group-hover:shadow-primary/30',
            dragOver && 'bg-primary text-primary-foreground',
          )}
        >
          {upload.isPending ? (
            <Loader2 className="size-6 animate-spin" />
          ) : dragOver ? (
            <FileUp className="size-6" />
          ) : (
            <UploadCloud className="size-6" />
          )}
        </span>
        <div>
          <p className="font-medium">
            {upload.isPending
              ? 'Uploading…'
              : 'Drop a file here, or click to browse'}
          </p>
          <p className="text-muted-foreground mt-1 text-sm">
            PDF, TXT, or Markdown · up to 20 MB
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          className="hidden"
          onChange={(event) => onFiles(event.target.files)}
        />
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your documents</h2>
          {documents.data && documents.data.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="size-4" /> Upload
            </Button>
          )}
        </div>

        <Card className="shadow-card">
          <CardContent className="p-0">
            {documents.isLoading ? (
              <div className="space-y-3 p-5">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton className="size-10 rounded-xl" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-1/3" />
                      <Skeleton className="h-3 w-1/5" />
                    </div>
                  </div>
                ))}
              </div>
            ) : documents.data?.length ? (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="pl-5">Name</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden md:table-cell">Uploaded</TableHead>
                    <TableHead className="pr-5 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.data.map((document) => {
                    const meta = statusMeta[document.status] ?? {
                      label: document.status,
                      variant: 'outline' as const,
                    }
                    const canChat = document.status === 'ready'
                    return (
                      <TableRow
                        key={document.id}
                        className={cn('group hover:bg-muted/40', canChat && 'cursor-pointer')}
                        onClick={() => {
                          if (canChat) navigate(`/chat?document=${document.id}`)
                        }}
                      >
                        <TableCell className="max-w-[260px] pl-5">
                          <div className="flex items-center gap-3">
                            <span className="bg-accent/60 text-accent-foreground flex size-10 shrink-0 items-center justify-center rounded-xl">
                              <FileText className="size-5" />
                            </span>
                            <div className="min-w-0">
                              <p className="truncate font-medium">{document.file_name}</p>
                              <p className="text-muted-foreground text-xs">
                                {document.content_type || '—'}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatBytes(document.size_bytes)}
                        </TableCell>
                        <TableCell>
                          <Badge variant={meta.variant} className={cn(meta.pulse && 'animate-pulse')}>
                            {meta.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground hidden md:table-cell">
                          {formatDate(document.created_at)}
                        </TableCell>
                        <TableCell className="pr-5 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {canChat && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-muted-foreground hover:text-primary gap-1.5 opacity-0 transition-opacity group-hover:opacity-100"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  navigate(`/chat?document=${document.id}`)
                                }}
                              >
                                <MessageSquare className="size-3.5" /> Ask
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={(event) => {
                                event.stopPropagation()
                                remove.mutate(document.id)
                              }}
                              disabled={isBusy}
                              aria-label={`Delete ${document.file_name}`}
                              className="text-muted-foreground hover:text-destructive opacity-0 transition-opacity group-hover:opacity-100"
                            >
                              <Trash2 className="size-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            ) : (
              <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
                <span className="bg-muted text-muted-foreground flex size-12 items-center justify-center rounded-2xl">
                  <FileText className="size-6" />
                </span>
                <div>
                  <p className="font-medium">Your library is empty</p>
                  <p className="text-muted-foreground text-sm">
                    Upload your first document above to start building your knowledge base.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {modelsInfo.data && (
          <Card className="shadow-card">
            <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-3 p-5">
              <div className="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                <Cpu className="size-4" /> Indexing pipeline
              </div>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <span className="text-muted-foreground">
                  Extraction{' '}
                  <code className="bg-accent/60 text-accent-foreground ml-1 rounded-md px-1.5 py-0.5 text-xs">
                    {modelsInfo.data.ingestion.extraction_model}
                  </code>
                </span>
                <span className="text-muted-foreground">
                  Embeddings{' '}
                  <code className="bg-accent/60 text-accent-foreground ml-1 rounded-md px-1.5 py-0.5 text-xs">
                    {modelsInfo.data.ingestion.embedding_model}
                  </code>
                </span>
                <Badge variant="secondary" className="capitalize">
                  {modelsInfo.data.ingestion.provider === 'local' ? 'runs locally' : modelsInfo.data.ingestion.provider}
                </Badge>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}