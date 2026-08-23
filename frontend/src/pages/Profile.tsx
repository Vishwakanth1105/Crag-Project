import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { CalendarDays, LogOut, Mail, Shield, User as UserIcon, CheckCircle2 } from 'lucide-react'
import { formatDate } from '@/lib/utils'

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function Profile() {
  const { user, logout } = useAuth()

  if (!user) return null

  const details = [
    { icon: Mail, label: 'Email', value: user.email },
    { icon: UserIcon, label: 'Full name', value: user.full_name || '—' },
    {
      icon: Shield,
      label: 'Role',
      value: (
        <Badge variant={user.role === 'admin' ? 'default' : 'secondary'} className="capitalize">
          {user.role}
        </Badge>
      ),
    },
    {
      icon: CheckCircle2,
      label: 'Account status',
      value: (
        <span className="flex items-center gap-1.5">
          <span className="bg-emerald-500 size-1.5 rounded-full" />
          {user.is_active ? 'Active' : 'Disabled'}
        </span>
      ),
    },
    { icon: CalendarDays, label: 'Member since', value: formatDate(user.created_at) },
  ]

  return (
    <div className="space-y-8">
      <div>
        <p className="text-muted-foreground mb-1 text-sm font-medium">Account</p>
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <Card className="shadow-card h-fit">
          <CardContent className="flex flex-col items-center gap-4 px-6 py-8 text-center">
            <Avatar className="size-20">
              <AvatarFallback className="text-lg">{initials(user.full_name || user.email)}</AvatarFallback>
            </Avatar>
            <div>
              <p className="text-lg font-semibold">{user.full_name || 'User'}</p>
              <p className="text-muted-foreground text-sm">{user.email}</p>
            </div>
            <Badge variant={user.role === 'admin' ? 'default' : 'secondary'} className="capitalize">
              {user.role}
            </Badge>
            <Button variant="outline" className="w-full gap-2" onClick={() => void logout()}>
              <LogOut className="size-4" /> Log out
            </Button>
          </CardContent>
        </Card>

        <Card className="shadow-card h-fit">
          <CardHeader>
            <CardTitle>Account details</CardTitle>
            <CardDescription>Information about your account on this instance.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            {details.map(({ icon: Icon, label, value }) => (
              <div
                key={label}
                className="flex items-center justify-between gap-4 rounded-xl px-3 py-3 transition-colors hover:bg-muted/50"
              >
                <span className="text-muted-foreground flex items-center gap-2.5 text-sm">
                  <Icon className="size-4" /> {label}
                </span>
                <span className="text-right text-sm font-medium">{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}