import { API_BASE } from '../api/config'

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  timestamp: string
  level: LogLevel
  message: string
  component?: string
  context?: string
  error?: string
  stack?: string
}

const LOG_LEVELS: Record<LogLevel, number> = { debug: 0, info: 1, warn: 2, error: 3 }
const MAX_BUFFER = 500
const FLUSH_INTERVAL_MS = 5000
const STORAGE_KEY = 'lazy_learn_logs'

let buffer: LogEntry[] = []
let flushTimer: ReturnType<typeof setInterval> | null = null
const minLevel: LogLevel = import.meta.env.DEV ? 'debug' : 'info'

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[minLevel]
}

function createEntry(
  level: LogLevel,
  message: string,
  opts?: { component?: string; context?: string; error?: Error },
): LogEntry {
  return {
    timestamp: new Date().toISOString(),
    level,
    message,
    component: opts?.component,
    context: opts?.context,
    error: opts?.error?.message,
    stack: opts?.error?.stack,
  }
}

function persistToStorage(entry: LogEntry): void {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as LogEntry[]
    stored.push(entry)
    if (stored.length > MAX_BUFFER) stored.splice(0, stored.length - MAX_BUFFER)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored))
  } catch {
    // localStorage full or unavailable — skip silently
  }
}

function writeToConsole(entry: LogEntry): void {
  const tag = entry.component ? `[${entry.component}]` : ''
  const msg = `${tag} ${entry.message}`
  switch (entry.level) {
    case 'debug': console.debug(msg); break
    case 'info': console.info(msg); break
    case 'warn': console.warn(msg); break
    case 'error': console.error(msg, entry.error || ''); break
  }
}

async function flushToBackend(): Promise<void> {
  if (buffer.length === 0) return
  const batch = buffer.splice(0, buffer.length)
  try {
    await fetch(`${API_BASE}/logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entries: batch.map((e) => ({
          level: e.level,
          message: e.message,
          component: e.component,
          context: e.context,
          error: e.error,
          stack: e.stack,
          timestamp: e.timestamp,
        })),
      }),
    })
  } catch {
    // Backend unreachable — logs are still in localStorage
  }
}

function startFlushTimer(): void {
  if (flushTimer) return
  flushTimer = setInterval(() => { void flushToBackend() }, FLUSH_INTERVAL_MS)
}

function log(
  level: LogLevel,
  message: string,
  opts?: { component?: string; context?: string; error?: Error },
): void {
  if (!shouldLog(level)) return
  const entry = createEntry(level, message, opts)
  writeToConsole(entry)
  persistToStorage(entry)
  buffer.push(entry)
  startFlushTimer()
}

export const logger = {
  debug: (msg: string, opts?: { component?: string; context?: string }) =>
    log('debug', msg, opts),
  info: (msg: string, opts?: { component?: string; context?: string }) =>
    log('info', msg, opts),
  warn: (msg: string, opts?: { component?: string; context?: string; error?: Error }) =>
    log('warn', msg, opts),
  error: (msg: string, opts?: { component?: string; context?: string; error?: Error }) =>
    log('error', msg, opts),
  flush: flushToBackend,
  getLogs: (): LogEntry[] => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as LogEntry[]
    } catch {
      return []
    }
  },
  clearLogs: (): void => {
    localStorage.removeItem(STORAGE_KEY)
    buffer = []
  },
}
