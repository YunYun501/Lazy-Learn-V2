# Lazy Learn — Issues & Gotchas

## Known Risks (pre-spike)
- PyMuPDF equation extraction quality unknown — may garble LaTeX. Spike will determine.
- DeepSeek JSON mode can return empty responses — retry logic MANDATORY.
- DeepSeek high-traffic latency can be 10+ minutes — exponential backoff + timeout handling required.
- Python backend startup 2-5 seconds — splash screen needed.

## Decisions
- Cookie persistence (Task 27 LMS) is ALLOWED — cookies are session tokens, not credentials.
- Math Library is user-built over time — not pre-populated.
- No embeddings by explicit user decision.
