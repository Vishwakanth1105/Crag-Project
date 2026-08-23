import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  GitBranch,
  Globe2,
  MessageSquare,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  User,
  CheckCircle2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/Layout'

const features = [
  {
    icon: GitBranch,
    title: 'Hybrid retrieval',
    description:
      'Combines Qdrant vector search with a Neo4j knowledge graph for answers that draw on both semantic and structural context.',
  },
  {
    icon: Search,
    title: 'Self-correcting RAG',
    description:
      'Grades every retrieved chunk, rewrites weak queries, and falls back to web search when your documents fall short.',
  },
  {
    icon: ShieldCheck,
    title: 'Secure by default',
    description:
      'Argon2 password hashing, database-backed sessions, and CSRF protection built into every request.',
  },
  {
    icon: Bot,
    title: 'Cited, grounded answers',
    description:
      'Every response ships with a confidence score, web-search provenance, and traceable reasoning steps.',
  },
]

const steps = [
  {
    icon: Upload,
    step: '01',
    title: 'Upload your documents',
    description: 'Drop in PDFs, text files, or markdown. A background worker parses, embeds, and indexes them.',
  },
  {
    icon: GitBranch,
    step: '02',
    title: 'We build your graph',
    description: 'Chunks land in Qdrant while entities and relationships are extracted into a Neo4j knowledge graph.',
  },
  {
    icon: MessageSquare,
    step: '03',
    title: 'Ask anything',
    description: 'Chat with your knowledge base and get grounded, cited answers with confidence scoring.',
  },
]

const stats = [
  { value: 'Hybrid', label: 'vector + graph retrieval' },
  { value: '3-way', label: 'relevance grading with correction' },
  { value: 'Multi-user', label: 'sessions, roles, and CSRF' },
]

