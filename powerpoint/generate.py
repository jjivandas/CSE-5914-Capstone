"""
StockRAG Progress Presentation Generator
Black & Green theme | CSE 5914 Capstone
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx.oxml.ns as nsmap
from lxml import etree

# ── Colors ──────────────────────────────────────────────────────────────────
BLACK       = RGBColor(0x0A, 0x0A, 0x0A)   # near-black background
DARK_CARD   = RGBColor(0x14, 0x14, 0x14)   # card / section bg
GREEN       = RGBColor(0x00, 0xC8, 0x53)   # primary accent
GREEN_DIM   = RGBColor(0x00, 0x7A, 0x33)   # secondary/dim green
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
GRAY        = RGBColor(0xAA, 0xAA, 0xAA)
DONE_GREEN  = RGBColor(0x00, 0xE6, 0x76)
TODO_AMBER  = RGBColor(0xFF, 0xD7, 0x40)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

# ── Helpers ──────────────────────────────────────────────────────────────────

def new_prs():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    layout = prs.slide_layouts[6]   # completely blank
    return prs.slides.add_slide(layout)


def fill_bg(slide, color=BLACK):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, color):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_text(slide, text, left, top, width, height,
             font_size=18, bold=False, color=WHITE,
             align=PP_ALIGN.LEFT, italic=False):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.italic = italic
    return txBox


def add_paragraph(tf, text, font_size=14, bold=False,
                  color=WHITE, indent=0, bullet=False, space_before=0):
    from pptx.util import Pt as _Pt
    p = tf.add_paragraph()
    p.space_before = _Pt(space_before)
    if indent:
        p.level = indent
    run = p.add_run()
    run.text = ("• " if bullet else "") + text
    run.font.size = _Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    return p


def accent_bar(slide, y_pos=Inches(0.62), height=Inches(0.04)):
    """Thin green bar across the top of a content slide."""
    add_rect(slide, 0, y_pos, SLIDE_W, height, GREEN)


def slide_header(slide, title, subtitle=None):
    """Standard content slide header row."""
    accent_bar(slide)
    add_text(slide, title,
             left=Inches(0.5), top=Inches(0.08),
             width=Inches(9), height=Inches(0.55),
             font_size=28, bold=True, color=GREEN)
    if subtitle:
        add_text(slide, subtitle,
                 left=Inches(0.5), top=Inches(0.68),
                 width=Inches(12), height=Inches(0.35),
                 font_size=13, color=GRAY, italic=True)


def tag(slide, label, color=GREEN_DIM, text_color=GREEN,
        left=Inches(10.3), top=Inches(0.1)):
    r = add_rect(slide, left, top, Inches(2.7), Inches(0.4), color)
    add_text(slide, label,
             left=left, top=top,
             width=Inches(2.7), height=Inches(0.4),
             font_size=11, bold=True, color=text_color,
             align=PP_ALIGN.CENTER)


def done_todo_cols(slide, done_items, todo_items,
                   done_label="✔  What's Done",
                   todo_label="◉  What's Left"):
    """Two-column done / todo layout."""
    col_top  = Inches(1.15)
    col_h    = Inches(5.7)
    lbl_h    = Inches(0.4)
    body_top = col_top + lbl_h + Inches(0.08)
    body_h   = col_h - lbl_h - Inches(0.08)

    # Done column
    add_rect(slide, Inches(0.35), col_top, Inches(5.9), col_h, DARK_CARD)
    add_text(slide, done_label,
             Inches(0.45), col_top + Inches(0.05),
             Inches(5.7), lbl_h,
             font_size=13, bold=True, color=DONE_GREEN)
    tb = slide.shapes.add_textbox(Inches(0.45), body_top, Inches(5.7), body_h)
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for item in done_items:
        if first:
            p = tf.paragraphs[0]; first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(4)
        run = p.add_run()
        run.text = "▸  " + item
        run.font.size = Pt(13)
        run.font.color.rgb = WHITE

    # Todo column
    add_rect(slide, Inches(6.6), col_top, Inches(6.4), col_h, DARK_CARD)
    add_text(slide, todo_label,
             Inches(6.7), col_top + Inches(0.05),
             Inches(6.2), lbl_h,
             font_size=13, bold=True, color=TODO_AMBER)
    tb2 = slide.shapes.add_textbox(Inches(6.7), body_top, Inches(6.2), body_h)
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    first = True
    for item in todo_items:
        if first:
            p = tf2.paragraphs[0]; first = False
        else:
            p = tf2.add_paragraph()
        p.space_before = Pt(4)
        run = p.add_run()
        run.text = "▸  " + item
        run.font.size = Pt(13)
        run.font.color.rgb = WHITE


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDES
# ═══════════════════════════════════════════════════════════════════════════

def slide_01_title(prs):
    s = blank_slide(prs)
    fill_bg(s)

    # Green diagonal accent block (top-right)
    add_rect(s, Inches(9.8), 0, Inches(3.53), Inches(7.5), RGBColor(0x00, 0x3A, 0x18))

    # Thin left border bar
    add_rect(s, 0, 0, Inches(0.08), SLIDE_H, GREEN)

    # App name
    add_text(s, "StockRAG", Inches(0.5), Inches(1.6),
             Inches(9), Inches(1.6),
             font_size=80, bold=True, color=GREEN)

    # Tagline
    add_text(s, "AI-Powered Stock Discovery",
             Inches(0.5), Inches(3.1), Inches(9), Inches(0.7),
             font_size=28, color=WHITE)

    # Sub-line
    add_text(s, "CSE 5914 Capstone  ·  Progress Update  ·  Spring 2026",
             Inches(0.5), Inches(3.75), Inches(9.2), Inches(0.45),
             font_size=15, color=GRAY)

    # Divider line
    add_rect(s, Inches(0.5), Inches(4.25), Inches(5), Inches(0.03), GREEN_DIM)

    # Team line
    add_text(s, "Michael Gorman  ·  Alex Fizer  ·  Arnav Rajashekara  ·  Manu  ·  Krish Patel  ·  Jay Jivandas",
             Inches(0.5), Inches(4.35), Inches(9.1), Inches(0.4),
             font_size=12, color=GRAY)

    # Right-column label
    add_text(s, "CAPSTONE\nPROJECT", Inches(10.1), Inches(2.8),
             Inches(3), Inches(1.5),
             font_size=32, bold=True, color=GREEN,
             align=PP_ALIGN.CENTER)


def slide_02_overview(prs):
    s = blank_slide(prs)
    fill_bg(s)
    slide_header(s, "What We're Building",
                 "A conversational AI for natural-language stock discovery")

    # Three pillars
    cols = [
        ("💬  Frontend",  "React chat UI with\nAI-generated stock cards",  Inches(0.5)),
        ("⚙  Backend",   "FastAPI connecting the\nUI to the RAG engine",   Inches(4.6)),
        ("🔍  RAG Pipeline", "SEC data → embeddings\n→ ChromaDB → Gemini LLM", Inches(8.7)),
    ]
    for title, body, left in cols:
        add_rect(s, left, Inches(1.15), Inches(3.9), Inches(2.1), DARK_CARD)
        add_text(s, title, left + Inches(0.15), Inches(1.22),
                 Inches(3.6), Inches(0.5),
                 font_size=15, bold=True, color=GREEN)
        add_text(s, body, left + Inches(0.15), Inches(1.7),
                 Inches(3.6), Inches(0.75),
                 font_size=13, color=WHITE)

    # Example query box
    add_rect(s, Inches(0.5), Inches(3.5), Inches(12.3), Inches(0.75), RGBColor(0x00, 0x2A, 0x12))
    add_text(s, '🔎  Example query:  "Cybersecurity stocks with >20% revenue growth and low debt"',
             Inches(0.65), Inches(3.57), Inches(12), Inches(0.6),
             font_size=14, color=GREEN, italic=True)

    # Response description
    tb = slide.shapes.add_textbox if False else \
         s.shapes.add_textbox(Inches(0.5), Inches(4.4), Inches(12.3), Inches(2.6))
    tf = tb.text_frame
    tf.word_wrap = True
    items = [
        "Users type free-form financial questions into the chat interface",
        "The backend routes the query through a RAG pipeline backed by SEC EDGAR data",
        "Gemini LLM generates a natural-language explanation + ranked stock recommendations",
        "Frontend renders rich StockCards: ticker, match %, sector, P/E ratio, 'Why it fits'",
    ]
    first = True
    for item in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_before = Pt(5)
        run = p.add_run()
        run.text = "▸  " + item
        run.font.size = Pt(13)
        run.font.color.rgb = WHITE


def slide_03_architecture(prs):
    s = blank_slide(prs)
    fill_bg(s)
    slide_header(s, "System Architecture", "End-to-end data flow")

    # Flow boxes
    boxes = [
        ("USER\nQUERY",         Inches(0.3),  RGBColor(0x1A, 0x1A, 0x1A)),
        ("REACT\nFRONTEND",     Inches(2.3),  RGBColor(0x00, 0x3A, 0x18)),
        ("FASTAPI\nBACKEND",    Inches(4.55), RGBColor(0x00, 0x3A, 0x18)),
        ("RAG\nPIPELINE",       Inches(6.8),  RGBColor(0x00, 0x3A, 0x18)),
        ("CHROMADB\nVECTOR DB", Inches(9.05), RGBColor(0x1A, 0x1A, 0x1A)),
        ("GEMINI\nLLM",         Inches(11.3), RGBColor(0x1A, 0x1A, 0x1A)),
    ]
    box_w = Inches(1.9)
    box_h = Inches(1.1)
    box_y = Inches(1.7)

    for label, left, bg in boxes:
        add_rect(s, left, box_y, box_w, box_h, bg)
        # Green border effect via thin overlay rects
        add_rect(s, left, box_y, box_w, Inches(0.04), GREEN_DIM)
        add_text(s, label, left + Inches(0.05), box_y + Inches(0.1),
                 box_w - Inches(0.1), box_h - Inches(0.15),
                 font_size=11, bold=True, color=GREEN, align=PP_ALIGN.CENTER)

    # Arrows between boxes
    arrow_y = box_y + Inches(0.5)
    for i in range(len(boxes) - 1):
        ax = boxes[i][1] + box_w + Inches(0.02)
        add_rect(s, ax, arrow_y - Inches(0.03), Inches(0.2), Inches(0.06), GREEN)

    # Return path label
    add_rect(s, Inches(0.3), Inches(3.1), Inches(12.9), Inches(0.04), GREEN_DIM)
    add_text(s, "◀  Recommendations returned to user",
             Inches(0.3), Inches(3.15), Inches(12.9), Inches(0.35),
             font_size=11, color=GRAY, italic=True, align=PP_ALIGN.CENTER)

    # Component descriptions
    descs = [
        (Inches(0.3),  "Enters natural\nlanguage query"),
        (Inches(2.3),  "Chat UI + StockCards\nAxios API client"),
        (Inches(4.55), "Routes, models,\nvalidation layer"),
        (Inches(6.8),  "Embed → search\n→ prompt LLM"),
        (Inches(9.05), "19k+ company\nvectors (SEC data)"),
        (Inches(11.3), "Explanation +\nranked results"),
    ]
    for left, desc in descs:
        add_text(s, desc, left, Inches(3.6), box_w, Inches(0.75),
                 font_size=10, color=GRAY, align=PP_ALIGN.CENTER)

    # Tech stack row
    stack_items = [
        ("React + TypeScript",  Inches(0.5)),
        ("Vite + Mantine UI",   Inches(3.1)),
        ("FastAPI + Pydantic",  Inches(5.7)),
        ("ChromaDB",            Inches(8.3)),
        ("all-MiniLM-L6-v2",   Inches(10.0)),
        ("Google Gemini",       Inches(11.7)),
    ]
    add_rect(s, Inches(0.3), Inches(6.5), Inches(12.9), Inches(0.04), RGBColor(0x22, 0x22, 0x22))
    add_text(s, "TECH STACK",
             Inches(0.3), Inches(6.6), Inches(2), Inches(0.35),
             font_size=9, bold=True, color=GRAY)
    for label, left in stack_items:
        add_text(s, label, left, Inches(6.55), Inches(1.6), Inches(0.4),
                 font_size=9, color=GREEN_DIM, align=PP_ALIGN.CENTER)


def slide_04_frontend(prs):
    s = blank_slide(prs)
    fill_bg(s)
    slide_header(s, "Frontend", "Michael Gorman & Alex Fizer")
    tag(s, "React + TypeScript + Mantine")

    done = [
        "Full chat interface with AppHeader, MainLayout",
        "WelcomeScreen with 4 example query chips",
        "MessageList with smooth auto-scroll",
        "StockCards: ticker, match %, sector, P/E, 'Why it fits'",
        "Loading skeletons & fade-in animations",
        "Custom dark / green Mantine theme",
        "useChat hook — optimistic UI, error handling",
        "useAutoScroll + useChatInput hooks",
        "Axios API client with mock data fallback",
        "TypeScript contracts matching backend models",
        "Strict code rules: <15 line functions, no prop drilling",
    ]
    todo = [
        "Login & Signup pages (Ticket-9)",
        "User Profile page with settings (Ticket-10)",
        "Portfolio state management — Zustand/Context (Ticket-11)",
        "Portfolio dashboard with charts (Recharts) (Ticket-12)",
        "Error toast notifications (Ticket-13)",
        "Connect frontend to live backend (remove mocks)",
    ]
    done_todo_cols(s, done, todo)


def slide_05_backend(prs):
    s = blank_slide(prs)
    fill_bg(s)
    slide_header(s, "Backend", "Arnav Rajashekara & Manu")
    tag(s, "FastAPI + Pydantic + ChromaDB")

    done = [
        "FastAPI app scaffolded (main.py, config.py)",
        "Pydantic v2 settings — Gemini key, ChromaDB dir, port",
        "Full API data models: RecommendationRequest,",
        "  StockRecommendation, RecommendationResponse,",
        "  HealthCheckResponse, StatsResponse",
        "Route structure: GET /health, GET /stats,",
        "  POST /api/recommendations",
        "Frontend-aligned API contracts",
        "Test notebook for model validation",
        "Docker Compose configuration",
    ]
    todo = [
        "LLM service: Gemini primary, Groq fallback",
        "ChromaDB vector DB interface (vector_db.py)",
        "RAG pipeline orchestration (pipeline.py)",
        "Embedding generation module (embeddings.py)",
        "Retrieval / similarity search (retrieval.py)",
        "Data enrichment: yfinance + Finnhub APIs",
        "Data validation & custom error handlers",
        "requirements.txt + .env.example documentation",
        "End-to-end integration test (mock → live)",
    ]
    done_todo_cols(s, done, todo)


def slide_06_rag(prs):
    s = blank_slide(prs)
    fill_bg(s)
    slide_header(s, "RAG Pipeline", "Krish Patel & Jay Jivandas")
    tag(s, "SEC EDGAR + ChromaDB + Gemini")

    done = [
        "Analyzed 19,215 SEC EDGAR company filings",
        "18.4 GB of raw financial data mapped and documented",
        "Identified key metrics: balance sheet, income",
        "  statement, cash flow, share data",
        "Taxonomies documented: us-gaap (~85%),",
        "  dei, srt, invest, ifrs-full",
        "Flagged 2,647 empty files to skip in pipeline",
        "Project architecture + module structure designed",
        "Full backend folder structure scaffolded",
    ]
    todo = [
        "Parse & clean SEC EDGAR JSON files",
        "Finnhub API integration for real-time prices",
        "Generate embeddings using all-MiniLM-L6-v2",
        "Populate ChromaDB with company vectors",
        "Build similarity search / retrieval logic",
        "Create backend interface for API to call",
        "Prompt template engineering for Gemini",
        "End-to-end pipeline test: query → results",
    ]
    done_todo_cols(s, done, todo)


def slide_07_integration(prs):
    s = blank_slide(prs)
    fill_bg(s)
    slide_header(s, "How It All Ties Together",
                 "Integration plan — bridging three independent workstreams")

    # Three phase blocks
    phases = [
        ("Phase 1\nData Ready",
         "RAG team finishes parsing SEC EDGAR\nfiles and populates ChromaDB\nwith stock embeddings",
         Inches(0.4), GREEN_DIM),
        ("Phase 2\nBackend Live",
         "Backend wires LLM service + vector DB\ninto the /recommendations route.\nMock responses replaced with real AI",
         Inches(4.6), RGBColor(0x00, 0x4D, 0x20)),
        ("Phase 3\nFull Integration",
         "Frontend switches from mock client\nto live API. Auth + portfolio features\nadded on top of working pipeline",
         Inches(8.8), RGBColor(0x00, 0x3A, 0x18)),
    ]
    for label, body, left, bg in phases:
        add_rect(s, left, Inches(1.15), Inches(3.8), Inches(2.4), bg)
        add_text(s, label, left + Inches(0.15), Inches(1.2),
                 Inches(3.5), Inches(0.75),
                 font_size=16, bold=True, color=GREEN)
        add_text(s, body, left + Inches(0.15), Inches(1.9),
                 Inches(3.5), Inches(1.4),
                 font_size=12, color=WHITE)

    # Arrows between phases
    for ax in [Inches(4.25), Inches(8.45)]:
        add_rect(s, ax, Inches(2.05), Inches(0.3), Inches(0.08), GREEN)

    # Current state note
    add_rect(s, Inches(0.4), Inches(3.8), Inches(12.5), Inches(0.8),
             RGBColor(0x0F, 0x0F, 0x0F))
    add_rect(s, Inches(0.4), Inches(3.8), Inches(0.06), Inches(0.8), GREEN)
    add_text(s, "Current state:  Frontend runs on mock data and is fully functional. "
                "Backend has defined contracts. RAG data analysis complete. "
                "The critical path is: SEC data processing → embeddings → ChromaDB → Backend services → Live frontend.",
             Inches(0.6), Inches(3.85), Inches(12.1), Inches(0.7),
             font_size=12, color=GRAY)

    # Key integration points
    tb = s.shapes.add_textbox(Inches(0.4), Inches(4.8), Inches(12.5), Inches(2.3))
    tf = tb.text_frame
    tf.word_wrap = True
    points = [
        ("Frontend → Backend", "TypeScript interfaces match Pydantic models exactly. Switch VITE_API_BASE_URL env var to go live."),
        ("Backend → RAG",      "routes.py already imports rag.pipeline — implementation just needs to be filled in."),
        ("RAG → Data",         "SEC EDGAR provides 19k+ companies. Finnhub adds real-time price enrichment on top."),
    ]
    first = True
    for key, val in points:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_before = Pt(6)
        run = p.add_run(); run.text = f"▸  {key}: "; run.font.size = Pt(12)
        run.font.bold = True; run.font.color.rgb = GREEN
        run2 = p.add_run(); run2.text = val; run2.font.size = Pt(12)
        run2.font.color.rgb = WHITE


def slide_08_next_steps(prs):
    s = blank_slide(prs)
    fill_bg(s)
    slide_header(s, "Next Steps", "Priorities across all three teams")

    # Priority columns
    teams = [
        ("Frontend",
         ["Connect to live API (remove mocks)",
          "Login / Signup pages",
          "User profile page",
          "Portfolio state & dashboard",
          "Error notification toasts"],
         Inches(0.35)),
        ("Backend",
         ["Implement LLM service (Gemini)",
          "ChromaDB vector DB interface",
          "Wire RAG pipeline into routes",
          "Data enrichment (yfinance + Finnhub)",
          "Requirements.txt + env docs"],
         Inches(4.55)),
        ("RAG Pipeline",
         ["Parse & clean SEC EDGAR data",
          "Generate embeddings (MiniLM)",
          "Populate ChromaDB",
          "Build retrieval / search logic",
          "Finnhub integration"],
         Inches(8.75)),
    ]
    for title, items, left in teams:
        add_rect(s, left, Inches(1.15), Inches(3.9), Inches(5.7), DARK_CARD)
        add_rect(s, left, Inches(1.15), Inches(3.9), Inches(0.45), GREEN_DIM)
        add_text(s, title, left + Inches(0.15), Inches(1.17),
                 Inches(3.6), Inches(0.4),
                 font_size=15, bold=True, color=WHITE)
        tb = s.shapes.add_textbox(left + Inches(0.15), Inches(1.7),
                                   Inches(3.6), Inches(5.0))
        tf = tb.text_frame; tf.word_wrap = True
        first = True
        for item in items:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.space_before = Pt(10)
            run = p.add_run()
            run.text = "→  " + item
            run.font.size = Pt(13)
            run.font.color.rgb = WHITE


def slide_09_closing(prs):
    s = blank_slide(prs)
    fill_bg(s)

    add_rect(s, 0, 0, Inches(0.08), SLIDE_H, GREEN)
    add_rect(s, Inches(9.8), 0, Inches(3.53), SLIDE_H, RGBColor(0x00, 0x3A, 0x18))

    add_text(s, "Questions?",
             Inches(0.5), Inches(2.2), Inches(9), Inches(1.4),
             font_size=72, bold=True, color=GREEN)

    add_text(s, "StockRAG  ·  CSE 5914 Capstone  ·  Spring 2026",
             Inches(0.5), Inches(3.6), Inches(9), Inches(0.45),
             font_size=16, color=GRAY)

    add_rect(s, Inches(0.5), Inches(4.15), Inches(4), Inches(0.03), GREEN_DIM)

    add_text(s, "github.com/jjivandas/CSE-5914-Capstone",
             Inches(0.5), Inches(4.25), Inches(9), Inches(0.4),
             font_size=12, color=GRAY, italic=True)

    add_text(s, "THANK\nYOU", Inches(10.1), Inches(2.8),
             Inches(3), Inches(1.5),
             font_size=32, bold=True, color=GREEN,
             align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    prs = new_prs()

    slide_01_title(prs)
    slide_02_overview(prs)
    slide_03_architecture(prs)
    slide_04_frontend(prs)
    slide_05_backend(prs)
    slide_06_rag(prs)
    slide_07_integration(prs)
    slide_08_next_steps(prs)
    slide_09_closing(prs)

    out = "stockrag_progress.pptx"
    prs.save(out)
    print(f"Saved → {out}")


if __name__ == "__main__":
    main()
