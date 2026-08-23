import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  FileText,
  MessageSquare,
  ArrowRight,
  Upload,
  FileCheck2,
  Clock,
} from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn, formatDate } from '@/lib/utils'
import type { Conversation, DocumentRecord } from '@/lib/types'

const statusVariant: Record<string, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
  ready: 'success',
  pending: 'warning',
  queued: 'warning',
  running: 'warning',
  failed: 'destructive',
  deleted: 'outline',
}

export function Dashboard() {
  const { user } = useAuth()

  const documents = useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      const { data } = await api.get<{ items: DocumentRecord[] }>('/documents')
      return data.items
    },
  })

  const conversations = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      const { data } = await api.get<{ items: Conversation[] }>('/conversations')
      return data.items
    },
  })

  const loading = documents.isLoading || conversations.isLoading
  const docCount = documents.data?.length ?? 0
  const convoCount = conversations.data?.length ?? 0

  const stats = [
    {
      label: 'Documents',
      value: docCount,
      icon: FileText,
      to: '/documents',
      accent: 'from-indigo-500 to-violet-600 shadow-indigo-500/30',
    },
    {
      label: 'Conversations',
      value: convoCount,
      icon: MessageSquare,
      to: '/chat',
      accent: 'from-fuchsia-500 to-pink-600 shadow-fuchsia-500/30',
    },
    {
      label: 'Documents ready to query',
      value: documents.data?.filter((d) => d.status === 'ready').length ?? 0,
      icon: FileCheck2,
      to: '/documents',
      accent: 'from-emerald-500 to-teal-600 shadow-emerald-500/30',
    },
  ]

  const recent = documents.data?.slice(0, 5) ?? []

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
            Welcome back,{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              {user?.full_name?.split(' ')[0] || user?.email}
            </span>
          </h1>
        </div>
        <div className="flex gap-2">
          <Link to="/documents">
            <Button className="shadow-lg shadow-indigo-600/25">
              <Upload className="size-4" /> Upload
            </Button>
          </Link>
          <Link to="/chat">
            <Button variant="outline" className="gap-2">
              Ask a question <ArrowRight className="size-4" />
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map(({ label, value, icon: Icon, to, accent }) => (
          <Link
            key={label}
            to={to}
            className="shadow-card hover:shadow-card-hover group rounded-2xl border bg-card p-5 transition-all duration-300 hover:-translate-y-0.5"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-muted-foreground text-sm">{label}</p>
                {loading ? (
                  <Skeleton className="mt-2 h-8 w-16" />
                ) : (
                  <p className="mt-1 text-3xl font-bold tracking-tight">{value ?? 0}</p>
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

      <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Quick actions</h2>
          <div className="grid gap-3">
            <Link
              to="/documents"
              className="shadow-card group flex items-center gap-4 rounded-2xl border bg-card p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover"
            >
              <span className="bg-accent text-accent-foreground group-hover:bg-primary group-hover:text-primary-foreground flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors">
                <Upload className="size-5" />
              </span>
              <div className="flex-1">
                <p className="font-semibold">Upload a document</p>
                <p className="text-muted-foreground text-sm">
                  Add PDFs, text, or markdown to your knowledge base
                </p>
              </div>
              <ArrowRight className="text-muted-foreground group-hover:text-foreground size-4 transition-colors" />
            </Link>
            <Link
              to="/chat"
              className="shadow-card group flex items-center gap-4 rounded-2xl border bg-card p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover"
            >
              <span className="bg-accent text-accent-foreground group-hover:bg-primary group-hover:text-primary-foreground flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors">
                <MessageSquare className="size-5" />
              </span>
              <div className="flex-1">
                <p className="font-semibold">Start a conversation</p>
                <p className="text-muted-foreground text-sm">
                  Ask anything about your indexed documents
                </p>
              </div>
              <ArrowRight className="text-muted-foreground group-hover:text-foreground size-4 transition-colors" />
            </Link>
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Recent documents</h2>
          <div className="shadow-card rounded-2xl border bg-card">
            {documents.isLoading ? (
              <div className="space-y-3 p-5">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="size-10 rounded-xl" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-3 w-1/4" />
                    </div>
                  </div>
                ))}
              </div>
            ) : recent.length > 0 ? (
              <ul className="divide-y">
                {recent.map((document) => (
                  <li
                    key={document.id}
                    className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-muted/50"
                  >
                    <span className="bg-accent/60 text-accent-foreground flex size-10 shrink-0 items-center justify-center rounded-xl">
                      <FileText className="size-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{document.file_name}</p>
                      <p className="text-muted-foreground flex items-center gap-1 text-xs">
                        <Clock className="size-3" /> {formatDate(document.created_at)}
                      </p>
                    </div>
                    <Badge variant={statusVariant[document.status] ?? 'outline'}>
                      {document.status}
                    </Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
                <span className="bg-muted text-muted-foreground flex size-12 items-center justify-center rounded-2xl">
                  <FileText className="size-6" />
                </span>
                <div>
                  <p className="font-medium">No documents yet</p>
                  <p className="text-muted-foreground text-sm">
                    Upload your first file to start asking questions.
                  </p>
                </div>
                <Link to="/documents">
                  <Button size="sm">Upload a document</Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}