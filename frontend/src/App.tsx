import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './styles/theme.css'
import 'katex/dist/katex.min.css'
import './App.css'
import { BookshelfPage } from './pages/BookshelfPage'
import { DeskPage } from './pages/DeskPage'

function App() {
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
