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

## Implemented (Feb 26, 2026 — MVP + Phase 2 + Phase 3)
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
- ✅ APScheduler daily 09:00 Asia/Manila reminder cron + `/api/admin/run-reminders`
- ✅ GET /api/forms/{id}/export.pdf (reportlab) + export.xml (eBIRForms-style)
- ✅ **PayMongo native recurring subscriptions** with mock fallback when keys empty:
  - GET /api/billing/config (provider + public key)
  - POST /api/billing/checkout (creates PayMongo customer + subscription + payment_intent OR mock)
  - POST /api/billing/attach-payment (attaches frontend-tokenized card to payment intent, returns 3DS URL)
  - POST /api/billing/cancel (cancels upstream + locally)
  - POST /api/billing/webhook/paymongo (HMAC-SHA256 signature verification, audit log, status mapping)
- ✅ **User.managed_by_cpa_id** optional/nullable field — non-breaking foundation for Phase 4 reseller dashboard

### Frontend
- ✅ Pricing page now opens **PayMongoCheckout modal** with PCI-safe card tokenization (public-key only, card data never touches our backend)
- ✅ Falls back to instant mock activation when keys empty

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
- ✅ Backend Phase 2: 13 new tests passed
- ✅ Backend Phase 3: 23 new tests passed (66/66 total — zero regressions)

## Backlog
### P0 (next)
- [ ] **Add `RESEND_API_KEY`** — email sending self-heals (`disabled` → `sent`)
- [ ] **Add PayMongo keys** (`PAYMONGO_SECRET_KEY`, `PAYMONGO_PUBLIC_KEY`, `PAYMONGO_WEBHOOK_SECRET`) — `/billing/config` flips to live; first ₱499 charge end-to-end
- [ ] Annual 1701 form + payroll 1604C module (Phase 4)

### P1
- [ ] Reseller / CPA dashboard (schema already supports `managed_by_cpa_id`)
- [ ] In-app support ticket form + email integration
- [ ] Stripe USD secondary billing for diaspora users

### P2 (skipped per founder)
- ~~SEO content hub in-app~~ — handled outside as a separate blog
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
