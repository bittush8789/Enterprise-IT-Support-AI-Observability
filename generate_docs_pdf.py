"""
Generates production-grade enterprise PDF specifications for:
1. Product Requirements Document (PRD)
2. Technical Requirements Document (TRD)
3. Software Requirements Document (SRD)
"""

import sys
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw total page counts and running headers/footers.
    """
    doc_title = "System Documentation"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Suppress running header/footer on title cover page

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Header
        self.drawString(54, 750, f"Enterprise IT Support Agentic RAG Copilot  |  {self.doc_title}")
        self.setFont("Helvetica", 8)
        self.drawRightString(558, 750, "Lead Engineer: Bittu Sharma")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(54, 744, 558, 744)

        # Footer
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential — Developed by Bittu Sharma (Forward Deployed Engineer)")
        self.drawRightString(558, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def get_styles():
    styles = getSampleStyleSheet()

    # Primary colors
    c_primary = colors.HexColor("#0f172a")     # Slate 900
    c_accent = colors.HexColor("#059669")      # Emerald 600
    c_blue = colors.HexColor("#0284c7")        # Sky 600
    c_body = colors.HexColor("#1e293b")        # Slate 800
    c_muted = colors.HexColor("#64748b")       # Slate 500

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica",
        fontSize=13,
        leading=17,
        textColor=c_accent,
        spaceAfter=18,
    ))

    styles.add(ParagraphStyle(
        name="MetaLabel",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=c_primary,
    ))

    styles.add(ParagraphStyle(
        name="MetaValue",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=c_body,
    ))

    styles.add(ParagraphStyle(
        name="SecH1",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="SecH2",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=c_blue,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="CustomBody",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=c_body,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="BulletText",
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=c_body,
        leftIndent=14,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name="CalloutText",
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#065f46"),
    ))

    styles.add(ParagraphStyle(
        name="CodeBlock",
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    ))

    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    ))

    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=c_body,
    ))

    styles.add(ParagraphStyle(
        name="TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=c_primary,
    ))

    return styles


def make_callout(text: str, styles, title: str = "KEY HIGHLIGHT"):
    p_title = Paragraph(f"<b>{title}:</b> {text}", styles["CalloutText"])
    t = Table([[p_title]], colWidths=[504])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
        ("LINELEFT", (0, 0), (0, -1), 3.5, colors.HexColor("#10b981")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def build_cover_meta(meta_dict, styles):
    data = []
    for k, v in meta_dict.items():
        data.append([
            Paragraph(k, styles["MetaLabel"]),
            Paragraph(v, styles["MetaValue"]),
        ])
    t = Table(data, colWidths=[130, 374])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


# ==============================================================================
# 1. GENERATE PRD (Product Requirements Document)
# ==============================================================================
def generate_prd():
    pdf_path = DOCS_DIR / "PRD_Product_Requirements_Document.pdf"
    styles = get_styles()
    story = []

    class PRDCanvas(NumberedCanvas):
        doc_title = "Product Requirements Document (PRD)"

    # Title & Metadata
    story.append(Paragraph("Product Requirements Document", styles["DocTitle"]))
    story.append(Paragraph("Enterprise IT Support Agentic RAG Copilot", styles["DocSubtitle"]))

    meta = {
        "Document Version": "1.0.0 (Release Candidate)",
        "Customer / Org": "NovaRetail (Fictional 3,000-employee enterprise)",
        "Author / Lead Engineer": "Bittu Sharma (Forward Deployed Engineer - AI Systems)",
        "Target Audience": "Product Management, IT Leadership, Support Operations",
        "Approval Status": "Approved for Production Deployment",
        "Evaluation Score": "88.9% Live Pass Rate | 100% Mock Mode | 100% Routing Accuracy",
    }
    story.append(build_cover_meta(meta, styles))
    story.append(Spacer(1, 14))

    # Section 1
    story.append(Paragraph("1. Business Problem & Opportunity", styles["SecH1"]))
    story.append(Paragraph(
        "NovaRetail employs 3,000 corporate and retail operations staff. The internal IT team maintains a comprehensive "
        "library of standard operating procedures: VPN configuration, identity and password policies, MFA requirements, "
        "software deployment rules, and laptop troubleshooting guides. Despite this documentation, employees submit over "
        "1,200 repetitive support tickets monthly because internal knowledge is fragmented across file shares and wikis.",
        styles["CustomBody"]
    ))
    story.append(Paragraph(
        "Traditional keyword search generates dozens of search hits without synthesis. Furthermore, standard off-the-shelf "
        "chatbots hallucinate policy details or fail entirely when questions depend on external vendor uptime status "
        "(e.g., Microsoft 365, AWS, Okta outages).",
        styles["CustomBody"]
    ))
    story.append(make_callout(
        "The business objective is to deliver a trustworthy, self-correcting IT Support Copilot that reduces Tier-1 tickets "
        "by 40%+ by answering grounded questions from company documents first, evaluating evidence quality, and selectively "
        "querying external sources only when necessary.", styles, "BUSINESS OBJECTIVE"
    ))
    story.append(Spacer(1, 10))

    # Section 2
    story.append(Paragraph("2. User Personas & Core Journeys", styles["SecH1"]))
    table_data = [
        [Paragraph("Persona", styles["TableHeader"]), Paragraph("Role & Needs", styles["TableHeader"]), Paragraph("Pain Points & Solution", styles["TableHeader"])],
        [
            Paragraph("Enterprise Employee (Mark)", styles["TableCellBold"]),
            Paragraph("Remote retail operations manager needing fast laptop/VPN resolution without jargon.", styles["TableCell"]),
            Paragraph("Frustrated by waiting 4+ hours for IT tickets. Needs step-by-step verified instructions immediately.", styles["TableCell"]),
        ],
        [
            Paragraph("IT Helpdesk Lead (Priya)", styles["TableCellBold"]),
            Paragraph("Tier-2 Support engineer who handles escalated tickets and monitors system decisions.", styles["TableCell"]),
            Paragraph("Needs complete visibility into the AI's reasoning path, confidence %, and citations to verify answers.", styles["TableCell"]),
        ],
        [
            Paragraph("IT Systems Admin (David)", styles["TableCellBold"]),
            Paragraph("Knowledge manager responsible for publishing updated corporate security policies.", styles["TableCell"]),
            Paragraph("Cannot wait for engineering release cycles to update bots. Needs zero-code drag-and-drop document indexing.", styles["TableCell"]),
        ],
    ]
    t_personas = Table(table_data, colWidths=[120, 190, 194])
    t_personas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_personas)
    story.append(Spacer(1, 10))

    # Section 3
    story.append(Paragraph("3. Functional Requirements (FR)", styles["SecH1"]))
    fr_items = [
        ("FR-1: Query Routing Engine", "System must intelligently categorize incoming questions into KB queries (VPN, passwords, software) vs conversational greetings (direct response)."),
        ("FR-2: Private Knowledge Retrieval", "System must perform dense vector similarity search across Pinecone enterprise namespace, retrieving Top-4 semantic chunks."),
        ("FR-3: Self-Reflective Evidence Grading", "A structured LLM grader must score retrieved internal evidence as GOOD or WEAK based on direct sufficiency."),
        ("FR-4: External Search Fallback", "When internal evidence is WEAK, workflow must invoke Tavily search to fetch live vendor guides without human intervention."),
        ("FR-5: Query Rewriter & Retry Guard", "If web evidence is insufficient, system rewrites technical query with technical keywords, guarded by max_retries=1 to prevent infinite loops."),
        ("FR-6: Dual-Tab User Experience", "Web application must provide an interactive Chat Stream tab and an automated Result & Insights tab showing full metrics."),
        ("FR-7: Document Ingestion Portal", "Authorized admins can upload PDF, DOCX, TXT, and Markdown files with token chunking and immediate vector indexing."),
        ("FR-8: Audit Logging & Security", "All questions, routed sources, and execution traces must be durably stored in SQLite for compliance auditability."),
    ]
    for code, desc in fr_items:
        story.append(Paragraph(f"• <b>{code}</b>: {desc}", styles["BulletText"]))

    story.append(Spacer(1, 10))

    # Section 4
    story.append(Paragraph("4. User Experience & Application KPIs", styles["SecH1"]))
    story.append(Paragraph(
        "The user experience is designed with an enterprise dark-mode theme featuring a dual-tab dashboard:",
        styles["CustomBody"]
    ))
    story.append(Paragraph("• <b>[1] Chat Tab:</b> Fast conversation stream with numbered bubbles (#1 You, #1 Agent Response) and suggestion pills.", styles["BulletText"]))
    story.append(Paragraph("• <b>[2] Result & Insights Tab:</b> Auto-switched upon query completion, displaying Query ID, 96% Evidence Confidence, 95% Groundedness Match, Latency, Cited Sources, and Decision Trace steps.", styles["BulletText"]))
    story.append(Paragraph("• <b>KPI Targets:</b> Routing Accuracy >= 95% (Achieved 100%), Pass Rate >= 85% (Achieved 88.9% live, 100% mock), Average Latency < 15 seconds.", styles["BulletText"]))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    doc.build(story, canvasmaker=PRDCanvas)
    print(f"Generated PRD: {pdf_path}")


# ==============================================================================
# 2. GENERATE TRD (Technical Requirements Document)
# ==============================================================================
def generate_trd():
    pdf_path = DOCS_DIR / "TRD_Technical_Requirements_Document.pdf"
    styles = get_styles()
    story = []

    class TRDCanvas(NumberedCanvas):
        doc_title = "Technical Requirements Document (TRD)"

    # Title & Metadata
    story.append(Paragraph("Technical Requirements Document", styles["DocTitle"]))
    story.append(Paragraph("Enterprise IT Support Agentic RAG Copilot", styles["DocSubtitle"]))

    meta = {
        "Document Version": "1.0.0 (Production Architecture)",
        "Technology Stack": "LangGraph, FastAPI, Pinecone, Groq (gpt-oss-120b), Tavily, SQLite",
        "Author / Lead Engineer": "Bittu Sharma (FDE Systems Architect & AI Engineer)",
        "Status": "Architecture Verified & Tested (38 Unit Tests Passed)",
        "Vector Engine": "Pinecone Serverless (AWS us-east-1, Cosine, 384-dim)",
        "Embedding Model": "sentence-transformers/all-MiniLM-L6-v2 (Normalized)",
    }
    story.append(build_cover_meta(meta, styles))
    story.append(Spacer(1, 14))

    # Section 1
    story.append(Paragraph("1. System Architecture & Component Design", styles["SecH1"]))
    story.append(Paragraph(
        "The system decouples user presentation from the agentic control plane. FastAPI provides high-throughput "
        "asynchronous HTTP endpoints, while LangGraph manages stateful graph traversal with cyclic loop control.",
        styles["CustomBody"]
    ))

    arch_data = [
        [Paragraph("Layer", styles["TableHeader"]), Paragraph("Technology", styles["TableHeader"]), Paragraph("Technical Responsibility", styles["TableHeader"])],
        [
            Paragraph("Presentation", styles["TableCellBold"]),
            Paragraph("Vanilla HTML5 / CSS3 / ES6+", styles["TableCell"]),
            Paragraph("Dual-tab state, real-time KPI progress bars, trace visualization, no external bloated dependencies.", styles["TableCell"]),
        ],
        [
            Paragraph("API Gateway", styles["TableCellBold"]),
            Paragraph("FastAPI 0.116 / Uvicorn", styles["TableCell"]),
            Paragraph("REST endpoints (/api/chat, /api/health, /api/ingest), header auth, CORS, async request dispatching.", styles["TableCell"]),
        ],
        [
            Paragraph("Graph Engine", styles["TableCellBold"]),
            Paragraph("LangGraph 1.1.10", styles["TableCell"]),
            Paragraph("StateGraph execution: route -> retrieve -> grade -> web fallback -> retry -> answer generation.", styles["TableCell"]),
        ],
        [
            Paragraph("Reasoning LLM", styles["TableCellBold"]),
            Paragraph("Groq (openai/gpt-oss-120b)", styles["TableCell"]),
            Paragraph("Ultra-fast sub-second inference for routing, grading, query rewriting, and grounded response synthesis.", styles["TableCell"]),
        ],
        [
            Paragraph("Vector Index", styles["TableCellBold"]),
            Paragraph("Pinecone Serverless (v7.3)", styles["TableCell"]),
            Paragraph("Enterprise namespace partitioning, 384-dimensional cosine index, dynamic index lifecycle management.", styles["TableCell"]),
        ],
        [
            Paragraph("Audit Persistence", styles["TableCellBold"]),
            Paragraph("SQLite 3 (WAL mode)", styles["TableCell"]),
            Paragraph("Local zero-latency write of query timestamps, routed sources, and JSON-serialized decision traces.", styles["TableCell"]),
        ],
    ]
    t_arch = Table(arch_data, colWidths=[80, 140, 284])
    t_arch.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    # Section 2
    story.append(Paragraph("2. LangGraph State Machine & Node Flow", styles["SecH1"]))
    story.append(Paragraph(
        "The shared agent state is defined via typing.TypedDict with explicit schemas for decisions and grades:",
        styles["CustomBody"]
    ))
    story.append(Paragraph("• <b>AgentState Schema:</b> question, current_query, kb_docs (List[Document]), web_results (str), kb_grade (Literal['good','weak']), web_grade, answer, source_used, retry_count, trace (List[str]), citations (List[Dict]).", styles["BulletText"]))
    story.append(Paragraph("• <b>Conditional Branch 1 (Router):</b> route_after_router inspects source_used; dispatches to retrieve_kb or direct_answer.", styles["BulletText"]))
    story.append(Paragraph("• <b>Conditional Branch 2 (KB Grade):</b> after_kb routes to generate_from_kb if 'good', else searches external web via Tavily.", styles["BulletText"]))
    story.append(Paragraph("• <b>Conditional Branch 3 (Web Grade & Loop Guard):</b> after_web routes to generate_from_web if 'good'. If 'weak' and retry_count < max_retries (1), it rewrites the query and retries KB retrieval; otherwise terminates at insufficient.", styles["BulletText"]))
    story.append(make_callout(
        "Deterministic Loop Prevention: retry_count is incremented on every rewrite_query execution. When retry_count reaches settings.max_retries (1), the state machine halts with an actionable fallback message to prevent runaway API spend.",
        styles, "SAFETY LOOP GUARD"
    ))
    story.append(Spacer(1, 10))

    # Section 3
    story.append(Paragraph("3. REST API Specifications", styles["SecH1"]))
    api_items = [
        ("POST /api/chat", "Request: { question: str (2-3000 chars) }\nResponse: { answer, source_used, trace, citations, rewritten_query, confidence_score, groundedness_score }"),
        ("GET /api/health", "Response: { status: 'ok', service: 'Enterprise IT Support Agentic RAG Copilot' }"),
        ("POST /api/ingest", "Headers: X-Admin-Key: <ADMIN_API_KEY>\nBody: Multipart form-data with file (.pdf, .txt, .md, .docx)\nResponse: { message, file, chunks, ids_created }"),
    ]
    for endpoint, spec in api_items:
        story.append(Paragraph(f"<b>{endpoint}</b>", styles["SecH2"]))
        story.append(Paragraph(spec.replace("\n", "<br/>"), styles["CodeBlock"]))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    doc.build(story, canvasmaker=TRDCanvas)
    print(f"Generated TRD: {pdf_path}")


# ==============================================================================
# 3. GENERATE SRD (Software Requirements Document)
# ==============================================================================
def generate_srd():
    pdf_path = DOCS_DIR / "SRD_Software_Requirements_Document.pdf"
    styles = get_styles()
    story = []

    class SRDCanvas(NumberedCanvas):
        doc_title = "Software Requirements Document (SRD)"

    # Title & Metadata
    story.append(Paragraph("Software Requirements Document", styles["DocTitle"]))
    story.append(Paragraph("Enterprise IT Support Agentic RAG Copilot", styles["DocSubtitle"]))

    meta = {
        "Document Version": "1.0.0 (IEEE 830 Conformance)",
        "Standard": "IEEE Std 830-1998 Software Requirements Specification",
        "Author / Lead Engineer": "Bittu Sharma (FDE Quality Engineering & Systems Infrastructure)",
        "Test Suite Status": "38 of 38 Tests Passing (0.77s execution time)",
        "Python Runtime": "Python 3.11 / 3.12 / 3.13 Compatible",
        "Packaging": "Dockerized Multi-stage Container & Virtualenv",
    }
    story.append(build_cover_meta(meta, styles))
    story.append(Spacer(1, 14))

    # Section 1
    story.append(Paragraph("1. System Environment & Hardware Requirements", styles["SecH1"]))
    story.append(Paragraph(
        "The software operates as a standalone microservice or containerized daemon capable of running on enterprise "
        "on-premises Linux/Windows hosts or AWS/GCP cloud virtual machines.",
        styles["CustomBody"]
    ))
    sys_reqs = [
        ("Host Operating System", "Windows 10/11, Ubuntu 22.04 LTS+, macOS Sonoma+, or Debian-based Docker container."),
        ("CPU & Memory", "Minimum: 2 vCPU cores, 4GB RAM. Recommended for production: 4 vCPU cores, 8GB RAM."),
        ("Disk Storage", "500MB free disk space for application files, SQLite audit database, and uploaded documents."),
        ("Network Connectivity", "Outbound HTTPS (port 443) access to Groq API (api.groq.com), Pinecone API, and Tavily API."),
    ]
    for label, val in sys_reqs:
        story.append(Paragraph(f"• <b>{label}:</b> {val}", styles["BulletText"]))

    story.append(Spacer(1, 10))

    # Section 2
    story.append(Paragraph("2. Software Dependency Matrix", styles["SecH1"]))
    deps_data = [
        [Paragraph("Package", styles["TableHeader"]), Paragraph("Version", styles["TableHeader"]), Paragraph("Technical Purpose in Copilot", styles["TableHeader"])],
        [Paragraph("fastapi", styles["TableCellBold"]), Paragraph("0.116.1", styles["TableCell"]), Paragraph("High-performance asynchronous backend API framework", styles["TableCell"])],
        [Paragraph("uvicorn[standard]", styles["TableCellBold"]), Paragraph("0.35.0", styles["TableCell"]), Paragraph("Lightning-fast ASGI production web server", styles["TableCell"])],
        [Paragraph("langgraph", styles["TableCellBold"]), Paragraph("1.1.10", styles["TableCell"]), Paragraph("StateGraph cyclic agentic decision orchestrator", styles["TableCell"])],
        [Paragraph("langchain-groq", styles["TableCellBold"]), Paragraph("1.1.3", styles["TableCell"]), Paragraph("Integration client for Groq high-speed LLM inference", styles["TableCell"])],
        [Paragraph("sentence-transformers", styles["TableCellBold"]), Paragraph("6.0.0", styles["TableCell"]), Paragraph("HuggingFace all-MiniLM-L6-v2 dense vector embedding model", styles["TableCell"])],
        [Paragraph("pinecone", styles["TableCellBold"]), Paragraph("7.3.0", styles["TableCell"]), Paragraph("Pinecone Serverless vector database SDK", styles["TableCell"])],
        [Paragraph("langchain-tavily", styles["TableCellBold"]), Paragraph("0.2.18", styles["TableCell"]), Paragraph("Real-time vendor and web search tool client", styles["TableCell"])],
        [Paragraph("pytest", styles["TableCellBold"]), Paragraph("8.3.4", styles["TableCell"]), Paragraph("Automated unit, integration, and dataset validation test runner", styles["TableCell"])],
        [Paragraph("httpx", styles["TableCellBold"]), Paragraph("0.28.1", styles["TableCell"]), Paragraph("FastAPI TestClient HTTP testing client", styles["TableCell"])],
    ]
    t_deps = Table(deps_data, colWidths=[120, 74, 310])
    t_deps.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_deps)
    story.append(Spacer(1, 10))

    # Section 3
    story.append(Paragraph("3. Verification, Validation & Test Matrix", styles["SecH1"]))
    story.append(Paragraph(
        "The application includes an automated test suite guaranteeing regression-free updates and verified accuracy:",
        styles["CustomBody"]
    ))
    test_cases = [
        ("tests/test_dataset_validation.py (10 Tests)", "Validates existence, UTF-8 integrity, and section policies of company_it_handbook.md and service_desk_runbook.md. Validates chunking boundaries and eval_dataset.json schema."),
        ("tests/test_api_endpoints.py (9 Tests)", "Validates GET /api/health, UI rendering, POST /api/chat error handling, input validation (422), audit database persistence, and POST /api/ingest security authorization."),
        ("tests/test_evaluation_service.py (9 Tests)", "Validates keyword coverage algorithms, trace route extraction, sample pass/fail thresholding, and mock evaluation reporting."),
        ("tests/test_workflow_units.py (10 Tests)", "Unit tests all LangGraph nodes (routing, grading, rewriting) with external LLMs mocked for fast deterministic execution."),
    ]
    for name, detail in test_cases:
        story.append(Paragraph(f"• <b>{name}:</b> {detail}", styles["BulletText"]))

    story.append(make_callout(
        "Continuous Quality Verification: All 38 automated test cases execute cleanly in under 1 second (0.77s - 1.03s), making the test suite ideal for pre-commit hooks and CI/CD deployment pipelines.",
        styles, "VERIFIED TESTING STATUS"
    ))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    doc.build(story, canvasmaker=SRDCanvas)
    print(f"Generated SRD: {pdf_path}")


def main():
    print("=" * 70)
    print("Generating Professional Enterprise PDF Specifications (PRD, TRD, SRD)...")
    print("=" * 70)
    generate_prd()
    generate_trd()
    generate_srd()
    print("=" * 70)
    print("All 3 PDF specifications generated successfully in docs/ folder!")
    print("=" * 70)


if __name__ == "__main__":
    main()
