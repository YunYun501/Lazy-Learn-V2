import { useEffect, useState } from 'react'

interface SplashScreenProps {
  onReady: () => void
}

const HEALTH_URL = 'http://localhost:8000/health'
const POLL_INTERVAL = 500
const TIMEOUT_SECONDS = 8

// Pixel art book: each sub-array is a row, 1 = filled, 0 = empty
// Rendered via box-shadow cascade on a 6px base pixel
const PIXEL_BOOK_ROWS = [
  [0, 1, 1, 1, 1, 1, 1, 0],
  [0, 1, 0, 1, 1, 1, 1, 0],
  [1, 1, 0, 1, 1, 1, 1, 1],
  [1, 1, 0, 1, 1, 1, 1, 1],
  [1, 1, 0, 1, 1, 1, 1, 1],
  [1, 1, 0, 1, 1, 1, 1, 1],
  [0, 1, 0, 1, 1, 1, 1, 0],
  [0, 1, 1, 1, 1, 1, 1, 0],
]

function buildBookShadow(): string {
  const PX = 6
  const shadows: string[] = []
  PIXEL_BOOK_ROWS.forEach((row, rowIdx) => {
    row.forEach((cell, colIdx) => {
      if (cell) {
        const x = colIdx * PX
        const y = rowIdx * PX
        const color =
          colIdx === 2
            ? '#e94560' // spine column
            : colIdx <= 1
              ? '#f5a623' // cover left
              : '#c8d8f0' // pages
        shadows.push(`${x}px ${y}px 0 ${color}`)
      }
    })
  })
  return shadows.join(', ')
}

const BOOK_SHADOW = buildBookShadow()

