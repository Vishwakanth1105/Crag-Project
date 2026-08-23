import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import { AuthProvider } from '@/context/AuthContext'
import { GuestRoute, ProtectedRoute } from '@/components/Routes'
import { Layout } from '@/components/Layout'
import { Home } from '@/pages/Home'
import { Login } from '@/pages/Login'
import { Register } from '@/pages/Register'
import { ForgotPassword } from '@/pages/ForgotPassword'
import { ResetPassword } from '@/pages/ResetPassword'
import { Dashboard } from '@/pages/Dashboard'
import { Chat } from '@/pages/Chat'
import { Documents } from '@/pages/Documents'
import { System } from '@/pages/System'
import { Users } from '@/pages/Users'
import { Support } from '@/pages/Support'
import { Profile } from '@/pages/Profile'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />

          <Route element={<GuestRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/support" element={<Support />} />
              <Route path="/system" element={<System />} />
              <Route path="/users" element={<Users />} />
              <Route path="/profile" element={<Profile />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors closeButton />
    </AuthProvider>
  )
}