import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { Mail, Lock, User } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
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
    fullName: z.string().max(255),
    email: z.string().email('Enter a valid email'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm: z.string(),
  })
  .refine((data) => data.password === data.confirm, {
    path: ['confirm'],
    message: 'Passwords do not match',
  })

type FormValues = z.infer<typeof schema>

export function Register() {
  const { register: registerUser } = useAuth()
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    try {
      await registerUser(values.email, values.password, values.fullName)
      toast.success('Account created — welcome aboard')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : undefined
      toast.error(
        typeof detail === 'string' ? detail : 'Registration failed. Try a different email.',
      )
    }
  }

  return (
    <AuthShell>
      <Card className="shadow-card-hover">
        <CardHeader>
          <CardTitle className="text-2xl">Create your account</CardTitle>
          <CardDescription>Start asking your documents questions.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName">Full name</Label>
              <div className="relative">
                <User className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
                <Input
                  id="fullName"
                  autoComplete="name"
                  className="pl-9"
                  placeholder="Ada Lovelace"
                  {...register('fullName')}
                />
              </div>
              {errors.fullName && (
                <p className="text-destructive text-sm">{errors.fullName.message}</p>
              )}
            </div>
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
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  className="pl-9"
                  placeholder="At least 8 characters"
                  {...register('password')}
                />
              </div>
              {errors.password && (
                <p className="text-destructive text-sm">{errors.password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">Confirm password</Label>
              <div className="relative">
                <Lock className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
                <Input
                  id="confirm"
                  type="password"
                  autoComplete="new-password"
                  className="pl-9"
                  placeholder="Repeat your password"
                  {...register('confirm')}
                />
              </div>
              {errors.confirm && (
                <p className="text-destructive text-sm">{errors.confirm.message}</p>
              )}
            </div>
            <Button
              type="submit"
              className="w-full shadow-lg shadow-indigo-600/25"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating account…' : 'Create account'}
            </Button>
          </form>
          <p className="text-muted-foreground mt-5 text-center text-sm">
            Already registered?{' '}
            <Link to="/login" className="text-primary font-medium underline-offset-4 hover:underline">
              Log in
            </Link>
          </p>
        </CardContent>
      </Card>
    </AuthShell>
  )
}