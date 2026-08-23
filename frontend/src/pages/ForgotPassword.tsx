import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { Mail } from 'lucide-react'
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

const schema = z.object({
  email: z.string().email('Enter a valid email'),
})

type FormValues = z.infer<typeof schema>

export function ForgotPassword() {
  const [sent, setSent] = useState(false)
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    try {
      await api.post('/auth/forgot-password', { email: values.email })
      setSent(true)
    } catch (err) {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(typeof detail === 'string' ? detail : 'Something went wrong.')
    }
  }

  return (
    <AuthShell>
      <Card className="shadow-card-hover">
        <CardHeader>
          <CardTitle className="text-2xl">Reset your password</CardTitle>
          <CardDescription>
            Enter your email and we&apos;ll send you a reset link.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="space-y-4">
              <p className="text-muted-foreground text-sm">
                If an account exists for{' '}
                <span className="text-foreground font-medium">{getValues('email')}</span>,
                a reset link is on its way. The link expires in 60 minutes.
              </p>
              <Button asChild variant="outline" className="w-full">
                <Link to="/login">Back to login</Link>
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    className="pl-9"
                    placeholder="you@example.com"
                    {...register('email')}
                  />
                </div>
                {errors.email && (
                  <p className="text-destructive text-sm">{errors.email.message}</p>
                )}
              </div>
              <Button
                type="submit"
                className="w-full shadow-lg shadow-indigo-600/25"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Sending…' : 'Send reset link'}
              </Button>
              <p className="text-muted-foreground text-center text-sm">
                Remembered it?{' '}
                <Link to="/login" className="text-primary font-medium underline-offset-4 hover:underline">
                  Log in
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </AuthShell>
  )
}
