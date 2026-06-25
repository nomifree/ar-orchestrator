from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "ar_orchestrator_plain_english_guide.pdf"


def style_sheet():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#0F1923"),
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubTitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontSize=12,
            leading=17,
            textColor=colors.HexColor("#475569"),
            spaceAfter=24,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1x",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=22,
            textColor=colors.HexColor("#0F1923"),
            spaceBefore=8,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2x",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#1B6CA8"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Bodyx",
            parent=styles["BodyText"],
            fontSize=10.2,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Smallx",
            parent=styles["BodyText"],
            fontSize=8.4,
            leading=11,
            textColor=colors.HexColor("#475569"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Callout",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0F172A"),
            backColor=colors.HexColor("#EEF6FC"),
            borderColor=colors.HexColor("#1B6CA8"),
            borderWidth=0.8,
            borderPadding=8,
            spaceBefore=8,
            spaceAfter=10,
        )
    )
    return styles


def p(text, style="Bodyx"):
    return Paragraph(text, STYLES[style])


def bullets(items):
    flow = []
    for item in items:
        flow.append(p(f"- {item}"))
    return flow


def table(data, widths=None, font_size=8.2):
    converted = [[p(str(cell), "Smallx") for cell in row] for row in data]
    t = Table(converted, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F1923")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]
        )
    )
    return t


