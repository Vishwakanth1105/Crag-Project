import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled render error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center p-6">
          <div className="shadow-card-hover w-full max-w-lg rounded-2xl border bg-card p-8 text-center">
            <p className="text-destructive mb-2 text-sm font-semibold uppercase tracking-wide">
              Something went wrong
            </p>
            <h1 className="mb-3 text-xl font-bold tracking-tight">This page crashed</h1>
            <p className="bg-muted text-muted-foreground mb-6 overflow-auto rounded-xl p-3 text-left font-mono text-xs break-words">
              {this.state.error.message}
            </p>
            <div className="flex justify-center gap-2">
              <button
                type="button"
                onClick={() => this.setState({ error: null })}
                className="bg-primary text-primary-foreground shadow hover:bg-primary/90 inline-flex h-9 items-center rounded-md px-4 text-sm font-medium transition-colors"
              >
                Try again
              </button>
              <button
                type="button"
                onClick={() => window.location.assign('/dashboard')}
                className="border-input bg-background hover:bg-accent inline-flex h-9 items-center rounded-md border px-4 text-sm font-medium transition-colors"
              >
                Back to dashboard
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
