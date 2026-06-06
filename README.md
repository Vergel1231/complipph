# CompliPH

**BIR tax compliance SaaS for Filipino freelancers and solo professionals.**

CompliPH automates the computation and generation of BIR forms 1701Q and 2551Q — the two most common filings for self-employed Filipinos. Built for doctors, lawyers, designers, consultants, and anyone with a Certificate of Registration.

🔗 **Live app:** https://vergel1231.github.io/complipph

---

## What it does

- **1701Q generator** — computes quarterly income tax under 8% flat rate or graduated TRAIN Law brackets, pre-fills all BIR line items, and exports to PDF and eBIRForms-compatible XML
- **2551Q generator** — computes quarterly percentage tax (3%) for non-VAT registered professionals
- **BIR Deadline Calendar** — tracks all upcoming filing deadlines with countdown badges and 30/7/1-day email reminders
- **Filing History** — every generated form is saved as a compliance archive with PDF and XML download
- **AI Tax Assistant** — answers questions about BIR forms, taxpayer classifications, deadlines, and penalties in plain Filipino-professional context
- **Onboarding** — captures TIN, RDO code, taxpayer type, and line of business to pre-fill all future forms automatically

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Tailwind CSS, shadcn/ui, React Router |
| Backend | FastAPI (Python 3.11), Motor (async MongoDB) |
| Database | MongoDB Atlas (Singapore region) |
| Auth | JWT (email/password), bcrypt |
| Email | Resend |
| Payments | PayMongo |
| AI | Anthropic Claude (claude-haiku-4-5) |
| Hosting | GitHub Pages (frontend) + Render (backend) |
| Scheduling | APScheduler — daily 09:00 Asia/Manila reminder job |

---

## Running locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB Atlas account (free M0 tier works)

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your credentials
uvicorn server:app --reload
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
cp .env.example .env
# Set REACT_APP_BACKEND_URL=http://localhost:8000
npm start
```

### Environment variables

See `backend/.env.example` and `frontend/.env.example` for the full list of required variables.

---

## Deployment

| Service | Purpose |
|---|---|
| GitHub Pages | React frontend (`gh-pages` branch) |
| Render | FastAPI backend (free tier, Singapore) |
| MongoDB Atlas | Database (free M0 cluster, Singapore) |

---

## Roadmap

- [ ] BIR Form 1701 (Annual Income Tax Return)
- [ ] BIR Form 1604C (Annual Information Return)
- [ ] 2551Q for graduated filers
- [ ] PayMongo subscription billing (live)
- [ ] SMS reminders via Twilio
- [ ] RDO-specific guidance

---

## License

MIT

---

*Built in the Philippines 🇵🇭 for Filipino professionals tired of spreadsheets.*