export function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div
        className="bg-grid pointer-events-none absolute inset-0 -z-10 opacity-[0.35]"
        style={{
          backgroundImage:
            'linear-gradient(to right, oklch(0.6 0.1 264 / 0.07) 1px, transparent 1px), linear-gradient(to bottom, oklch(0.6 0.1 264 / 0.07) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px] bg-[radial-gradient(ellipse_at_top,oklch(0.85_0.07_264/0.45),transparent_70%)]" />

      <header className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <div className="flex items-center gap-2">
          <Link to="/login">
            <Button variant="ghost" className="text-muted-foreground">
              Log in
            </Button>
          </Link>
          <Link to="/register">
            <Button className="shadow-lg shadow-indigo-600/25">
              Get started <ArrowRight className="size-4" />
            </Button>
          </Link>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-6xl flex-col items-center px-4 pt-20 pb-16 text-center sm:px-6 sm:pt-28">
        <div className="animate-fade-in-up">
          <span className="bg-accent text-accent-foreground border-border inline-flex items-center gap-2 rounded-full border px-3.5 py-1 text-xs font-medium">
            <Sparkles className="size-3.5" /> Corrective RAG · Agentic RAG · LangGraph
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold tracking-tight text-balance sm:text-6xl">
            Ask questions your documents{' '}
            <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 bg-clip-text text-transparent">
              actually answer
            </span>
          </h1>
          <p className="text-muted-foreground mx-auto mt-6 max-w-xl text-lg text-pretty">
            Upload your knowledge base and get cited, grounded answers from a
            self-correcting retrieval pipeline that never trusts a bad retrieval
            twice.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to="/register" className="w-full sm:w-auto">
              <Button size="lg" className="w-full gap-2 shadow-lg shadow-indigo-600/25 sm:w-auto">
                Create your account <ArrowRight className="size-4" />
              </Button>
            </Link>
            <Link to="/login" className="w-full sm:w-auto">
              <Button size="lg" variant="outline" className="w-full sm:w-auto">
                Log in to continue
              </Button>
            </Link>
          </div>
        </div>

        <div className="animate-fade-in-up mt-16 w-full [animation-delay:120ms]">
          <div className="border-border bg-card/80 shadow-card-hover relative mx-auto max-w-5xl rounded-2xl border p-2 backdrop-blur-sm">
            <div className="flex items-center justify-between px-3 py-2.5">
              <div className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-rose-400" />
                <span className="size-2.5 rounded-full bg-amber-400" />
                <span className="size-2.5 rounded-full bg-emerald-400" />
              </div>
              <span className="text-muted-foreground hidden items-center gap-2 text-xs sm:flex">
                <MessageSquare className="size-3.5" /> chat — ask anything about your
                documents
              </span>
            </div>
            <div className="bg-muted/40 flex flex-col gap-4 rounded-xl p-4 text-left sm:p-6">
              <div className="flex items-start justify-end gap-3">
                <div className="bg-primary text-primary-foreground max-w-[80%] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm shadow-md shadow-indigo-600/20 sm:max-w-[70%]">
                  What are the key benefits of the hybrid retrieval approach in this
                  system?
                </div>
                <span className="bg-gradient-to-br from-indigo-600 to-violet-600 flex size-8 shrink-0 items-center justify-center rounded-full">
                  <User className="size-4 text-white" />
                </span>
              </div>
              <div className="flex items-start gap-3">
                <span className="bg-accent text-accent-foreground flex size-8 shrink-0 items-center justify-center rounded-full">
                  <Bot className="size-4" />
                </span>
                <div className="bg-card border-border shadow-sm max-w-[80%] rounded-2xl rounded-tl-sm border px-4 py-3 text-sm sm:max-w-[75%]">
                  <p className="text-pretty">
                    The system combines semantic search over vector embeddings with
                    structural traversal over a knowledge graph, so answers surface both
                    related passages and the relationships between them.
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className="text-success inline-flex items-center gap-1 text-xs font-medium">
                      <CheckCircle2 className="size-3.5" /> Confidence 0.91
                    </span>
                    <span className="bg-accent text-accent-foreground inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs">
                      <Globe2 className="size-3" /> Web search used
                    </span>
                    <span className="text-muted-foreground text-xs">3 sources cited</span>
                  </div>
                </div>
              </div>
              <div className="border-border bg-card/70 mt-1 flex items-center gap-2 rounded-full border px-4 py-2.5">
                <span className="text-muted-foreground text-sm">
                  Ask anything about your documents…
                </span>
                <span className="bg-primary ml-auto flex size-7 shrink-0 items-center justify-center rounded-full">
                  <ArrowRight className="size-3.5 text-white" />
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y bg-card/60">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-6 px-4 py-10 sm:grid-cols-3 sm:px-6">
          {stats.map(({ value, label }) => (
            <div key={value} className="text-center">
              <p className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-2xl font-bold text-transparent">
                {value}
              </p>
              <p className="text-muted-foreground text-sm">{label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-balance">
            Everything you need to talk to your knowledge base
          </h2>
          <p className="text-muted-foreground mt-3">
            A production-grade retrieval pipeline wrapped in a clean, multi-user
            workspace.
          </p>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="shadow-card hover:shadow-card-hover group rounded-2xl border bg-card p-6 transition-all duration-300 hover:-translate-y-1"
            >
              <span className="bg-accent text-accent-foreground group-hover:bg-primary group-hover:text-primary-foreground mb-4 inline-flex size-11 items-center justify-center rounded-xl transition-colors">
                <Icon className="size-5" />
              </span>
              <h3 className="mb-1.5 font-semibold">{title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-y bg-card/60">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-balance">
              From upload to answer in three steps
            </h2>
          </div>
          <div className="mt-12 grid gap-5 sm:grid-cols-3">
            {steps.map(({ icon: Icon, step, title, description }) => (
              <div key={step} className="shadow-card relative rounded-2xl border bg-card p-6">
                <span className="text-muted-foreground/25 absolute top-5 right-6 text-4xl font-bold">
                  {step}
                </span>
                <span className="bg-primary/10 text-primary mb-4 inline-flex size-11 items-center justify-center rounded-xl">
                  <Icon className="size-5" />
                </span>
                <h3 className="mb-1.5 font-semibold">{title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
        <div className="bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-600 relative overflow-hidden rounded-3xl px-6 py-14 text-center text-white sm:px-12">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgb(255_255_255/0.25),transparent_60%)]" />
          <h2 className="relative text-3xl font-bold tracking-tight text-balance sm:text-4xl">
            Ready to talk to your documents?
          </h2>
          <p className="relative mx-auto mt-3 max-w-lg text-white/80 text-pretty">
            Create an account in seconds, upload your first file, and start asking
            questions.
          </p>
          <div className="relative mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to="/register" className="w-full sm:w-auto">
              <Button size="lg" className="w-full bg-white text-indigo-700 shadow-xl hover:bg-white/90 sm:w-auto">
                Get started free
              </Button>
            </Link>
            <Link to="/login" className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="ghost"
                className="w-full text-white hover:bg-white/15 hover:text-white sm:w-auto"
              >
                Log in
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t bg-card/60">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-3 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:px-6">
          <Logo />
          <p>
            © {new Date().getFullYear()} Agentic RAG · LangGraph · Qdrant ·
            Neo4j
          </p>
        </div>
      </footer>
    </div>
  )
}