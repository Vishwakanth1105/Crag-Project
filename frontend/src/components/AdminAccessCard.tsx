import { ShieldAlert } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function AdminAccessCard({ resource }: { resource: string }) {
  return (
    <Card className="shadow-card">
      <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
        <span className="bg-warning/15 text-warning-foreground flex size-14 items-center justify-center rounded-2xl">
          <ShieldAlert className="size-7" />
        </span>
        <div>
          <p className="font-semibold">Administrator access required</p>
          <p className="text-muted-foreground mt-1 text-sm">
            Sign in with an admin account to view {resource}.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}