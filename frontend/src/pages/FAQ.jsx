import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import {
  ArrowRightIcon,
  CaretDownIcon,
  CaretUpIcon,
} from "@phosphor-icons/react";

const CATEGORIES = [
  {
    id: "getting-started",
    label: "Getting Started",
    faqs: [
      {
        q: "What is an RDO code, and where do I find mine?",
        a: "RDO stands for Revenue District Office — the BIR branch that manages your tax records. Your RDO code is printed on your BIR Certificate of Registration (Form 2303). If you're in Novaliches, your RDO is likely 28. You can also call the BIR hotline at 02-8538-3200, or check any previous ITR filing — the code appears on every form.",
      },
      {
        q: "What's the difference between 8% flat and graduated? Which one should I pick?",
        a: "The 8% flat rate means you pay 8% of your total gross professional income — no deductions, no brackets, no quarterly percentage tax. Simple and predictable. The graduated rate taxes your net income (gross minus allowable expenses) using TRAIN Law brackets from 0% to 35%, but requires filing 2551Q (3% percentage tax) on top of 1701Q each quarter. For most solo professionals earning under ₱3M annually, 8% flat is simpler and often results in less tax. CompliPH shows you the computed amount either way so you can compare before committing.",
      },
      {
        q: "What is a taxpayer classification, and how do I know what mine is?",
        a: "It's the tax method you registered with the BIR when you got your Certificate of Registration (Form 2303). Look under 'Tax Type' on that document. If you registered as a professional and didn't opt into the graduated system, you're likely on 8% flat. If you're unsure, your RDO or accountant can confirm in one call.",
      },
      {
        q: "Why does the app ask for my TIN? Is it stored securely?",
        a: "Your TIN is a required field on every BIR return — it's how the BIR identifies your account. CompliPH stores it in MongoDB Atlas (a cloud database in Singapore) encrypted at rest and in transit. Access requires authentication with your password. Your TIN is never shared with any third party or used for anything other than generating your forms.",
      },
    ],
  },
  {
    id: "filling-forms",
    label: "Filling Out Your Form",
    faqs: [
      {
        q: "What is 'creditable tax withheld'? I don't think my patients withhold tax.",
        a: "Individual patients don't — but hospitals, HMOs, and clinics that pay you professional fees are required by BIR to withhold 10% or 15% before releasing your payment. They give you BIR Form 2307 as proof. Add up all your 2307s for the quarter and enter the total here. If you have no 2307s, enter ₱0.",
      },
      {
        q: "What is 'tax paid in previous quarters'?",
        a: "If you've already filed 1701Q for Q1 and Q2 of the same year, the tax you paid in those quarters is deducted from your Q3 computation — so you're never taxed twice on the same income within a year. If this is your first filing of the year, enter ₱0.",
      },
      {
        q: "What goes under 'other income'? Does my hospital retainer count?",
        a: "Yes. Your hospital retainer, teaching honoraria, medical mission allowances, and any income that isn't direct patient billing all go under 'other income.' Both gross sales and other income are combined to arrive at your total taxable base.",
      },
      {
        q: "Why do the Cost of Sales and Operating Expenses fields disappear when I pick 8% flat?",
        a: "Because 8% flat doesn't allow deductions — you pay 8% of gross income, full stop. Those fields only matter under the graduated rate, where you're taxed on net income after expenses. Hiding them for 8% filers prevents confusion and avoids data entry mistakes.",
      },
      {
        q: "Why is there no Q4 option for Form 1701Q?",
        a: "The BIR doesn't have a 1701Q for Q4. Instead, you file the annual Form 1701 (due April 15 of the following year), which covers the full year and reconciles everything. Form 1701 is on CompliPH's roadmap and will be available before the April 2027 filing season.",
      },
    ],
  },
  {
    id: "after-generating",
    label: "After You Generate",
    faqs: [
      {
        q: "What is Line 41 / Net Taxable Income?",
        a: "Line 41 is the BIR's label for the income figure your tax is actually computed on. For 8% flat filers, it equals your gross professional income (since no deductions apply at the quarterly level). For graduated filers, it's gross income minus cost of services minus operating expenses. The line numbers match exactly what you'd see on the physical BIR 1701Q form.",
      },
      {
        q: "The computed amount looks off. How do I verify it?",
        a: "The computation follows TRAIN Law exactly. For 8% flat: Tax = Gross Income × 8%, minus creditable tax withheld, minus tax paid in previous quarters this year. If the number seems high, the most common cause is forgetting to enter your 2307 totals or your prior-quarter payments. Double-check those two fields first.",
      },
      {
        q: "What does 'Mark as submitted' mean? Does that file my return with the BIR?",
        a: "No — it doesn't file with the BIR. It tells CompliPH that you've completed filing on your end, which closes the deadline on your calendar and updates your compliance record. Actual filing still goes through the BIR's own channels (eBIRForms or eFPS). Think of it as checking a box in your own records.",
      },
      {
        q: "What is the eBIRForms XML file? Do I need it?",
        a: "eBIRForms is the BIR's free desktop software for filing returns. The XML file CompliPH generates follows the same data structure, so you can import it directly or use the numbers from the PDF to fill in the fields manually. Most non-eFPS filers (which most solo professionals are) submit through eBIRForms and pay separately at a bank or via GCash.",
      },
      {
        q: "What exactly do I do after generating my form to actually file with the BIR?",
        a: (
          <ol className="list-decimal list-inside space-y-2 text-sand-700">
            <li><strong className="text-olive-900">In CompliPH:</strong> Generate your 1701Q, review the computed amounts, and download the PDF (for your records) and the XML file.</li>
            <li><strong className="text-olive-900">Install eBIRForms</strong> if you haven't already — free download at bir.gov.ph. It's a desktop app.</li>
            <li><strong className="text-olive-900">Open eBIRForms,</strong> select Form 1701Q, and enter the values from your CompliPH PDF. You can also import the XML directly.</li>
            <li><strong className="text-olive-900">Submit electronically</strong> through eBIRForms — this sends your return to the BIR.</li>
            <li><strong className="text-olive-900">Pay the tax due</strong> via an authorized agent bank (BDO, BPI, Metrobank), GCash (BIR payment option), or Landbank/DBP online.</li>
            <li><strong className="text-olive-900">Keep your proof</strong> — the eBIRForms confirmation email plus your bank receipt or GCash screenshot.</li>
            <li><strong className="text-olive-900">Back in CompliPH:</strong> Click "Mark as submitted" to close the deadline and update your compliance record.</li>
          </ol>
        ),
      },
    ],
  },
  {
    id: "deadlines",
    label: "Deadlines & Reminders",
    faqs: [
      {
        q: "Are the deadlines accurate for my RDO?",
        a: "Yes. BIR filing deadlines are national and uniform — May 15 (Q1), Aug 15 (Q2), Nov 15 (Q3) for 1701Q. Your RDO location doesn't change your deadlines. The only exception is when the BIR issues a special extension (usually after typhoons or system outages). CompliPH will add support for BIR-issued extensions in a future update.",
      },
      {
        q: "Will the app remind me before a deadline?",
        a: "Yes — CompliPH sends email reminders at 30 days, 7 days, and 1 day before each deadline. Make sure your email address is correct under Settings. The penalty for a late filing is a 25% surcharge, 12% annual interest, and a ₱1,000 compromise penalty — so the reminders are worth paying attention to.",
      },
      {
        q: "Why is there no Q4 deadline for Form 1701Q on the calendar?",
        a: "Q4 rolls into the annual Form 1701, filed April 15 of the following year. That's a separate, more comprehensive form that reconciles your full year of income (including the ₱250,000 personal exemption). It's on the roadmap for the next major release.",
      },
    ],
  },
  {
    id: "account-privacy",
    label: "Account & Privacy",
    faqs: [
      {
        q: "Is my income and TIN data safe?",
        a: "Your data is stored in MongoDB Atlas, hosted in Singapore, encrypted at rest and in transit. Only you can access your filings — each record is tied to your account and protected by your password, which is bcrypt-hashed and never stored in plain text. CompliPH does not sell or share your data with any third party.",
      },
      {
        q: "Who else can see my filings?",
        a: "Nobody except you. There is an admin account used for system maintenance, but individual filing data is not accessed during normal operations. Everything visible in your Filing History and Settings pages is yours alone.",
      },
      {
        q: "Is CompliPH officially accredited by the BIR?",
        a: "No — CompliPH is not an official BIR product and is not accredited as an eFPS or eBIRForms provider. It is a computation and form-preparation tool. The actual submission still goes through official BIR channels. Think of it the way you'd think of a well-made spreadsheet template: the math is correct and the form is pre-filled, but you still file through the BIR's own system.",
      },
      {
        q: "Can I delete my account?",
        a: "Account deletion through the app UI is a planned Settings feature. For now, you can request deletion by emailing us and it will be completed within 24 hours.",
      },
      {
        q: "Is this free? What happens after the beta?",
        a: "CompliPH is free during the beta — no payment required, no credit card asked. After beta, the Solo Pro plan will be ₱499/month, covering unlimited 1701Q and 2551Q filings for one business profile. Beta users will receive early access to a discounted rate before public launch.",
      },
      {
        q: "What do I get on the paid plan that I don't have now?",
        a: "During beta, you have full access to everything. The paid plan post-launch adds: priority AI assistant responses, filing history beyond 12 months, and upcoming features like the annual Form 1701, SMS reminders via text, and multi-profile support — useful if you have both a clinic and a teaching appointment under separate TINs.",
      },
    ],
  },
];

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-sand-200 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start justify-between gap-4 py-5 text-left"
        aria-expanded={open}
      >
        <span className="font-medium text-olive-900 leading-snug">{q}</span>
        <span className="shrink-0 mt-0.5 text-terracotta-600">
          {open ? <CaretUpIcon size={18} weight="bold" /> : <CaretDownIcon size={18} weight="bold" />}
        </span>
      </button>
      {open && (
        <div className="pb-5 text-sand-700 leading-relaxed text-[0.95rem]">
          {typeof a === "string" ? <p>{a}</p> : a}
        </div>
      )}
    </div>
  );
}

