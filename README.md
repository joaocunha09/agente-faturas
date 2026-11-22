# agente-faturas

Supplier invoice agent for Portuguese SMEs. It reads the AT QR code first, uses Claude only when code alone can't, validates VAT and NIF, flags duplicates and routes every invoice through human review and payment approval.

**Work in progress.** The plan is in `docs/PLANO.md` (in Portuguese).

Stack: Python (FastAPI), Next.js, Supabase, Claude API.