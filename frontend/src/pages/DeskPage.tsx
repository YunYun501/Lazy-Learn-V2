import React, { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PixelButton, PixelInput, PixelPanel, PixelBadge } from '../components/pixel'
import { ContentRenderer } from '../components/ContentRenderer'
import { useConversation } from '../hooks/useConversation'
import { usePanelLayout } from '../hooks/usePanelLayout'
import { usePinnedItems } from '../hooks/usePinnedItems'
import '../styles/desk.css'

const QUICK_ACTIONS = [
  { label: 'EXPLAIN', prefix: 'Explain ' },
  { label: 'DERIVE', prefix: 'Derive step by step: ' },
  { label: 'EXAMPLE', prefix: 'Show me a worked example of ' },
]

export function DeskPage() {
  const { textbookId } = useParams<{ textbookId: string }>()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  const conversationIdRef = useRef<string>(crypto.randomUUID())

  async function handleAiSend(query: string): Promise<string> {
    const res = await fetch('http://127.0.0.1:8000/api/conversations/followup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: conversationIdRef.current, message: query }),
    })
    if (!res.ok) throw new Error(`Chat failed: ${res.status}`)

    // Collect SSE stream into a full string
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let fullText = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ') && line.trim() !== 'data: [DONE]') {
          fullText += line.slice(6)
        }
      }
    }
    return fullText
  }

  const { messages, loading, sendMessage } = useConversation(handleAiSend)
  const { panelA, panelB, merged, swapPanels, toggleMerge } = usePanelLayout()
  const { pinnedImages, pinnedFormulas, recentConcepts, pinImage, unpinImage } = usePinnedItems()

  // ESC key: go back to bookshelf
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        navigate('/')
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [navigate])

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatEndRef.current && typeof chatEndRef.current.scrollIntoView === 'function') { chatEndRef.current.scrollIntoView({ behavior: 'auto' }) }
  }, [messages])

  function handleSend() {
    if (!query.trim()) return
    sendMessage(query)
    setQuery('')
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleQuickAction(prefix: string) {
    const topic = recentConcepts[0] ?? 'this topic'
    setQuery(prefix + topic)
  }

  function handleGenerateQA() {
    const topic = recentConcepts[0] ?? 'the current topic'
    sendMessage(`Generate practice questions and solutions for: ${topic}`)
  }

  return (
    <div className="desk-page" data-testid="desk-page">
      {/* ── Left column: Input + Chat (15%) ── */}
      <aside className="desk-col desk-col--input" data-testid="input-column">
        <div className="desk-back">
          <PixelButton variant="secondary" onClick={() => navigate('/')}>
            ← BACK
          </PixelButton>
        </div>

        <div className="desk-quick-actions">
          {QUICK_ACTIONS.map(action => (
            <PixelButton
              key={action.label}
              variant="secondary"
              onClick={() => handleQuickAction(action.prefix)}
              className="desk-quick-btn"
            >
              {action.label}
            </PixelButton>
          ))}
          <PixelButton
            variant="primary"
            onClick={handleGenerateQA}
            className="desk-qa-btn"
          >
            GENERATE Q&amp;A
          </PixelButton>
        </div>

        <div className="desk-chat" data-testid="chat-history">
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`chat-bubble chat-bubble--${msg.role}`}
              data-testid={`chat-bubble-${msg.role}`}
            >
              <ContentRenderer content={msg.content} />
            </div>
          ))}
          {loading && (
            <div className="chat-bubble chat-bubble--assistant chat-bubble--loading">
              <span className="loading-dots">···</span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="desk-input-area">
          <PixelInput
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question…"
            multiline
            rows={3}
          />
          <PixelButton onClick={handleSend} disabled={loading || !query.trim()}>
            SEND
          </PixelButton>
        </div>
      </aside>

      {/* ── Panel A (35%) ── */}
      <main
        className={`desk-col desk-col--panel-a ${merged ? 'desk-col--merged' : ''}`}
        data-testid="panel-a"
      >
        <div className="panel-header">
          <span className="panel-label">
            {panelA.type === 'ai' ? 'AI EXPLANATION' : 'TEXTBOOK'}
          </span>
          <div className="panel-controls">
            <PixelButton variant="secondary" onClick={swapPanels} className="panel-swap-btn">
              ⇄ SWAP
            </PixelButton>
            <PixelButton variant="secondary" onClick={toggleMerge} className="panel-merge-btn">
              {merged ? 'SPLIT' : 'MERGE'}
            </PixelButton>
          </div>
        </div>
        <PixelPanel className="panel-content">
          {messages.length === 0 ? (
            <p className="panel-placeholder">AI explanations will appear here.</p>
          ) : (
            <ContentRenderer
              content={messages.filter(m => m.role === 'assistant').slice(-1)[0]?.content ?? ''}
            />
          )}
        </PixelPanel>
      </main>

      {/* ── Panel B (35%) — hidden when merged ── */}
      {!merged && (
        <section className="desk-col desk-col--panel-b" data-testid="panel-b">
          <div className="panel-header">
            <span className="panel-label">
              {panelB.type === 'textbook' ? 'TEXTBOOK' : 'AI EXPLANATION'}
            </span>
          </div>
          <PixelPanel className="panel-content">
            <p className="panel-placeholder">
              Textbook content for <strong>{textbookId}</strong> will appear here.
            </p>
          </PixelPanel>
        </section>
      )}

      {/* ── Quick Ref (15%) ── */}
      <aside className="desk-col desk-col--quick-ref" data-testid="quick-ref">
        <h3 className="quick-ref-title">QUICK REF</h3>

        {recentConcepts.length > 0 && (
          <div className="quick-ref-section">
            <h4 className="quick-ref-label">RECENT</h4>
            {recentConcepts.slice(0, 5).map(concept => (
              <PixelBadge key={concept} type="USES" className="quick-ref-concept">
                {concept}
              </PixelBadge>
            ))}
          </div>
        )}

        {pinnedImages.length > 0 && (
          <div className="quick-ref-section">
            <h4 className="quick-ref-label">PINNED</h4>
            {pinnedImages.map(img => (
              <div key={img.id} className="pinned-image-thumb">
                <img src={img.src} alt={img.alt} />
                <button
                  className="pinned-image-remove"
                  onClick={() => unpinImage(img.id)}
                  title="Unpin"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {pinnedFormulas.length === 0 && pinnedImages.length === 0 && recentConcepts.length === 0 && (
          <p className="quick-ref-empty">
            Pin formulas and images here for quick reference.
          </p>
        )}
      </aside>
    </div>
  )
}

export default DeskPage
