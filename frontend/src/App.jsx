import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import Navbar from './components/Navbar'
import JobSearch from './pages/JobSearch'
import Applications from './pages/Applications'
import ResumeTailor from './pages/ResumeTailor'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex min-h-screen bg-[#030712]">
          <Navbar />
          <main className="flex-1 ml-64 p-8">
            <Routes>
              <Route path="/" element={<Navigate to="/jobs" replace />} />
              <Route path="/jobs" element={<JobSearch />} />
              <Route path="/applications" element={<Applications />} />
              <Route path="/resume" element={<ResumeTailor />} />
            </Routes>
          </main>
        </div>
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
    </QueryClientProvider>
  )
}

export default App