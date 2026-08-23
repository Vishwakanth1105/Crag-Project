import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { KeyRound } from 'lucide-react'
import { api } from '@/lib/api'
import { AuthShell } from '@/components/AuthShell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

const schema = z
  .object({
    password: z.string().min(8, 'At least 8 characters'),
    confirm: z.string(),
  })
  .refine((values) => values.password === values.confirm, {
    message: 'Passwords do not match',
    path: ['confirm'],
  })

type FormValues = z.infer<typeof schema>

export function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    if (!token) {
      toast.error('This reset link is missing its token. Request a new one.')
      return
    }
    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: values.password,
      })
      toast.success('Password updated. Please log in with your new password.')
      navigate('/login', { replace: true })
    } catch (err) {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(
        typeof detail === 'string' ? detail : 'Reset failed. The link may have expired.'
      )
    }
  }

  if (!token) {
    return (
      <AuthShell>
        <Card className="shadow-card-hover">
          <CardHeader>
            <CardTitle className="text-2xl">Invalid reset link</CardTitle>
            <CardDescription>
              This link is missing its token. Request a fresh one below.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline" className="w-full">
              <Link to="/forgot-password">Request new link</Link>
            </Button>
          </CardContent>
        </Card>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <Card className="shadow-card-hover">
        <CardHeader>
          <CardTitle className="text-2xl">Choose a new password</CardTitle>
          <CardDescription>Your new password must be at least 8 characters.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">New password</Label>
              <div className="relative">
                <KeyRound className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  className="pl-9"
                  placeholder="••••••••"
                  {...register('password')}
                />
              </div>
              {errors.password && (
                <p className="text-destructive text-sm">{errors.password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                placeholder="••••••••"
                {...register('confirm')}
              />
              {errors.confirm && (
                <p className="text-destructive text-sm">{errors.confirm.message}</p>
              )}
            </div>
            <Button
              type="submit"
              className="w-full shadow-lg shadow-indigo-600/25"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Updating…' : 'Update password'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </AuthShell>
  )
}
