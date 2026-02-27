import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import './styles/theme.css'
import 'katex/dist/katex.min.css'
import './App.css'
import { BookshelfPage } from './pages/BookshelfPage'
import { DeskPage } from './pages/DeskPage'
import SplashScreen from './components/SplashScreen'

function App() {
  const [backendReady, setBackendReady] = useState(false)

  if (!backendReady) {
    return <SplashScreen onReady={() => setBackendReady(true)} />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<BookshelfPage />} />
        <Route path="/desk/:textbookId" element={<DeskPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