def page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(0.65 * inch, 0.42 * inch, "AR Orchestrator Plain-English Guide")
    canvas.drawRightString(A4[0] - 0.65 * inch, 0.42 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_story():
    flow = []
    flow.append(p("AR Orchestrator", "TitleCenter"))
    flow.append(
        p(
            "A plain-English guide to the company, the business problem, the build, and how to explain it in an interview.",
            "SubTitle",
        )
    )
    flow.append(
        p(
            "Read this like a map. The whole project is about one simple idea: money is stuck in unpaid medical claims, and managers need a clean way to decide what to chase first.",
            "Callout",
        )
    )
    flow += bullets(
        [
            "Audience: Nouman, preparing for a finance or revenue-operations interview.",
            "Company target: Twenty Four Seven Consultancy, Rawalpindi.",
            "Build target: AR Work Queue and Denial Resolution Orchestrator.",
            "Language rule: no heavy jargon. Every term is explained.",
        ]
    )
    flow.append(PageBreak())

    flow.append(p("1. First, Understand The Company", "H1x"))
    flow.append(
        p(
            "24-7 Consultancy presents itself as a service company. It sells support to other businesses so those businesses can run smoother. On its public site, the main service buckets are BPO, healthcare, digital marketing, and software or web development.",
        )
    )
    flow.append(
        p(
            "For this project, the most important part is healthcare. Their site says healthcare work includes medical billing, medical transcription, and management services. Their homepage also says healthcare includes patient billing and insurance claims processing. That means they are not only doing general office work. They are involved in the flow of medical money.",
        )
    )
    flow.append(
        p(
            "Their medical billing page says they help with claims submission, payment posting, follow-up, reducing denials, revenue cycle reports, coding review, documentation review, credentialing, and compliance. Their management services page mentions patient payments, insurance eligibility, and regular reports.",
        )
    )
    flow.append(p("Simple meaning:", "H2x"))
    flow += bullets(
        [
            "Doctors and clinics treat patients.",
            "Those clinics need to get paid by insurance companies and sometimes by patients.",
            "That payment process is messy, slow, and document-heavy.",
            "24-7 sells people, process, reports, and support to manage that mess.",
        ]
    )
    flow.append(
        p(
            "Deep business read: 24-7 is likely competing on reliability, cost, trained staff, process discipline, and reporting clarity. Their client does not only want cheap labor. The client wants fewer errors, faster cash, fewer denials, and proof that work is being done.",
            "Callout",
        )
    )

    flow.append(p("2. The Business In One Picture", "H1x"))
    flow.append(
        table(
            [
                ["Player", "What they want", "What can go wrong"],
                ["Clinic / doctor", "Get paid for care already delivered.", "Claims are denied, delayed, or written off."],
                ["Insurance company", "Pay only valid claims under its rules.", "Slow review, denial, request for documents."],
                ["Patient", "Know what they owe and avoid confusion.", "Wrong balance, missed statement, delayed payment."],
                ["24-7 billing team", "Move claims toward payment efficiently.", "Reps chase the wrong claims or miss deadlines."],
                ["24-7 manager", "Control workload and prove results.", "Manual spreadsheets, weak visibility, poor reports."],
                ["Client owner / CFO", "Better cash flow and lower losses.", "Aging AR, write-offs, no clear accountability."],
            ],
            widths=[1.35 * inch, 2.05 * inch, 2.3 * inch],
        )
    )
    flow.append(
        p(
            "The painful word here is AR. AR means Accounts Receivable. In normal language, it means money someone owes you but has not paid yet. In medical billing, AR can sit unpaid for weeks or months.",
        )
    )
    flow.append(
        p(
            "Your project is built around that stuck money. It asks: which unpaid claims should the team work today so the company protects the most cash with the least wasted effort?",
        )
    )

    flow.append(PageBreak())
    flow.append(p("3. Medical Billing Without Jargon", "H1x"))
    flow.append(
        p(
            "Imagine a patient visits a clinic. The clinic does the treatment. Now the clinic wants payment. It sends a claim to the insurance company. A claim is just a formal request for payment.",
        )
    )
    flow.append(
        table(
            [
                ["Step", "Plain meaning", "Money risk"],
                ["Visit", "Patient receives care.", "No money collected yet."],
                ["Claim sent", "Clinic asks insurance to pay.", "Clock starts running."],
                ["Payer review", "Insurance checks rules and documents.", "Delay starts."],
                ["Payment", "Insurance pays all or part.", "Good outcome."],
                ["Denial", "Insurance refuses payment.", "Cash is now at risk."],
                ["Follow-up", "Billing rep chases or fixes the claim.", "Labor cost starts."],
                ["Appeal", "Team argues the denial should be reversed.", "Deadline matters."],
                ["Write-off", "Company gives up on collecting.", "Revenue is lost."],
            ],
            widths=[1.15 * inch, 2.6 * inch, 1.95 * inch],
        )
    )
    flow.append(
        p(
            "The key point: not every unpaid claim deserves attention today. Some claims are still within normal insurance processing time. Touching them wastes staff time. Other claims are urgent because they have high value, old age, or a deadline.",
            "Callout",
        )
    )

    flow.append(p("4. What Problem Your Build Solves", "H1x"))
    flow.append(
        p(
            "The project solves a management problem: billing teams often have a long list of unpaid claims, but the list does not clearly say what to work first. A rep may chase a small claim while a large denial is about to pass its appeal deadline.",
        )
    )
    flow.append(
        table(
            [
                ["Old way", "Better way your build shows"],
                ["Long spreadsheet of claims.", "Ranked queue showing what to work first."],
                ["Rep decides from experience.", "Rules explain why each claim is high priority."],
                ["Managers count touches.", "Managers see recovery value and stale claims."],
                ["Client reports made manually.", "Client export generated from live data."],
                ["Denials found late.", "Deadline risk visible before loss happens."],
            ],
            widths=[2.8 * inch, 2.8 * inch],
        )
    )
    flow.append(
        p(
            "This is why the project is useful for a finance interview. It is not just software. It is a cash-recovery control system. It connects operations to money.",
            "Callout",
        )
    )

    flow.append(PageBreak())
    flow.append(p("5. The Build In One Simple Flow", "H1x"))
    flow.append(
        table(
            [
                ["Part", "Plain meaning"],
                ["Synthetic data", "Fake but realistic claims, denials, follow-ups, payers, clients, and employees."],
                ["Database", "A place to store the data so the app can calculate from it."],
                ["Rules engine", "A checklist that decides claim status, score, and next action."],
                ["API", "The bridge between the backend calculations and the screen."],
                ["Dashboard", "Manager view: how much risk exists today."],
                ["Queue", "Work list: which claims to work first."],
                ["Drilldown", "Proof screen: why this claim got this score."],
                ["Exports", "Files for managers or clients."],
                ["Tests", "Checks that prove the rules behave as expected."],
            ],
            widths=[1.45 * inch, 4.25 * inch],
        )
    )
    flow.append(p("Think of it like a restaurant kitchen:", "H2x"))
    flow += bullets(
        [
            "Raw orders are the claims.",
            "The manager needs to know which orders are urgent.",
            "The rules engine is the kitchen checklist.",
            "The queue is the order board.",
            "The drilldown is the reason written on the ticket.",
            "The export is the report sent to the owner.",
        ]
    )

    flow.append(p("6. The Three Core Questions", "H1x"))
    flow.append(
        p(
            "Every claim in your build is judged by three questions. If you can explain these three questions, you understand the whole project.",
            "Callout",
        )
    )
    flow.append(
        table(
            [
                ["Question", "What it means", "Output"],
                ["Should anyone touch this today?", "Some claims should wait. Some need action now.", "Workability status"],
                ["If yes, how urgent is it?", "Older, larger, riskier claims go higher.", "Priority score"],
                ["What exactly should the rep do?", "No guessing. One next action.", "Recommended action"],
            ],
            widths=[1.9 * inch, 2.4 * inch, 1.35 * inch],
        )
    )

    flow.append(PageBreak())
    flow.append(p("7. Workability: Should A Rep Touch It Today?", "H1x"))
    flow.append(
        p(
            "Workability simply means: is this claim ready for human action today? This matters because touching the wrong claim wastes salary hours.",
        )
    )
    flow.append(
        table(
            [
                ["Status", "Simple meaning", "Touch today?"],
                ["System Hold", "The system or normal payer time has not passed yet.", "No"],
                ["Waiting Payer", "The payer is expected to respond later.", "No"],
                ["Waiting Client", "The clinic/provider must send information first.", "No"],
                ["Active Workable", "The claim is open and should be followed up.", "Yes"],
                ["Denial Workable", "Denied, but can still be appealed or fixed.", "Yes"],
                ["Patient Balance", "Insurance part is done; patient owes money.", "Yes"],
                ["Escalation Required", "High risk, old, stuck, or deadline problem.", "Yes, manager attention"],
                ["Closed", "Paid, voided, or written off.", "No"],
            ],
            widths=[1.45 * inch, 3.2 * inch, 1.05 * inch],
        )
    )
    flow.append(
        p(
            "Interview line: The first saving is not recovery. The first saving is avoiding wasted touches. If 50 percent of open claims should not be touched today, a clean workability filter protects labor time.",
            "Callout",
        )
    )

    flow.append(p("8. Priority Score: What To Work First", "H1x"))
    flow.append(
        p(
            "After a claim is work-ready, the project gives it a score from 0 to 100. Higher score means work it earlier. The score is not magic. It is just six small scores added together.",
        )
    )
    flow.append(
        table(
            [
                ["Factor", "Why it matters", "Max points"],
                ["Days in AR", "Older money is more likely to become lost money.", "25"],
                ["Outstanding balance", "Bigger unpaid amount deserves more attention.", "20"],
                ["Denial deadline", "Appeal deadlines can destroy recovery chances.", "20"],
                ["Stale follow-up", "No recent touch means the claim may be forgotten.", "15"],
                ["Payer risk", "Some payers are slower or harder to collect from.", "10"],
                ["Repeat denial", "Same problem again means deeper issue.", "10"],
            ],
            widths=[1.55 * inch, 3.2 * inch, 0.95 * inch],
        )
    )
    flow.append(
        p(
            "Priority labels are simple: 80 to 100 is Critical, 60 to 79 is High, 40 to 59 is Medium, and below 40 is Low.",
        )
    )

    flow.append(PageBreak())
    flow.append(p("9. The Demo Claim: CLM-10021", "H1x"))
    flow.append(
        p(
            "The build includes one strong demo claim called CLM-10021. It is designed to make the logic easy to explain.",
        )
    )
    flow.append(
        table(
            [
                ["Field", "Value", "Why it matters"],
                ["Client", "Sunrise Family Clinic", "Shows client-level reporting."],
                ["Payer", "UnitedHealthcare", "Payer risk affects score."],
                ["Claim type", "Authorization denial", "A common denial category."],
                ["Days in AR", "96", "Old enough to be dangerous."],
                ["Appeal deadline", "2026-07-01", "Only 6 days after the fixed demo date."],
                ["Score", "82", "Critical."],
                ["Action", "File authorization appeal today or escalate.", "Clear next step."],
            ],
            widths=[1.3 * inch, 1.8 * inch, 2.6 * inch],
        )
    )
    flow.append(p("Score explanation for CLM-10021:", "H2x"))
    flow.append(
        table(
            [
                ["Score part", "Points"],
                ["Days AR", "25"],
                ["Balance", "7"],
                ["Denial deadline", "20"],
                ["Stale follow-up", "10"],
                ["Payer risk", "10"],
                ["Repeat denial", "10"],
                ["Total", "82"],
            ],
            widths=[3.2 * inch, 1.0 * inch],
        )
    )
    flow.append(
        p(
            "This is the heart of the demo. You can point at the claim and say: this is not a black box. The app shows the exact reason behind the score.",
            "Callout",
        )
    )

    flow.append(p("10. What Each Screen Means", "H1x"))
    flow.append(
        table(
            [
                ["Screen", "What to say"],
                ["Dashboard", "This is the morning manager view. It shows the size of today's AR risk."],
                ["Queue", "This is the rep work list. It ranks claims by urgency and value."],
                ["Drilldown", "This proves the score. It shows financial facts, denial details, and timeline."],
                ["Reps", "This measures recovery value and useful work, not just activity."],
                ["Clients", "This helps leadership prepare client reports quickly."],
                ["Settings", "This shows managers can adjust scoring weights without changing code."],
            ],
            widths=[1.4 * inch, 4.2 * inch],
        )
    )

    flow.append(PageBreak())
    flow.append(p("11. Why This Matters To 24-7", "H1x"))
    flow.append(
        p(
            "24-7 sells service quality. In medical billing, service quality is not only politeness or speed. It is whether the billing team helps clients collect money correctly and on time.",
        )
    )
    flow.append(
        table(
            [
                ["24-7 public service area", "How this build connects"],
                ["Medical billing", "Claims, denials, follow-up, payment posting logic."],
                ["Revenue cycle reports", "Dashboard and Excel exports."],
                ["Reducing denials", "Denial category tracking and action guidance."],
                ["Patient payments", "Patient balance queue and next action."],
                ["Insurance eligibility", "Eligibility denial workflow."],
                ["Management services", "Manager dashboard, rep metrics, client pack."],
                ["Technology and innovation", "Working prototype with live backend and frontend."],
                ["Security and compliance posture", "Synthetic data only; production would need RBAC and audit logs."],
            ],
            widths=[2.25 * inch, 3.4 * inch],
        )
    )
    flow.append(
        p(
            "Deep fit: the project is valuable because it sits between finance and operations. It turns a messy daily workflow into a ranked recovery system. That is exactly the kind of thinking a finance person can bring to a service company.",
            "Callout",
        )
    )

    flow.append(p("12. Finance Understanding Behind The Build", "H1x"))
    flow.append(
        p(
            "Finance is not only making statements. In a service business, finance also means understanding where cash gets stuck and what process change can release it.",
        )
    )
    flow.append(
        table(
            [
                ["Finance idea", "Simple meaning", "Where the build shows it"],
                ["Cash flow", "How quickly money comes in.", "Aged AR and priority queue."],
                ["Write-off risk", "Money likely to be lost.", "90+ AR and expired deadlines."],
                ["Labor ROI", "Does staff time create value?", "Recovery per follow-up touch."],
                ["Client retention", "Can you prove value to clients?", "Client export pack."],
                ["Control system", "Rules prevent random work.", "Workability and scoring engine."],
                ["Forecasting base", "Clean data supports future planning.", "Structured claims and denial data."],
            ],
            widths=[1.45 * inch, 2.0 * inch, 2.2 * inch],
        )
    )

    flow.append(PageBreak())
    flow.append(p("13. Why It Is Not Static", "H1x"))
    flow.append(
        p(
            "A static demo would be fake numbers on a screen. This build is better because the screen asks the backend for live data. The backend calculates from the database. The rules decide the output.",
        )
    )
    flow += bullets(
        [
            "Dashboard numbers come from API endpoints.",
            "Queue rows come from the database.",
            "Scores come from the rules engine.",
            "Settings can change the scoring weights.",
            "Follow-up logging changes backend data and refreshes the queue.",
            "Exports are generated from current backend data.",
            "Tests check the important business rules.",
        ]
    )
    flow.append(
        p(
            "Simple proof: if the backend is stopped, the frontend shows an error instead of pretending. That proves the UI is not just hardcoded numbers.",
            "Callout",
        )
    )

    flow.append(p("14. Why It Is Defendable", "H1x"))
    flow.append(
        table(
            [
                ["Risk", "How the build controls it"],
                ["Hallucination", "No AI decides claim priority. Rules decide it."],
                ["Random score", "Each score has visible parts that add up."],
                ["Fake medical data", "Synthetic data only; no real patient data."],
                ["Wrong deadline logic", "Expired deadlines are checked before urgent deadlines."],
                ["Overclaiming production readiness", "Docs list missing production pieces honestly."],
                ["Confusing finance story", "Demo focuses on AR, cash recovery, and reporting."],
            ],
            widths=[2.05 * inch, 3.6 * inch],
        )
    )

    flow.append(p("15. The Honest Limits", "H1x"))
    flow.append(
        p(
            "These limits are not weaknesses if you say them clearly. They show maturity.",
            "Callout",
        )
    )
    flow += bullets(
        [
            "The data is synthetic, not real client data.",
            "The upload and validation screen is not fully built yet.",
            "There is no login, role-based access, or audit log yet.",
            "There is no live connection to a real practice management system.",
            "Production would need private hosting, PHI controls, security review, and client-specific rules.",
            "The current version is a prototype to prove the business logic and workflow.",
        ]
    )

    flow.append(PageBreak())
    flow.append(p("16. How To Explain It In An Interview", "H1x"))
    flow.append(p("Use this exact simple structure:", "H2x"))
    flow.append(
        p(
            "I studied your healthcare and medical billing services. I noticed that in medical billing, one big finance problem is unpaid claims sitting in AR. Some claims should be worked today, some should wait, and some are urgent because of denial deadlines. So I built a small rules-based prototype that ranks claims by recovery risk and tells the billing team the next action.",
            "Callout",
        )
    )
    flow.append(p("Then demo in this order:", "H2x"))
    flow += bullets(
        [
            "Dashboard: Here is the total work and risk today.",
            "Queue: Here are the claims ranked by urgency.",
            "CLM-10021: Here is why one claim is Critical.",
            "Rep scorecard: Here is how managers can measure value, not just activity.",
            "Client export: Here is how client reporting becomes faster.",
            "Settings: Here is how managers can adjust the rule weights.",
        ]
    )
    flow.append(p("Do not say:", "H2x"))
    flow += bullets(
        [
            "Do not say it is production-ready.",
            "Do not say it uses real patient data.",
            "Do not say it replaces their billing system.",
            "Do not lead with coding terms like FastAPI, DuckDB, or React.",
            "Do not make medical advice claims.",
        ]
    )

    flow.append(p("17. Best One-Minute Pitch", "H1x"))
    flow.append(
        p(
            "This project is a finance-operations prototype for medical billing. It helps a manager see which unpaid claims need action today, which denials are close to deadlines, and which reps are recovering value. The key idea is simple: do not waste staff time on claims that should wait, and do not let high-value claims age into write-offs. The system uses synthetic data and fixed rules, so every score is explainable and not a black box.",
            "Callout",
        )
    )

    flow.append(PageBreak())
    flow.append(p("18. Questions They May Ask", "H1x"))
    flow.append(
        table(
            [
                ["Question", "Simple answer"],
                ["Why did you build this?", "Because medical billing is a cash-flow process, and poor follow-up turns recoverable AR into lost revenue."],
                ["Is this AI?", "No. The important decisions are rules-based and explainable."],
                ["Can it use real data?", "Yes, but production needs secure upload, PHI controls, access roles, and audit logs."],
                ["How does it help finance?", "It reduces write-off risk, improves collections focus, and makes client reporting faster."],
                ["What would you build next?", "Upload validation, user roles, audit logs, and real client-specific reporting."],
                ["Why should we care?", "It connects staff work to cash outcomes, which is the real finance value."],
            ],
            widths=[2.0 * inch, 3.65 * inch],
        )
    )

    flow.append(p("19. Shariah And Career Screen", "H1x"))
    flow.append(
        p(
            "This project itself is not an interest-based finance product. It is about service revenue, unpaid claims, workflow, and reporting. That is generally cleaner than a conventional lending or interest-income role.",
        )
    )
    flow.append(
        p(
            "Still, if the finance job involves loans, interest income, bank facilities, or conventional debt products, ask directly before accepting. A good question is: Does this role involve managing interest-based financing, loan products, or interest income?",
            "Callout",
        )
    )

    flow.append(p("20. Source Notes", "H1x"))
    flow.append(
        p(
            "Company facts were checked from 24-7 Consultancy public pages on 2026-06-25. The project facts come from the local build in this workspace.",
        )
    )
    flow += bullets(
        [
            "Homepage: https://24-7consultancy.pk/",
            "Medical Billing: https://24-7consultancy.pk/medical-billing",
            "Management Services: https://24-7consultancy.pk/management-services",
            "Career page: https://24-7consultancy.pk/career",
            "Local rules file: backend/app/rules.py",
            "Local business rules doc: docs/business_rules.md",
            "Local tickets doc: docs/tickets.md",
        ]
    )
    flow.append(
        p(
            "Final mental model: 24-7 helps clients run operations. Medical billing operations are really money operations. Your build shows that you can understand cash risk, create a control system, and communicate it simply.",
            "Callout",
        )
    )
    return flow


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="AR Orchestrator Plain-English Guide",
        author="Codex for Nouman Qureshi",
    )
    story = build_story()
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    print(OUT)


STYLES = style_sheet()


if __name__ == "__main__":
    main()