export default function SplashScreen({ onReady }: SplashScreenProps) {
  const [timedOut, setTimedOut] = useState(false)
  const [retryKey, setRetryKey] = useState(0)
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(HEALTH_URL)
        if (res.ok) {
          onReady()
        }
      } catch {
        // keep polling silently — backend is still waking up
      }
    }

    // Check immediately on mount
    checkHealth()

    // Set timeout for 8 seconds
    const timeout = setTimeout(() => {
      setTimedOut(true)
    }, TIMEOUT_SECONDS * 1000)

    // Then poll every 500ms
    const interval = setInterval(checkHealth, POLL_INTERVAL)
    return () => {
      clearTimeout(timeout)
      clearInterval(interval)
    }
  }, [onReady, retryKey]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <style>{`
        @keyframes splash-bar-fill {
          0%   { width: 4%;  }
          25%  { width: 35%; }
          50%  { width: 65%; }
          75%  { width: 82%; }
          90%  { width: 92%; }
          100% { width: 4%;  }
        }
        @keyframes splash-title-glow {
          0%, 100% { text-shadow: 4px 4px 0 rgba(0,0,0,0.6), 0 0 24px rgba(233,69,96,0.3); }
          50%       { text-shadow: 4px 4px 0 rgba(0,0,0,0.6), 0 0 48px rgba(233,69,96,0.7); }
        }
        @keyframes splash-book-float {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-6px); }
        }
        @keyframes splash-dot-blink {
          0%, 66%  { opacity: 1; }
          67%, 100% { opacity: 0; }
        }
        .splash-dot-1 { animation: splash-dot-blink 1.2s steps(1) infinite 0.0s; }
        .splash-dot-2 { animation: splash-dot-blink 1.2s steps(1) infinite 0.4s; }
        .splash-dot-3 { animation: splash-dot-blink 1.2s steps(1) infinite 0.8s; }

        .splash-screen {
          position: fixed;
          inset: 0;
          background-color: var(--color-bg-primary, #1a1a2e);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          overflow: hidden;
        }
        .splash-screen::before {
          content: '';
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 3px,
            rgba(0, 0, 0, 0.08) 3px,
            rgba(0, 0, 0, 0.08) 4px
          );
          pointer-events: none;
        }
        .splash-grid-bg {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(42, 74, 122, 0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(42, 74, 122, 0.15) 1px, transparent 1px);
          background-size: 32px 32px;
          pointer-events: none;
        }
        .splash-content {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0;
        }
        .splash-book-wrap {
          animation: splash-book-float 2s steps(4) infinite;
          margin-bottom: 32px;
        }
        .splash-book-pixel {
          width: 6px;
          height: 6px;
          background: transparent;
          box-shadow: ${BOOK_SHADOW};
          image-rendering: pixelated;
        }
        .splash-title {
          font-family: var(--font-pixel, 'Press Start 2P', monospace);
          font-size: clamp(18px, 4vw, 32px);
          color: var(--color-accent-primary, #e94560);
          letter-spacing: 2px;
          margin: 0 0 16px 0;
          animation: splash-title-glow 2.4s ease-in-out infinite;
          line-height: 1.4;
          text-align: center;
        }
        .splash-subtitle {
          font-family: var(--font-pixel, 'Press Start 2P', monospace);
          font-size: 8px;
          color: var(--color-text-secondary, #a0a0b0);
          margin: 0 0 24px 0;
          letter-spacing: 1px;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .splash-loading-bar-outer {
          width: 240px;
          height: 18px;
          border: 3px solid var(--color-border-bright, #4a7aaa);
          background: var(--color-bg-secondary, #16213e);
          box-shadow: 4px 4px 0 rgba(0,0,0,0.5), inset 2px 2px 0 rgba(0,0,0,0.3);
          overflow: hidden;
          image-rendering: pixelated;
        }
        .splash-loading-bar-inner {
          height: 100%;
          background: var(--color-accent-primary, #e94560);
          animation: splash-bar-fill 2s steps(20) infinite;
          box-shadow: inset 0 0 0 2px rgba(255,255,255,0.15);
        }
        .splash-version {
          margin-top: 20px;
          font-family: var(--font-pixel, 'Press Start 2P', monospace);
          font-size: 6px;
          color: var(--color-text-muted, #606070);
          letter-spacing: 1px;
        }
        .splash-error-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          padding: 24px;
          background: var(--color-bg-secondary, #16213e);
          border: 3px solid var(--color-accent-primary, #e94560);
          box-shadow: 4px 4px 0 rgba(0,0,0,0.5);
        }
        .splash-error-heading {
          font-family: var(--font-pixel, 'Press Start 2P', monospace);
          font-size: 12px;
          color: var(--color-accent-primary, #e94560);
          margin: 0;
          text-align: center;
          letter-spacing: 1px;
        }
        .splash-error-message {
          font-family: var(--font-content, 'Inter', sans-serif);
          font-size: 12px;
          color: var(--color-text-secondary, #a0a0b0);
          margin: 0;
          text-align: center;
          line-height: 1.5;
        }
        .splash-error-code {
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
          font-size: 9px;
          color: var(--color-accent-secondary, #f5a623);
          background: var(--color-bg-primary, #1a1a2e);
          border: 2px solid var(--color-border, #2a4a7a);
          padding: 12px;
          margin: 8px 0;
          white-space: pre-wrap;
          word-break: break-all;
          text-align: left;
          box-shadow: inset 2px 2px 0 rgba(0,0,0,0.3);
        }
        .splash-error-buttons {
          display: flex;
          gap: 12px;
          margin-top: 8px;
        }
        .splash-error-btn {
          font-family: var(--font-pixel, 'Press Start 2P', monospace);
          font-size: 8px;
          padding: 10px 16px;
          border: 3px solid var(--color-border-bright, #4a7aaa);
          background: var(--color-bg-secondary, #16213e);
          color: var(--color-text-primary, #e8e8e8);
          cursor: pointer;
          box-shadow: 4px 4px 0 rgba(0,0,0,0.5);
          transition: none;
          image-rendering: pixelated;
          letter-spacing: 1px;
        }
        .splash-error-btn:hover:not(:disabled) {
          background: var(--color-bg-panel, #0f3460);
          border-color: var(--color-accent-primary, #e94560);
        }
        .splash-error-btn:active:not(:disabled) {
          box-shadow: 2px 2px 0 rgba(0,0,0,0.5);
          transform: translate(2px, 2px);
        }
        .splash-error-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .splash-error-btn--danger {
          border-color: var(--color-accent-primary, #e94560);
          color: var(--color-accent-primary, #e94560);
        }
      `}</style>


      <div className="splash-screen">
        <div className="splash-grid-bg" />

        <div className="splash-content">
          {timedOut ? (
            <div className="splash-error-state">
              <h2 className="splash-error-heading">⚠ BACKEND OFFLINE</h2>
              <p className="splash-error-message">Backend not running. Start the Python server first.</p>
              <div className="splash-error-code">cd backend && uvicorn app.main:app --port 8000</div>
              <div className="splash-error-buttons">
                <button
                  className="splash-error-btn splash-error-btn--danger"
                  onClick={() => {
                    setTimedOut(false)
                    setRetryKey(prev => prev + 1)
                  }}
                >
                  ↺ RETRY
                </button>
                <button
                  className="splash-error-btn"
                  onClick={() => onReady()}
                >
                  CONTINUE ANYWAY
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Pixel art book icon */}
              <div className="splash-book-wrap" aria-hidden="true">
                <div className="splash-book-pixel" />
              </div>

              {/* Title */}
              <h1 className="splash-title">Lazy Learn</h1>

              {/* Subtitle with blinking dots */}
              <p className="splash-subtitle">
                Loading study assistant
                <span className="splash-dot-1">.</span>
                <span className="splash-dot-2">.</span>
                <span className="splash-dot-3">.</span>
              </p>

              {/* Pixel loading bar */}
              <div className="splash-loading-bar-outer" role="progressbar" aria-label="Loading">
                <div className="splash-loading-bar-inner" />
              </div>

              <p className="splash-version">v0.1.0 — CONNECTING TO BACKEND</p>
            </>
          )}
        </div>
      </div>
    </>
  )
}
