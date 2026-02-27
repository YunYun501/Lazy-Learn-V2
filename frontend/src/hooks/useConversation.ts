import { useState, useCallback } from 'react'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface ConversationState {
  messages: Message[]
  loading: boolean
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void
}

let messageCounter = 0

function makeId() {
  return `msg_${++messageCounter}_${Date.now()}`
}

export function useConversation(
  onSend?: (query: string) => Promise<string>
): ConversationState {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return

      const userMsg: Message = {
        id: makeId(),
        role: 'user',
        content,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, userMsg])
      setLoading(true)

      try {
        const response = onSend ? await onSend(content) : '(No AI handler configured)'
        const assistantMsg: Message = {
          id: makeId(),
          role: 'assistant',
          content: response,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, assistantMsg])
      } catch (err) {
        const errorMsg: Message = {
          id: makeId(),
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, errorMsg])
      } finally {
        setLoading(false)
      }
    },
    [onSend]
  )

  const clearMessages = useCallback(() => setMessages([]), [])

  return { messages, loading, sendMessage, clearMessages }
}
