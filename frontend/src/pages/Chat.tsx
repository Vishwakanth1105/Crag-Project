import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import {
  Plus,
  Send,
  MessageSquare,
  Trash2,
  Bot,
  User,
  Globe2,
  Sparkles,
  FileText,
  PanelRightClose,
  PanelRightOpen,
  X,
  Highlighter,
  Cpu,
} from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn, formatDate } from '@/lib/utils'
import { buildRanges, splitIntoSegments } from '@/lib/highlight'
import type {
  Conversation,
  DocumentContent,
  DocumentRecord,
  Message,
  ModelsInfo,
} from '@/lib/types'

function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      const { data } = await api.get<{ items: Conversation[] }>('/conversations')
      return data.items
    },
  })
}

function useMessages(conversationId: number | null) {
  return useQuery({
    queryKey: ['messages', conversationId],
    enabled: conversationId !== null,
    queryFn: async () => {
      const { data } = await api.get<{ items: Message[] }>(
        `/conversations/${conversationId}/messages`,
      )
      return data.items
    },
  })
}

const statusMeta: Record<string, { label: string; variant: 'success' | 'warning' | 'destructive' | 'outline' }> = {
  ready: { label: 'Ready', variant: 'success' },
  pending: { label: 'Pending', variant: 'warning' },
  queued: { label: 'Queued', variant: 'warning' },
  running: { label: 'Indexing', variant: 'warning' },
  failed: { label: 'Failed', variant: 'destructive' },
}