export default function FAQ() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState(CATEGORIES[0].id);

  const active = CATEGORIES.find((c) => c.id === activeCategory);

  return (
    <div className="min-h-screen bg-sand-100 paper-grain">
      {/* Header — identical to Landing */}
      <header className="sticky top-0 z-40 bg-sand-100/85 backdrop-blur-xl border-b border-sand-300">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white font-display font-bold">C</div>
            <div className="font-display font-bold text-olive-900 text-lg">CompliPH</div>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-sand-800">
            <Link to="/#how" className="hover:text-olive-900">How it works</Link>
            <Link to="/#why" className="hover:text-olive-900">Why us</Link>
            <Link to="/pricing" className="hover:text-olive-900">Pricing</Link>
            <Link to="/#cpas" className="hover:text-olive-900">For CPAs</Link>
            <Link to="/faq" className="text-terracotta-600 font-semibold">FAQ</Link>
          </nav>
          <div className="flex items-center gap-3">
            {user ? (
              <Button
                onClick={() => navigate("/dashboard")}
                className="bg-olive-600 text-white hover:bg-olive-700"
              >
                Go to dashboard <ArrowRightIcon size={16} />
              </Button>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-olive-800 hover:text-olive-900">Log in</Link>
                <Button
                  onClick={() => navigate("/register")}
                  className="bg-olive-600 text-white hover:bg-olive-700"
                >
                  Get started
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Page hero */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 pt-14 pb-10">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-4">
          Help Center
        </div>
        <h1 className="font-display font-bold text-olive-900 text-4xl lg:text-5xl tracking-tight max-w-2xl leading-[1.05]">
          Frequently asked questions
        </h1>
        <p className="mt-5 text-lg text-sand-700 max-w-xl leading-relaxed">
          Everything you need to know about CompliPH, BIR filings, and what happens to your data.
        </p>
      </section>

      {/* FAQ body — sidebar + content */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 pb-24">
        <div className="flex flex-col lg:flex-row gap-10">

          {/* Category sidebar */}
          <aside className="lg:w-56 shrink-0">
            <nav className="flex flex-row lg:flex-col gap-2 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`shrink-0 text-left px-4 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap lg:whitespace-normal ${
                    activeCategory === cat.id
                      ? "bg-olive-600 text-white"
                      : "text-sand-700 hover:bg-sand-200 hover:text-olive-900"
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </nav>
          </aside>

          {/* FAQ list */}
          <div className="flex-1 bg-white rounded-2xl border border-sand-200 px-6 lg:px-10 py-2">
            <h2 className="font-display font-semibold text-xl text-olive-900 pt-6 pb-4 border-b border-sand-200">
              {active.label}
            </h2>
            {active.faqs.map((item) => (
              <FAQItem key={item.q} q={item.q} a={item.a} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA band */}
      <section className="bg-olive-900 text-sand-50 py-20">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 flex flex-col md:flex-row items-center justify-between gap-8">
          <div>
            <h2 className="font-display font-bold text-3xl lg:text-4xl tracking-tight">
              Still have questions?
            </h2>
            <p className="mt-3 text-sand-300 text-lg">
              Try the AI tax assistant inside the app — it knows BIR rules and can answer in plain Filipino English.
            </p>
          </div>
          <Button
            onClick={() => navigate(user ? "/ai-assistant" : "/register")}
            className="shrink-0 bg-terracotta-500 hover:bg-terracotta-600 text-white px-7 py-6 text-base"
          >
            {user ? "Open AI assistant" : "Get started free"} <ArrowRightIcon size={18} />
          </Button>
        </div>
      </section>

      {/* Footer — identical to Landing */}
      <footer className="bg-olive-900 text-sand-300 py-14 border-t border-white/10">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 flex flex-col md:flex-row justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-9 w-9 rounded-md bg-terracotta-500 grid place-items-center text-white font-display font-bold">C</div>
              <div className="font-display font-bold text-white text-lg">CompliPH</div>
            </div>
            <p className="text-sm text-sand-400 max-w-sm">
              The solo professional's tool that generates your BIR form in 60 seconds.
            </p>
          </div>
          <div className="text-sm">
            © {new Date().getFullYear()} CompliPH. Made in Manila.
          </div>
        </div>
      </footer>
    </div>
  );
}
