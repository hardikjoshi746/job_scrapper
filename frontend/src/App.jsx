import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import JobSearch from './pages/JobSearch'
import Applications from './pages/Applications'
import ResumeTailor from './pages/ResumeTailor'
import CustomJob from './pages/CustomJob'
import Login from './pages/Login'
import Register from './pages/Register'

const queryClient = new QueryClient()

function ProtectedRoute({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return children
}

function AppLayout() {
  const { user } = useAuth()

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <div className="flex min-h-screen bg-[#030712]">
      <Navbar />
      <main className="flex-1 ml-64 p-8">
        <Routes>
          <Route path="/" element={<Navigate to="/jobs" replace />} />
          <Route path="/jobs" element={<ProtectedRoute><JobSearch /></ProtectedRoute>} />
          <Route path="/applications" element={<ProtectedRoute><Applications /></ProtectedRoute>} />
          <Route path="/resume" element={<ProtectedRoute><ResumeTailor /></ProtectedRoute>} />
          <Route path="/custom-job" element={<ProtectedRoute><CustomJob /></ProtectedRoute>} />
          <Route path="/login" element={<Navigate to="/jobs" replace />} />
          <Route path="/register" element={<Navigate to="/jobs" replace />} />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppLayout />
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: 'rgba(15, 15, 25, 0.9)',
                color: '#f8fafc',
                border: '1px solid rgba(167, 139, 250, 0.2)',
                backdropFilter: 'blur(12px)',
              },
            }}
          />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
