"""Generate IDAES progress update deck for 2026-05-21 meeting.

Topics:
1. 2035 PCM operational violation analysis (no-extreme vs extreme)
2. GTEP codebase divergence: main vs commitment_period branch
3. Version alignment question for collaborators
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt


ROOT = Path("/Users/yilu/Documents/GitHub/idaes-gtep")
OUT_PPTX = ROOT / "quality_reports/decks/2026-05-21_idaes_progress_update.pptx"

DARK_BLUE = RGBColor(0x1B, 0x3A, 0x5C)
MEDIUM_BLUE = RGBColor(0x2C, 0x5F, 0x8A)
LIGHT_BLUE = RGBColor(0xD6, 0xE8, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x33, 0x33, 0x33)
GRAY = RGBColor(0x66, 0x66, 0x66)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x27, 0xAE, 0x60)
AMBER = RGBColor(0xF3, 0x9C, 0x12)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def add_background(slide, color=WHITE):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_title_bar(slide, title_text, subtitle_text=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(1.2))
    shape.fill.solid()
    shape.fill.fore_color.rgb = DARK_BLUE
    shape.line.fill.background()

    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(31)
    p.font.color.rgb = WHITE
    p.font.bold = True
    p.alignment = PP_ALIGN.LEFT
    tf.margin_left = Inches(0.6)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    if subtitle_text:
        shape2 = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, Inches(1.2), SLIDE_W, Inches(0.45)
        )
        shape2.fill.solid()
        shape2.fill.fore_color.rgb = MEDIUM_BLUE
        shape2.line.fill.background()
        tf2 = shape2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = subtitle_text
        p2.font.size = Pt(16)
        p2.font.color.rgb = RGBColor(0xCC, 0xDD, 0xEE)
        p2.font.italic = True
        p2.alignment = PP_ALIGN.LEFT
        tf2.margin_left = Inches(0.6)
        tf2.vertical_anchor = MSO_ANCHOR.MIDDLE
        return Inches(1.85)
    return Inches(1.4)


def add_bullet_box(slide, left, top, width, height, bullets, font_size=18):
    tx_box = slide.shapes.add_textbox(left, top, width, height)
    tf = tx_box.text_frame
    tf.word_wrap = True
    for idx, b in enumerate(bullets):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.level = b.get("level", 0)
        p.space_after = Pt(b.get("space_after", 5))
        run = p.add_run()
        run.text = b["text"]
        run.font.size = Pt(font_size)
        run.font.bold = b.get("bold", False)
        run.font.color.rgb = b.get("color", BLACK)
    return tx_box


def add_table(slide, left, top, width, row_height_emu, headers, rows,
              col_widths=None):
    n_rows = len(rows) + 1
    n_cols = len(headers)
    shape = slide.shapes.add_table(
        n_rows, n_cols, left, top, width, Emu(row_height_emu * n_rows)
    )
    table = shape.table

    if col_widths:
        for i, w in enumerate(col_widths):
            table.columns[i].width = w

    for col, header in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = DARK_BLUE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = WHITE
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

    for ridx, row in enumerate(rows):
        bg = LIGHT_BLUE if ridx % 2 == 0 else WHITE
        for cidx, val in enumerate(row):
            cell = table.cell(ridx + 1, cidx)
            if isinstance(val, dict):
                cell.text = val["text"]
                bg_override = val.get("bg")
                if bg_override:
                    bg = bg_override
            else:
                cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(11)
            p.font.color.rgb = BLACK
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    return shape


def add_card(slide, left, top, width, height, title, body, color):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.15)
    tf.margin_right = Inches(0.15)
    p1 = tf.paragraphs[0]
    p1.text = title
    p1.font.bold = True
    p1.font.size = Pt(14)
    p1.font.color.rgb = WHITE
    p1.alignment = PP_ALIGN.LEFT
    p2 = tf.add_paragraph()
    p2.text = body
    p2.font.size = Pt(12)
    p2.font.color.rgb = WHITE
    p2.alignment = PP_ALIGN.LEFT


def add_note(slide, text: str):
    slide.notes_slide.notes_text_frame.text = text


def add_footer(slide, text):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, Inches(6.85), SLIDE_W, Inches(0.65)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = DARK_BLUE
    shape.line.fill.background()
    fp = shape.text_frame.paragraphs[0]
    fp.text = text
    fp.font.size = Pt(14)
    fp.font.color.rgb = WHITE
    fp.alignment = PP_ALIGN.CENTER


def main():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # ================================================================
    # Slide 1: Title
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "IDAES-GTEP Progress Update",
        "2035 PCM Operational Feasibility & GTEP Codebase Status | May 21, 2026",
    )
    add_bullet_box(
        slide, Inches(0.8), y + Inches(0.4), Inches(12.0), Inches(3.5),
        [
            {"text": "Part 1: Operational violation audit of the 2035 GTEP fleet in Prescient PCM",
             "bold": True},
            {"text": "    No-extreme (365 days) vs extreme (69 days, partial) comparison",
             "level": 1},
            {"text": "Part 2: GTEP codebase divergence between main and working branch",
             "bold": True},
            {"text": "    Bug fixes, structural differences, and version alignment question",
             "level": 1},
            {"text": "Part 3: Discussion — which GTEP version should we run, and can we benchmark together?",
             "bold": True},
        ],
        font_size=19,
    )
    add_footer(slide, "IDAES-GTEP | Bi-weekly progress update")
    add_note(slide,
        "Two-part update: (1) results from running the GTEP-derived 2035 fleet through "
        "365-day Prescient PCM — what violations emerge and why; (2) codebase status after "
        "17 rounds of debugging the commitment_period branch, and what I found when comparing "
        "back to upstream main."
    )

    # ================================================================
    # Slide 2: Violation Dashboard — No-Extreme (all PASS)
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "2035 Fleet — Hard Violations: All Clear (No-Extreme)",
        "365-day Prescient simulation, PTDF & btheta configs, 278 generators"
    )

    PASS_GREEN = RGBColor(0xD5, 0xF5, 0xE3)
    add_table(
        slide, Inches(0.5), y + Inches(0.2), Inches(12.3), 340000,
        ["Violation Check", "Annual Total", "Hours Affected", "Peak Value", "Status"],
        [
            ["Load shedding", "0 MWh", "0 / 8,760", "0 MW",
             {"text": "PASS", "bg": PASS_GREEN}],
            ["Over-generation", "0 MWh", "0 / 8,760", "0 MW",
             {"text": "PASS", "bg": PASS_GREEN}],
            ["Reserve shortfall", "0 MWh", "0 / 8,760", "0 MW",
             {"text": "PASS", "bg": PASS_GREEN}],
            ["Renewable curtailment", "0 GWh", "0 / 8,760", "0 MW",
             {"text": "PASS", "bg": PASS_GREEN}],
            ["Line flow violations", "0", "0 / 2.2M line-hrs", "0 MW",
             {"text": "PASS", "bg": PASS_GREEN}],
            ["PMin/PMax compliance", "0 violations", "262K online hrs", "—",
             {"text": "PASS", "bg": PASS_GREEN}],
            ["Ramp rate compliance", "0 violations", "1.3M ramp events", "—",
             {"text": "PASS", "bg": PASS_GREEN}],
            ["Min up/down time", "0 violations", "Interior runs only", "—",
             {"text": "PASS", "bg": PASS_GREEN}],
        ],
    )
    add_bullet_box(
        slide, Inches(0.6), y + Inches(4.1), Inches(12.0), Inches(1.5),
        [
            {"text": "All hard violation checks pass with zeros across both PTDF and btheta configurations.",
             "bold": True, "color": GREEN},
            {"text": "The GTEP-derived fleet is operationally feasible for the full year under no-extreme conditions."},
        ],
        font_size=15,
    )
    add_note(slide,
        "Source: operational_violations_2035_executed.ipynb, Cells 5/12/16-18/21/23. "
        "Both PTDF (sh=6, rh=36) and btheta (sh=24, rh=48) configurations give identical "
        "all-pass results. Supply-demand balance is perfect (0 MW imbalance)."
    )

    # ================================================================
    # Slide 3: But — stress signals exist
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "Stress Signals Under the Surface (No-Extreme)",
        "Hard violations are zero, but congestion and cycling stress are real"
    )
    add_card(
        slide, Inches(0.5), y + Inches(0.2), Inches(3.8), Inches(2.3),
        "Congestion",
        "18 lines above 90% rating\n21,381 near-congested line-hours\nCongestion in 99.9% of hours",
        AMBER,
    )
    add_card(
        slide, Inches(4.6), y + Inches(0.2), Inches(3.8), Inches(2.3),
        "Negative LMPs",
        "1,024 bus-hours at 100/123 buses\nRange: -$883 to +$1,000\n4 bus-hours above $500/MWh",
        RED,
    )
    add_card(
        slide, Inches(8.9), y + Inches(0.2), Inches(4.2), Inches(2.3),
        "CT Cycling",
        "7,400+ startups / year\n~55 starts/gen (nearly daily)\nTop cycler: 341 starts/yr",
        MEDIUM_BLUE,
    )
    add_bullet_box(
        slide, Inches(0.6), y + Inches(2.8), Inches(12.0), Inches(2.5),
        [
            {"text": "System price is remarkably stable: mean $11.62/MWh, std $3.04, no spikes — "
                     "confirms over-built fleet.", "space_after": 8},
            {"text": "Congestion is structural: negative LMPs signal renewable surplus trapped behind "
                     "transmission bottlenecks.", "space_after": 8},
            {"text": "CT cycling cost is invisible to GTEP: model uses 4 representative days + linear cost, "
                     "no startup penalty in the objective.", "space_after": 8},
            {"text": "These are not violations, but they indicate where the GTEP's simplified model "
                     "diverges from real operations.", "bold": True, "color": DARK_BLUE},
        ],
        font_size=15,
    )
    add_note(slide,
        "Source: Cells 13 (congestion), 14 (neg LMP), 19 (cycling), 27 (prices). "
        "The fleet has 2.05x dispatchable capacity vs peak demand. Over-build masks "
        "all hard constraints but cannot eliminate congestion or cycling."
    )

    # ================================================================
    # Slide 4: Extreme scenario — violations appear
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "Extreme Scenario: Real Violations Emerge (69 Days, Partial)",
        "Same fleet, more aggressive load/renewable profiles — the over-build buffer breaks"
    )

    FAIL_RED = RGBColor(0xFA, 0xDB, 0xDB)
    add_table(
        slide, Inches(0.5), y + Inches(0.15), Inches(12.3), 330000,
        ["Finding", "No-Extreme (365d)", "Extreme PTDF (69d)", "Extreme btheta (69d)"],
        [
            ["Reserve shortfall",
             {"text": "0 hours", "bg": PASS_GREEN},
             {"text": "2 RT hrs, 82 MW worst", "bg": FAIL_RED},
             {"text": "2 RT + 7 DA hrs, 527 MW worst", "bg": FAIL_RED}],
            ["Min reserve margin",
             {"text": "16.5 - 23.7%", "bg": PASS_GREEN},
             {"text": "9.7% (2 hrs < 10%)", "bg": FAIL_RED},
             {"text": "7.9% (2 hrs < 10%)", "bg": FAIL_RED}],
            ["Load shedding",
             {"text": "0 hours", "bg": PASS_GREEN},
             {"text": "0 hours", "bg": PASS_GREEN},
             {"text": "4 hours", "bg": FAIL_RED}],
            ["Over-generation",
             {"text": "0 hours", "bg": PASS_GREEN},
             {"text": "344 hrs, +2,192 MW peak", "bg": FAIL_RED},
             {"text": "351 hrs, +2,202 MW peak", "bg": FAIL_RED}],
            ["NUC cycling",
             {"text": "0 starts (always on)", "bg": PASS_GREEN},
             {"text": "14 starts in 69 days", "bg": FAIL_RED},
             {"text": "17 starts in 69 days", "bg": FAIL_RED}],
            ["COAL cycling rate",
             {"text": "0.3 starts/gen/day", "bg": PASS_GREEN},
             {"text": "6.0 starts/gen/day (20x)", "bg": FAIL_RED},
             {"text": "5.7 starts/gen/day (19x)", "bg": FAIL_RED}],
        ],
    )
    add_bullet_box(
        slide, Inches(0.6), y + Inches(3.6), Inches(12.0), Inches(1.8),
        [
            {"text": "The over-build buffer is finite. Under extreme conditions, NUC is forced to cycle "
                     "(should never happen), COAL cycling explodes, and reserves fail.",
             "bold": True, "color": RED},
            {"text": "Caveat: only 69 of 365 days completed (simulation stopped). Full-year extreme run needed."},
        ],
        font_size=15,
    )
    add_note(slide,
        "Source: Cells 9 (margin), 10 (shortfall), 19 (cycling), 23 (overgen), 32 (summary). "
        "Extreme scenario uses more aggressive load and renewable variability profiles. "
        "The simulation stopped at day 69 — possibly solver issues under stress. "
        "NUC cycling is a red flag: nuclear plants have 48hr min up time and should never cycle."
    )

    # ================================================================
    # Slide 5: Why no violations? Root cause
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "Root Cause: Why Zero Violations in No-Extreme?",
        "The GTEP over-builds because its simplified model can't \"see\" real operational costs"
    )
    add_table(
        slide, Inches(0.5), y + Inches(0.15), Inches(12.3), 340000,
        ["GTEP Simplification", "What Prescient Actually Does", "Consequence"],
        [
            ["4 representative days",
             "365-day chronological simulation",
             "GTEP plans for worst-case peak across 4 days → excess capacity"],
            ["Linear cost (gen × fuelCost)",
             "Piecewise heat rates, 4-segment HR",
             "No efficiency differentiation → over-installs same-type units"],
            ["No startup cost in objective",
             "Full start/stop with hot/warm/cold costs",
             "CTs are \"free\" to add → 135 CTs installed, 7,400 starts/yr"],
            ["Reserves disabled (commented out)",
             "10% spinning reserve enforced",
             "Reserve adequacy is accidental, not planned"],
            ["No ramp rate constraint",
             "Hourly ramp limits enforced",
             "Fleet happens to have headroom; not guaranteed"],
            ["Uniform fuel_cost3 per type",
             "Generator-specific HR curves",
             "All CTs cost $22.80/MWh; all COALs $18.94/MWh"],
        ],
    )
    add_bullet_box(
        slide, Inches(0.6), y + Inches(3.7), Inches(12.0), Inches(1.5),
        [
            {"text": "Result: 2.05x dispatchable capacity vs peak demand. "
                     "Fleet is so large that violations are impossible under normal conditions.",
             "bold": True, "color": DARK_BLUE},
            {"text": "This is not good planning — it's over-investment masking model gaps. "
                     "The extreme scenario proves the margin is finite."},
        ],
        font_size=15,
    )
    add_note(slide,
        "The GTEP fleet has 81,664 MW dispatchable capacity vs 39,819 MW peak demand. "
        "Fleet economics show $714M thermal profit with CTs at $0.17/MWh median — "
        "marginal peakers that exist because GTEP didn't see their cycling cost."
    )

    # ================================================================
    # Slide 6: GTEP Codebase — main vs commitment_period
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "GTEP Codebase: main vs Working Branch",
        "17 rounds of debugging revealed both upstream bugs and structural divergence"
    )
    add_table(
        slide, Inches(0.3), y + Inches(0.15), Inches(12.7), 310000,
        ["Issue", "Severity", "main", "commitment_period", "Can Upstream?"],
        [
            ["Stage-specific costs (fixedCost1/2/3)", "High",
             "Declarations deleted, usage kept → crash", "Restored from gen data", "Yes"],
            ["GEN UID type mismatch (int vs str)", "High",
             "No astype(str) → never matches", "Fixed with astype + iloc guard", "Yes"],
            ["non_fuel_startup_cost missing", "High",
             "KeyError on some generators", "setdefault(0) fallback", "Yes"],
            ["Block-level reference (load_scaling)", "Medium",
             "Wrong block → crash w/ Texas data", "Fixed to investmentStage block", "Yes"],
            ["time_keys Prescient 2.2.2 compat", "Medium",
             "No fallback for numeric keys", "Date string fallback added", "Yes"],
            ["Storage guard (no storage.csv)", "Medium",
             "AttributeError", "hasattr() guard added", "Yes"],
            ["Code architecture", "—",
             "Modular (model_library/)", "Monolithic (3,600-line file)", "N/A"],
        ],
    )
    add_bullet_box(
        slide, Inches(0.6), y + Inches(3.7), Inches(12.0), Inches(1.5),
        [
            {"text": "6 bugs found in upstream main that crash the Texas case study pipeline. "
                     "3 are high severity (model won't build).",
             "bold": True, "color": RED},
            {"text": "main has been refactored into model_library/ modules, "
                     "but some refactoring dropped working code (e.g., cost param declarations)."},
        ],
        font_size=14,
    )
    add_note(slide,
        "Source: session_logs/2026-05-21_main_vs_commitment_period_diff.md. "
        "The commitment_period branch has been through 17 debug rounds and can build + BigM "
        "transform successfully. main crashes at multiple points when running the Texas case. "
        "Upstream also has a logic bug: 'if \"Texas\" or \"Coal\" not in data_path' is always True."
    )

    # ================================================================
    # Slide 7: What main does better
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "What I Can Learn from main (and Vice Versa)",
        "Neither branch is complete — each has improvements the other needs"
    )

    add_bullet_box(
        slide, Inches(0.5), y + Inches(0.15), Inches(5.8), Inches(4.5),
        [
            {"text": "main does better:", "bold": True, "color": DARK_BLUE, "space_after": 10},
            {"text": "renewableCapacityNameplate: takes max across all representative periods "
                     "(commitment_period only looks at period 1)", "space_after": 8},
            {"text": "load_prescient: fully parameterized (start_date, sced_freq, num_steps, "
                     "representative_dates all configurable)", "space_after": 8},
            {"text": "Defensive checks in load_default_data_settings "
                     "(guards against missing 'elements' or 'fuel' keys)", "space_after": 8},
            {"text": "Modular code organization (model_library/) — easier to maintain long-term",
             "space_after": 8},
        ],
        font_size=14,
    )
    add_bullet_box(
        slide, Inches(6.6), y + Inches(0.15), Inches(6.3), Inches(4.5),
        [
            {"text": "commitment_period does better:", "bold": True, "color": DARK_BLUE,
             "space_after": 10},
            {"text": "Actually runs the Texas case study end-to-end "
                     "(load → model → BigM → ready to solve)", "space_after": 8},
            {"text": "6 bug fixes that main still needs (cost params, GEN UID, startup cost, "
                     "block refs, time_keys, storage guard)", "space_after": 8},
            {"text": "rampUpRates units = dimensionless (correct); "
                     "main uses MW/min (misleading for percentage data)", "space_after": 8},
            {"text": "mutable=True on period lengths — enables 2hr/4hr commitment sensitivity",
             "space_after": 8},
        ],
        font_size=14,
    )
    add_bullet_box(
        slide, Inches(0.6), y + Inches(4.0), Inches(12.0), Inches(1.2),
        [
            {"text": "Ideal path: merge commitment_period bug fixes into main's modular structure, "
                     "then adopt main's parameterization improvements.",
             "bold": True, "color": DARK_BLUE},
        ],
        font_size=15,
    )
    add_note(slide,
        "The renewableCapacityNameplate issue affects model correctness — commitment_period "
        "may underestimate renewable nameplate capacity if representative periods have different "
        "peak outputs. This should be a priority fix."
    )

    # ================================================================
    # Slide 8: Pipeline status
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "Current Pipeline Status",
        "commitment_period branch: model builds, BigM transforms — blocked on solver environment"
    )

    stages = [
        ("load_prescient", GREEN, "PASS"),
        ("texas_case_study", GREEN, "PASS"),
        ("model_data_refs", GREEN, "PASS"),
        ("investment_stages", GREEN, "PASS"),
        ("commitment_periods", GREEN, "PASS"),
        ("dispatch", GREEN, "PASS"),
        ("create_model", GREEN, "PASS"),
        ("BigM transform", GREEN, "PASS"),
        ("solve (Gurobi)", RED, "BLOCKED"),
    ]
    box_w = Inches(1.3)
    box_h = Inches(0.7)
    gap = Inches(0.08)
    x_start = Inches(0.35)
    y_start = y + Inches(0.3)

    for i, (label, color, status) in enumerate(stages):
        x = x_start + i * (box_w + gap)
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, x, y_start, box_w, box_h
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.fill.background()
        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.text = label
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER
        p2 = tf.add_paragraph()
        p2.text = status
        p2.font.size = Pt(9)
        p2.font.color.rgb = WHITE
        p2.alignment = PP_ALIGN.CENTER

    add_bullet_box(
        slide, Inches(0.6), y + Inches(1.4), Inches(12.0), Inches(3.8),
        [
            {"text": "Blocker: GurobiDirect on CRC cannot find solver binary. "
                     "This is an environment config issue, not a code bug.", "space_after": 10},
            {"text": "Next step: try HiGHS (open-source) to verify model feasibility, "
                     "then resolve Gurobi path on CRC for production runs.", "space_after": 15},
            {"text": "PCM analysis pipeline (separate from GTEP solve):", "bold": True,
             "space_after": 8},
            {"text": "    2035 no-extreme: 365 days complete, both configs (PTDF + btheta)",
             "level": 1, "color": GREEN, "space_after": 6},
            {"text": "    2035 extreme: 69 days partial (stopped), both configs",
             "level": 1, "color": AMBER, "space_after": 6},
            {"text": "    Analysis notebooks: operational violations + generator profitability complete",
             "level": 1, "color": GREEN, "space_after": 6},
            {"text": "    CEM-vs-PCM validation: 2x2 factorial complete, gap quantified",
             "level": 1, "color": GREEN},
        ],
        font_size=15,
    )
    add_note(slide,
        "The solve step is blocked by CRC Gurobi environment, not code. "
        "All preceding steps (17 debug rounds) now pass. "
        "PCM analysis uses pre-computed Prescient results and runs locally."
    )

    # ================================================================
    # Slide 9: Discussion — version alignment
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(
        slide,
        "Discussion: Version Alignment",
        "Which GTEP should we run? Can we establish a shared benchmark?"
    )
    add_bullet_box(
        slide, Inches(0.6), y + Inches(0.2), Inches(12.0), Inches(5.0),
        [
            {"text": "The problem:", "bold": True, "color": RED, "space_after": 10},
            {"text": "GTEP main has been refactored significantly since the version I received. "
                     "Main has new modular structure but introduced regressions "
                     "(6 bugs that crash the Texas pipeline). My working branch has fixes but "
                     "is monolithic.",
             "space_after": 15},

            {"text": "What I'd like to propose:", "bold": True, "color": DARK_BLUE,
             "space_after": 10},
            {"text": "1. Share the 6 bug fixes as a patch set (or PR) so main can run the Texas case again.",
             "space_after": 8},
            {"text": "2. Define a reproducibility benchmark: same input data, same GTEP config "
                     "→ both of us get the same objective value and investment decisions.",
             "space_after": 8},
            {"text": "3. Once we confirm the benchmark matches, I'll rebase my commitment-period "
                     "work onto the fixed main.",
             "space_after": 15},

            {"text": "Why this matters:", "bold": True, "color": DARK_BLUE, "space_after": 10},
            {"text": "Without version alignment, my PCM analysis may be validating a fleet "
                     "that the latest GTEP wouldn't produce. The 2035 results are only as good "
                     "as the GTEP solution they came from."},
        ],
        font_size=15,
    )
    add_note(slide,
        "This is the key discussion point. The goal is collaborative, not accusatory. "
        "I want to contribute fixes back and establish trust in the shared pipeline. "
        "The benchmark doesn't need to be expensive — just one run with agreed inputs "
        "and a comparison of objective + investment decisions."
    )

    # ================================================================
    # Slide 10: Summary & Next Steps
    # ================================================================
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    y = add_title_bar(slide, "Summary & Next Steps")

    add_bullet_box(
        slide, Inches(0.5), y + Inches(0.15), Inches(6.0), Inches(5.0),
        [
            {"text": "Key takeaways:", "bold": True, "color": DARK_BLUE, "space_after": 10},
            {"text": "The 2035 GTEP fleet passes all hard PCM checks under normal conditions, "
                     "but this is due to over-building, not good planning.",
             "space_after": 8},
            {"text": "Under extreme conditions, real violations appear: reserve shortfall, "
                     "NUC forced cycling, over-generation.",
             "space_after": 8},
            {"text": "The GTEP codebase has diverged — main has regressions, "
                     "working branch has fixes but needs main's improvements.",
             "space_after": 8},
            {"text": "We need version alignment before the next round of GTEP runs.",
             "bold": True, "space_after": 8},
        ],
        font_size=15,
    )
    add_bullet_box(
        slide, Inches(6.8), y + Inches(0.15), Inches(6.0), Inches(5.0),
        [
            {"text": "Proposed next steps:", "bold": True, "color": DARK_BLUE, "space_after": 10},
            {"text": "1. Share bug fix patch with collaborator",
             "space_after": 8},
            {"text": "2. Run reproducibility benchmark together",
             "space_after": 8},
            {"text": "3. Complete extreme scenario full-year PCM run",
             "space_after": 8},
            {"text": "4. Add GTEP reserve constraints + startup cost",
             "space_after": 8},
            {"text": "5. Resolve CRC Gurobi environment for commitment-period solve",
             "space_after": 8},
        ],
        font_size=15,
    )
    add_footer(slide, "IDAES-GTEP | Next update: TBD")
    add_note(slide,
        "The next steps are ordered by priority. Steps 1-2 are prerequisites for "
        "meaningful further GTEP development. Steps 3-5 can proceed in parallel once "
        "version alignment is confirmed."
    )

    # ================================================================
    # Save
    # ================================================================
    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    print(f"Saved: {OUT_PPTX}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    main()