export function Chat() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const documentParam = searchParams.get('document')
  const conversations = useConversations()
  const [activeId, setActiveId] = useState<number | null>(null)
  const [draft, setDraft] = useState('')
  const [viewerOpen, setViewerOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Open the pinned-document viewer when arriving via /chat?document=<id>.
  useEffect(() => {
    if (documentParam) setViewerOpen(true)
  }, [documentParam])

  const pinnedDocument = useQuery({
    queryKey: ['documents', documentParam],
    enabled: Boolean(documentParam),
    queryFn: async () => {
      try {
        const { data } = await api.get<DocumentRecord>(`/documents/${documentParam}`)
        return data
      } catch {
        toast.error('That document is no longer available')
        setSearchParams({}, { replace: true })
        return null
      }
    },
  })

  const documentContent = useQuery({
    queryKey: ['documents', documentParam, 'content'],
    enabled: Boolean(documentParam) && pinnedDocument.data?.status === 'ready',
    queryFn: async () => {
      const { data } = await api.get<DocumentContent>(`/documents/${documentParam}/content`)
      return data
    },
  })

  const modelsInfo = useQuery({
    queryKey: ['models-info'],
    queryFn: async () => {
      const { data } = await api.get<ModelsInfo>('/info/models')
      return data
    },
  })

  const messages = useMessages(activeId)
  const messageList = messages.data ?? []
  const activeConversation = conversations.data?.find((c) => c.id === activeId)
  const lastAssistantMessage = [...messageList].reverse().find((m) => m.role === 'assistant')

  // Highlight passages of the pinned document that grounded the latest answer.
  const highlightRanges = useMemo(() => {
    const text = documentContent.data?.text
    if (!text || !lastAssistantMessage) return []
    const snippets = lastAssistantMessage.retrieval_evidence
      .filter((ev) => ev.document_id === documentParam && ev.retrieval_source !== 'graph')
      .map((ev) => ev.text)
    return buildRanges(text, snippets)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentContent.data?.text, lastAssistantMessage?.id, documentParam])

  useEffect(() => {
    if (conversations.data && activeId === null && conversations.data.length > 0) {
      setActiveId(conversations.data[0].id)
    }
  }, [conversations.data, activeId])

  const createConversation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<Conversation>('/conversations', {})
      return data
    },
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setActiveId(conversation.id)
    },
  })

  const deleteConversation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/conversations/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      if (activeId !== null) {
        queryClient.invalidateQueries({ queryKey: ['messages', activeId] })
      }
      setActiveId(null)
      toast.success('Conversation deleted')
    },
  })

  const sendMessage = useMutation({
    mutationFn: async (content: string) => {
      const { data } = await api.post<Message>(
        `/conversations/${activeId}/messages`,
        { content },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', activeId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
    onError: (err) => {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(typeof detail === 'string' ? detail : 'Message failed to send')
    },
  })

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content || sendMessage.isPending || activeId === null) return
    setDraft('')
    sendMessage.mutate(content)
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messageList.length, sendMessage.isPending])

  return (
    <div
      className={cn(
        'grid h-[calc(100vh-9.5rem)] min-h-[480px] gap-4',
        documentParam && viewerOpen
          ? 'lg:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[220px_minmax(0,1fr)_380px]'
          : 'lg:grid-cols-[280px_minmax(0,1fr)]',
      )}
    >
      <aside className="hidden flex-col rounded-2xl border bg-card p-3 shadow-card lg:flex">
        <Button
          className="mb-3 w-full justify-start gap-2 shadow-lg shadow-indigo-600/25"
          onClick={() => createConversation.mutate()}
          disabled={createConversation.isPending}
        >
          <Plus className="size-4" /> New conversation
        </Button>
        <div className="flex flex-1 flex-col gap-1 overflow-y-auto">
          {conversations.isLoading ? (
            <div className="space-y-2 p-1">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-10 w-full rounded-lg" />
              ))}
            </div>
          ) : conversations.data?.length ? (
            conversations.data.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  'group flex items-center gap-2 rounded-xl px-2 py-2 text-sm transition-colors',
                  activeId === conversation.id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'hover:bg-accent',
                )}
              >
                <button
                  type="button"
                  onClick={() => setActiveId(conversation.id)}
                  className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
                >
                  <MessageSquare className="size-4 shrink-0" />
                  <span className="truncate">{conversation.title}</span>
                </button>
                <button
                  type="button"
                  onClick={() => deleteConversation.mutate(conversation.id)}
                  aria-label="Delete conversation"
                  className="text-muted-foreground hover:text-destructive shrink-0 rounded-md p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-destructive/10"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            ))
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
              <span className="bg-muted text-muted-foreground flex size-10 items-center justify-center rounded-xl">
                <MessageSquare className="size-5" />
              </span>
              <p className="text-muted-foreground text-sm">
                No conversations yet. Start a new one to begin.
              </p>
            </div>
          )}
        </div>
      </aside>

      <section className="flex flex-col overflow-hidden rounded-2xl border bg-card shadow-card">
        <header className="flex items-center justify-between gap-3 border-b px-5 py-3">
          <div className="flex items-center gap-2.5">
            <span className="bg-accent text-accent-foreground flex size-8 items-center justify-center rounded-lg">
              <MessageSquare className="size-4" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">
                {activeConversation?.title ?? 'Conversation'}
              </p>
              <p className="text-muted-foreground flex items-center gap-1 text-xs">
                <span className="bg-emerald-500 size-1.5 rounded-full" />
                {sendMessage.isPending ? 'Thinking…' : 'Ready to answer'}
              </p>
            </div>
          </div>
          {documentParam && (
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-foreground gap-2"
              onClick={() => setViewerOpen((open) => !open)}
            >
              {viewerOpen ? <PanelRightClose className="size-4" /> : <PanelRightOpen className="size-4" />}
              <span className="hidden sm:inline">{viewerOpen ? 'Hide document' : 'View document'}</span>
            </Button>
          )}
          {modelsInfo.data && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-muted-foreground hover:text-foreground gap-2"
                >
                  <Cpu className="size-4" />
                  <span className="hidden max-w-[140px] truncate md:inline">
                    {modelsInfo.data.chat.generation_model}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                <DropdownMenuLabel>Chat models ({modelsInfo.data.chat.provider === 'local' ? 'local' : modelsInfo.data.chat.provider})</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="justify-between gap-4">
                  <span className="text-muted-foreground">Answers</span>
                  <code className="text-xs">{modelsInfo.data.chat.generation_model}</code>
                </DropdownMenuItem>
                <DropdownMenuItem className="justify-between gap-4">
                  <span className="text-muted-foreground">Embeddings</span>
                  <code className="max-w-[150px] truncate text-xs">{modelsInfo.data.chat.embedding_model}</code>
                </DropdownMenuItem>
                <DropdownMenuItem className="justify-between gap-4">
                  <span className="text-muted-foreground">Rerank</span>
                  <code className="max-w-[150px] truncate text-xs">{modelsInfo.data.chat.rerank_model}</code>
                </DropdownMenuItem>
                <DropdownMenuItem className="justify-between gap-4">
                  <span className="text-muted-foreground">Grading</span>
                  <code className="text-xs">{modelsInfo.data.chat.grader_model}</code>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          {activeId !== null && (
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-destructive gap-2"
              onClick={() => deleteConversation.mutate(activeId)}
            >
              <Trash2 className="size-4" /> <span className="hidden sm:inline">Delete</span>
            </Button>
          )}
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-6">
          {activeId === null ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <span className="bg-gradient-to-br from-indigo-600 to-violet-600 flex size-14 items-center justify-center rounded-2xl shadow-lg shadow-indigo-600/25">
                <Sparkles className="size-7 text-white" />
              </span>
              <div>
                <p className="font-semibold">Ask your documents anything</p>
                <p className="text-muted-foreground mt-1 max-w-xs text-sm">
                  Select a conversation from the list, or start a new one to begin.
                </p>
              </div>
              <Button
                className="mt-2 shadow-lg shadow-indigo-600/25"
                onClick={() => createConversation.mutate()}
                disabled={createConversation.isPending}
              >
                <Plus className="size-4" /> New conversation
              </Button>
            </div>
          ) : messageList.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <span className="bg-accent text-accent-foreground mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl">
                  <Bot className="size-6" />
                </span>
                <p className="text-muted-foreground text-sm">
                  Ask a question about your uploaded documents.
                </p>
              </div>
            </div>
          ) : (
            messageList.map((message) => (
              <div
                key={message.id}
                className={cn('flex items-start gap-3', message.role === 'user' && 'flex-row-reverse')}
              >
                <span
                  className={cn(
                    'flex size-8 shrink-0 items-center justify-center rounded-full',
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-indigo-600 to-violet-600 text-white'
                      : 'bg-accent text-accent-foreground',
                  )}
                >
                  {message.role === 'user' ? <User className="size-4" /> : <Bot className="size-4" />}
                </span>
                <div
                  className={cn(
                    'flex max-w-[75%] flex-col gap-1.5',
                    message.role === 'user' && 'items-end',
                  )}
                >
                  <div
                    className={cn(
                      'rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap',
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground rounded-tr-sm shadow-md shadow-indigo-600/20'
                        : 'bg-muted/70 rounded-tl-sm',
                    )}
                  >
                    {message.content}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 px-1">
                    <span className="text-muted-foreground text-xs">
                      {formatDate(message.created_at)}
                    </span>
                    {message.role === 'assistant' &&
                      message.confidence_score !== null && (
                        <span
                          className={cn(
                            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                            message.confidence_score >= 0.7
                              ? 'text-success bg-success/10'
                              : message.confidence_score >= 0.4
                                ? 'bg-warning/15 text-warning-foreground'
                                : 'text-destructive bg-destructive/10',
                          )}
                        >
                          Confidence {(message.confidence_score * 100).toFixed(0)}%
                        </span>
                      )}
                    {message.role === 'assistant' && message.web_search_used && (
                      <span className="text-muted-foreground inline-flex items-center gap-1 text-xs">
                        <Globe2 className="size-3" /> web search used
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          {sendMessage.isPending && (
            <div className="flex items-start gap-3">
              <span className="bg-accent text-accent-foreground flex size-8 shrink-0 items-center justify-center rounded-full">
                <Bot className="size-4" />
              </span>
              <div className="bg-muted/70 flex items-center gap-1.5 rounded-2xl rounded-tl-sm px-4 py-3.5">
                <span className="bg-muted-foreground/50 size-2 animate-bounce rounded-full [animation-delay:0ms]" />
                <span className="bg-muted-foreground/50 size-2 animate-bounce rounded-full [animation-delay:150ms]" />
                <span className="bg-muted-foreground/50 size-2 animate-bounce rounded-full [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <Separator />
        <form onSubmit={onSubmit} className="flex items-end gap-2 p-3">
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask about your documents…"
            className="min-h-12 max-h-40 flex-1 resize-none rounded-xl"
            rows={1}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onSubmit(event as unknown as React.FormEvent)
              }
            }}
          />
          <Button
            type="submit"
            size="icon"
            className="size-12 shrink-0 rounded-xl shadow-lg shadow-indigo-600/25"
            disabled={sendMessage.isPending || activeId === null || !draft.trim()}
            aria-label="Send message"
          >
            <Send className="size-4" />
          </Button>
        </form>
      </section>

      {pinnedDocument.data && viewerOpen && (
        <>
          <aside className="hidden flex-col overflow-hidden rounded-2xl border bg-card shadow-card xl:flex">
            <DocumentViewer
              document={pinnedDocument.data}
              content={documentContent.data?.text ?? null}
              contentLoading={documentContent.isLoading}
              highlightCount={highlightRanges.length}
              ranges={highlightRanges}
              onClose={() => setViewerOpen(false)}
            />
          </aside>
          <div className="fixed inset-0 z-50 bg-black/40 xl:hidden" onClick={() => setViewerOpen(false)} />
          <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l bg-card shadow-2xl xl:hidden">
            <DocumentViewer
              document={pinnedDocument.data}
              content={documentContent.data?.text ?? null}
              contentLoading={documentContent.isLoading}
              highlightCount={highlightRanges.length}
              ranges={highlightRanges}
              onClose={() => setViewerOpen(false)}
            />
          </aside>
        </>
      )}
    </div>
  )
}

interface DocumentViewerProps {
  document: DocumentRecord
  content: string | null
  contentLoading: boolean
  highlightCount: number
  ranges: { start: number; end: number }[]
  onClose: () => void
}

function DocumentViewer({ document, content, contentLoading, highlightCount, ranges, onClose }: DocumentViewerProps) {
  const meta = statusMeta[document.status] ?? { label: document.status, variant: 'outline' as const }
  const segments = useMemo(
    () => (content ? splitIntoSegments(content, ranges) : []),
    [content, ranges],
  )

  return (
    <>
      <header className="flex items-start justify-between gap-3 border-b px-5 py-3">
        <div className="flex min-w-0 items-start gap-2.5">
          <span className="bg-accent text-accent-foreground mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg">
            <FileText className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{document.file_name}</p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <Badge variant={meta.variant} className="px-2 py-0 text-xs capitalize">
                {meta.label}
              </Badge>
              {highlightCount > 0 && (
                <span className="text-muted-foreground inline-flex items-center gap-1 text-xs">
                  <Highlighter className="size-3 text-amber-500" />
                  {highlightCount} retrieved passage{highlightCount === 1 ? '' : 's'}
                </span>
              )}
            </div>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground -mr-2 size-7 shrink-0"
          onClick={onClose}
          aria-label="Close document viewer"
        >
          <X className="size-4" />
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {contentLoading ? (
          <div className="space-y-3">
            {[...Array(8)].map((_, i) => (
              <Skeleton key={i} className={cn('h-3', i % 3 === 2 ? 'w-2/3' : 'w-full')} />
            ))}
          </div>
        ) : content ? (
          <>
            {highlightCount > 0 && (
              <p className="text-muted-foreground mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-relaxed">
                Highlighted passages were retrieved from this document to answer your latest
                question.
              </p>
            )}
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {segments.map((segment, index) =>
                segment.highlighted ? (
                  <mark key={index} className="bg-amber-200/80 text-inherit rounded-sm px-0.5">
                    {segment.value}
                  </mark>
                ) : (
                  segment.value
                ),
              )}
            </p>
          </>
        ) : (
          <div className="text-muted-foreground space-y-2 py-10 text-center text-sm">
            <FileText className="mx-auto mb-2 size-6 opacity-50" />
            No preview available for this document yet.
          </div>
        )}
      </div>
    </>
  )
}