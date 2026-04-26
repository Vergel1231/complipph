# BIR Filipino — Product Requirements Document

_Last updated: Feb 26, 2026_

## Original Problem Statement
Build a focused B2B SaaS app for Filipino freelancers and solo professionals
(consultants, designers, lawyers, doctors) managing quarterly BIR ITR filing
and monthly payroll for 1–5 employees. Solve exactly one problem: BIR form
auto-generation and deadline tracking. Built for monthly recurring revenue,
80%+ retention via filing-history lock-in, founder-independent operations,
and 18-month exit positioning.

Tagline: _"The solo professional's tool that generates your BIR form in 60 seconds."_

## User Personas
1. **Solo professional (primary)** — consultant, designer, lawyer, doctor with
   BIR registration. Earns ₱500K–₱3M/year. Hates filing taxes. Pays monthly to
   never miss a deadline.
2. **CPA / bookkeeper (secondary, reseller)** — manages 5–25 freelancer clients.
   Wants one dashboard for all client filings. Earns recurring per-seat fee.
3. **Admin (founder)** — needs to operate without dependency: editable BIR
   rules, MRR/churn dashboards, user list, support tickets.

## Core Requirements (static)
- Recurring revenue (MRR), no free tier
- Retention via filing history archive lock-in
- 80%+ monthly retention target
- Admin dashboard: MRR, churn, active users, BIR rule editor
- Compliance rules (BIR deadlines, tax tables, form versions) editable via admin
- 30-day founder-independent operability
- Exit-ready architecture (predictable, scalable, founder-independent)

## Tech Stack
- Backend: FastAPI + MongoDB + JWT email/password + Emergent Google SSO
- AI: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) via Emergent LLM key
- Email: Resend (no-op without `RESEND_API_KEY`, ready to activate)
- Billing: Mock provider (clean PayMongo swap-in: replace `_mock_create_checkout`)
- Frontend: React + React Router + Tailwind + shadcn/ui + Phosphor Icons
- Design: Cabinet Grotesk + Manrope, warm sand / deep olive / terracotta palette

## Implemented (Feb 26, 2026 — MVP + Phase 2)
### Backend
- ✅ JWT email/password auth (register, login, logout, refresh, /me, forgot/reset)
- ✅ Emergent Google SSO (POST /api/auth/google/session) with httpOnly session cookie
- ✅ Admin auto-seed (admin@birfilipino.app)
- ✅ Business profile + 3-step onboarding-driven `is_vat`/classification
- ✅ BIR engine: 1701Q (8% flat & graduated TRAIN brackets) and 2551Q (3%)
- ✅ 2551Q gating (rejects 8%-flat or VAT-registered)
- ✅ Filing history (mark-submitted closes deadline)
- ✅ Deadline calendar (1701Q Q1/Q2/Q3 + 2551Q Q1–Q4 for graduated non-VAT)
- ✅ AI Tax Assistant (Claude Sonnet 4.5)
- ✅ Admin: MRR, churn, user count, BIR rules editor, user list
- ✅ Mock billing (Solo / Pro / Reseller plans, PayMongo-ready structure)
- ✅ **APScheduler daily 09:00 Asia/Manila** reminder cron — sends 30/7/1-day BIR deadline emails via Resend (no-op until `RESEND_API_KEY` is set; self-healing dedup logic)
- ✅ **POST /api/admin/run-reminders** manual trigger endpoint (admin-only)
- ✅ **GET /api/forms/{id}/export.pdf** — reportlab BIR worksheet PDF
- ✅ **GET /api/forms/{id}/export.xml** — eBIRForms-style XML envelope

### Frontend
- ✅ Landing page (hero with Tetris grid, 3-stat band, how-it-works, audience showcase, retention lock-in band, CPA reseller, footer CTA)
- ✅ Login & Register (email + Google SSO buttons)
- ✅ AuthCallback (Emergent OAuth session_id exchange)
- ✅ 3-step Onboarding (business → classification → first period)
- ✅ Dashboard (next deadline, stats, upcoming list, recent filings)
- ✅ Form Generator (1701Q + 2551Q wizard with computed BIR field map)
- ✅ Filing History (archive table with detail modal)
- ✅ Calendar View (deadlines grouped by month, severity badges)
- ✅ AI Assistant (chat UI with suggested prompts)
- ✅ Pricing page (3 plans, PHP-first display, USD secondary)
- ✅ Settings (account + business profile + subscription)
- ✅ Admin (metrics, users table, BIR rules editor)

### Testing
- ✅ Backend Phase 1: 30/30 tests passed
- ✅ Backend Phase 2: 13 new tests passed (43/43 total — zero regressions)

## Backlog
### P0 (next)
- [ ] **Add `RESEND_API_KEY` to env** — email sending is fully wired; reminders flip from `disabled` → `sent` automatically (dedup is self-healing)
- [ ] PayMongo live swap (replace mock checkout, add webhook handler)

### P1
- [ ] Payroll module (compute net pay, 1604C summary)
- [ ] Reseller/CPA dashboard (manage 25 client filings from one screen)
- [ ] Annual 1701 form support
- [ ] In-app support ticket form + email integration
- [ ] SEO content hub for high-intent BIR keywords

### P2
- [ ] Stripe USD secondary billing for diaspora users
- [ ] Multi-business support (Pro plan: 3 profiles)
- [ ] Bulk import filings from spreadsheet
- [ ] eBIRForms direct submission (when API available)
- [ ] Mobile-app (React Native) for deadline notifications

## Test Credentials
- Admin: `admin@birfilipino.app` / `Admin@2026` (auto-seeded)
- Test users: register via UI

## Distribution Strategy
- Primary: SEO content for BIR deadline keywords (P1 backlog)
- Secondary: CPA reseller program (P1 backlog)
- Tertiary: Filipino freelancer FB communities

## Exit Positioning
- Target acquirer: Filipino fintech operator, regional holdco, accounting SaaS
- Revenue model: ₱499 / ₱999 / ₱2,499 monthly = MRR-stable
- Multiple: 3–5x annual profit at 80%+ retention with owned SEO channel
