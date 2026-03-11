"""Generate GTEP PCM Analysis Update presentation from outline."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# --- Colors ---
DARK_BLUE = RGBColor(0x1B, 0x3A, 0x5C)
MEDIUM_BLUE = RGBColor(0x2C, 0x5F, 0x8A)
LIGHT_BLUE = RGBColor(0xD6, 0xE8, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x33, 0x33, 0x33)
GRAY = RGBColor(0x66, 0x66, 0x66)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x27, 0xAE, 0x60)
AMBER = RGBColor(0xF3, 0x9C, 0x12)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def add_background(slide, color=WHITE):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_title_bar(slide, title_text, subtitle_text=None):
    """Dark blue top bar with title."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(1.2)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = DARK_BLUE
    shape.line.fill.background()

    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(32)
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
        tf2.word_wrap = True
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


def add_bullet_box(slide, left, top, width, height, bullets, font_size=18, bold_first_word=False):
    """Add a text box with bullet points."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.space_after = Pt(6)
        p.space_before = Pt(2)
        p.level = bullet.get("level", 0)

        text = bullet["text"]
        if bold_first_word and ":" in text:
            bold_part, rest = text.split(":", 1)
            run = p.add_run()
            run.text = bold_part + ":"
            run.font.size = Pt(font_size)
            run.font.color.rgb = BLACK
            run.font.bold = True
            run2 = p.add_run()
            run2.text = rest
            run2.font.size = Pt(font_size)
            run2.font.color.rgb = BLACK
        else:
            run = p.add_run()
            run.text = text
            run.font.size = Pt(font_size)
            run.font.color.rgb = bullet.get("color", BLACK)
            run.font.bold = bullet.get("bold", False)
    return txBox


def add_table(slide, left, top, width, row_height, headers, rows):
    """Add a formatted table."""
    num_rows = len(rows) + 1
    num_cols = len(headers)
    table_shape = slide.shapes.add_table(num_rows, num_cols, left, top, width, Emu(row_height * num_rows))
    table = table_shape.table

    # Style header
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = DARK_BLUE
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(14)
        p.font.color.rgb = WHITE
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

    # Style rows
    for i, row in enumerate(rows):
        bg = LIGHT_BLUE if i % 2 == 0 else WHITE
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(13)
            p.font.color.rgb = BLACK
            p.alignment = PP_ALIGN.CENTER
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE

    return table_shape


def add_speaker_notes(slide, text):
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text


def add_section_divider(title, subtitle):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    add_background(slide, DARK_BLUE)
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(1.5))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.color.rgb = WHITE
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    p2.text = subtitle
    p2.font.size = Pt(22)
    p2.font.color.rgb = RGBColor(0xAA, 0xCC, 0xEE)
    p2.alignment = PP_ALIGN.CENTER
    return slide


def add_figure_placeholder(slide, left, top, width, height, label):
    """Add a dashed-border placeholder for a notebook figure."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0xF5, 0xF5, 0xF5)
    shape.line.color.rgb = MEDIUM_BLUE
    shape.line.dash_style = 2  # dash
    shape.line.width = Pt(1.5)
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label
    run.font.size = Pt(14)
    run.font.color.rgb = MEDIUM_BLUE
    run.font.italic = True


# ============================================================
# TITLE SLIDE
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide, WHITE)

# Top bar
shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.15))
shape.fill.solid()
shape.fill.fore_color.rgb = DARK_BLUE
shape.line.fill.background()

txBox = slide.shapes.add_textbox(Inches(1.5), Inches(2.0), Inches(10), Inches(2.5))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = "GTEP Production Cost Model Analysis"
p.font.size = Pt(40)
p.font.color.rgb = DARK_BLUE
p.font.bold = True
p.alignment = PP_ALIGN.CENTER

p2 = tf.add_paragraph()
p2.text = "Benchmarking Prescient UC+ED Against Lu et al. 2025"
p2.font.size = Pt(22)
p2.font.color.rgb = MEDIUM_BLUE
p2.alignment = PP_ALIGN.CENTER
p2.space_before = Pt(12)

p3 = tf.add_paragraph()
p3.text = "TX-123BT ERCOT System  |  B-theta DC Power Flow  |  365-Day Simulation"
p3.font.size = Pt(16)
p3.font.color.rgb = GRAY
p3.alignment = PP_ALIGN.CENTER
p3.space_before = Pt(24)

# Bottom bar
shape2 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.8), SLIDE_W, Inches(0.7))
shape2.fill.solid()
shape2.fill.fore_color.rgb = DARK_BLUE
shape2.line.fill.background()
tf2 = shape2.text_frame
tf2.vertical_anchor = MSO_ANCHOR.MIDDLE
p4 = tf2.paragraphs[0]
p4.text = "Research Update  |  February 2026"
p4.font.size = Pt(16)
p4.font.color.rgb = WHITE
p4.alignment = PP_ALIGN.CENTER
tf2.margin_left = Inches(0.5)


# ============================================================
# ACT 1 DIVIDER
# ============================================================
add_section_divider("Act 1: ERCOT Data & Processing", "TX-123BT test case, data pipeline, assumptions")

# ============================================================
# SLIDE 1 — TX-123BT Test Case Overview
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "TX-123BT Test Case Overview", "ERCOT 123-Bus Backbone Transmission Network")

add_bullet_box(slide, Inches(0.5), y_start + Inches(0.2), Inches(6), Inches(4.5), [
    {"text": "123-bus ERCOT backbone network (public dataset)", "bold": True},
    {"text": "292 generators across 6 fuel types:", "level": 0},
    {"text": "Nuclear, Natural Gas (CT), Coal, Wind, Solar, Hydro", "level": 1},
    {"text": "188 transmission lines with impedance and ratings", "level": 0},
    {"text": "5-year hourly profiles: load, wind, solar", "level": 0},
    {"text": "8 weather zones: COAST, EAST, FWEST, NCENT, NORTH, SCENT, SOUTH, WEST", "level": 0},
], font_size=17)

add_figure_placeholder(slide, Inches(7), y_start + Inches(0.2), Inches(5.8), Inches(4.5),
                        "[Insert: Network topology map\nor bus/zone diagram from paper]")

add_speaker_notes(slide,
    "This is the TX-123BT test case - a 123-bus backbone model of the ERCOT system used in Lu et al. 2025. "
    "It has 292 generators across 6 fuel types and 188 transmission lines. "
    "The public dataset provides 5 years of hourly load, wind, and solar profiles.")

# ============================================================
# SLIDE 2 — Data Processing Pipeline
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "Data Processing Pipeline", "Raw ERCOT data -> Prescient-ready format")

# Left: pipeline description
add_bullet_box(slide, Inches(0.5), y_start + Inches(0.2), Inches(5.5), Inches(2.0), [
    {"text": "Raw data: Data_public_5year/"},
    {"text": "Bus_data.csv, Line_data.csv, Generator_data.xlsx", "level": 1},
    {"text": "Daily load/wind/solar .txt files (5 years)", "level": 1},
    {"text": "Processing: demo_processing_XC.ipynb"},
    {"text": "Output: gen.csv, bus.csv, branch.csv, timeseries CSVs"},
], font_size=16)

# Right: assumptions table
add_table(slide, Inches(6.5), y_start + Inches(0.2), Inches(6.3), Emu(350000),
    ["Parameter", "Value"],
    [
        ["Gas fuel price", "$2.29/MMBTU"],
        ["Coal fuel price", "$1.78/MMBTU"],
        ["Nuclear fuel price", "$0.81/MMBTU"],
        ["Gas min up/down", "2h / 1h"],
        ["Coal min up/down", "12h / 12h"],
        ["Nuclear min up/down", "48h / 48h"],
        ["Cost curve segments", "4 (30-50-70-100% PMax)"],
    ])

add_speaker_notes(slide,
    "I convert the raw ERCOT data into Prescient's input format using a processing notebook. "
    "The key assumptions are fuel prices, generator flexibility parameters, and piecewise-linear "
    "cost curves with 4 segments. I use 2019 data to benchmark against the paper's work.")

# ============================================================
# SLIDE 3 — GTEP to Prescient Handoff
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "GTEP to Prescient Handoff", "Investment decisions -> Production cost simulation")

# Flow diagram as shapes
box_left = Inches(0.8)
box_top = y_start + Inches(0.8)
box_w = Inches(2.5)
box_h = Inches(1.2)
gap = Inches(0.6)

labels = [
    ("GTEP Pyomo Model\n\nInvestment/retirement\ndecisions for 2035", DARK_BLUE),
    ("output_to_prescient\n\nFilter to invested\ngenerator fleet", MEDIUM_BLUE),
    ("Prescient UC+ED\n\n365-day btheta\nsimulation on CRC", DARK_BLUE),
    ("LMP Analysis\n\nLoad-weighted LMP,\nbenchmarking", MEDIUM_BLUE),
]

for i, (label, color) in enumerate(labels):
    x = box_left + i * (box_w + gap)
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, box_top, box_w, box_h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = label
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    # Arrow between boxes
    if i < 3:
        arrow_x = x + box_w + Inches(0.05)
        arrow_y = box_top + box_h / 2 - Inches(0.1)
        arr = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, arrow_x, arrow_y, Inches(0.5), Inches(0.2))
        arr.fill.solid()
        arr.fill.fore_color.rgb = GRAY
        arr.line.fill.background()

# Config details below
add_bullet_box(slide, Inches(0.5), box_top + box_h + Inches(0.5), Inches(12), Inches(3.0), [
    {"text": "Coal retirement scenario: 282 generators (10 coal retired, no hydro)"},
    {"text": "Prescient config:", "bold": True},
    {"text": "B-theta DC power flow for RUC and SCED", "level": 1},
    {"text": "48h RUC horizon, 24h SCED horizon", "level": 1},
    {"text": "Perfect foresight (no forecast error)", "level": 1},
], font_size=16)

add_speaker_notes(slide,
    "The GTEP model decides which generators to build, extend, or retire. "
    "I filter the fleet to the invested generators and pass it to Prescient, "
    "which runs a full 365-day unit commitment and economic dispatch simulation on CRC. "
    "This run uses B-theta DC power flow with perfect foresight.")


# ============================================================
# ACT 2 DIVIDER
# ============================================================
add_section_divider("Act 2: PCM Results", "Generally positive LMP ($24.73/MWh annual)")

# ============================================================
# SLIDE 4 — Annual LMP Summary
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "Annual LMP Summary", "Load-weighted system LMP: $24.73/MWh")

add_bullet_box(slide, Inches(0.5), y_start + Inches(0.2), Inches(5.5), Inches(4.5), [
    {"text": "Load-weighted system LMP: $24.73/MWh", "bold": True},
    {"text": "Total demand: 383.8 TWh"},
    {"text": "Generation cost: $1.52B"},
    {"text": ""},
    {"text": "Negative LMP: 10% of bus-hours", "color": RED, "bold": True},
    {"text": "Concentrated in wind-heavy zones (NORTH, FWEST)", "level": 1},
    {"text": "Physical: renewable oversupply behind transmission constraints", "level": 1},
    {"text": "However, in the paper there is no negative LMP", "level": 1, "color": RED},
], font_size=16)

add_figure_placeholder(slide, Inches(6.5), y_start + Inches(0.2), Inches(6.3), Inches(4.5),
                        "[Insert: Full-year LMP time series\nNotebook Cell 21, Sec 9.1]")

add_speaker_notes(slide,
    "The annual load-weighted LMP is about $25/MWh - generally positive. "
    "About 10% of bus-hours show negative prices, concentrated in wind-heavy zones. "
    "This is physically consistent behavior. However, the paper shows no negative LMP at all, "
    "which is a notable difference.")

# ============================================================
# SLIDE 5 — Quarterly Breakdown
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "Quarterly LMP Breakdown", "Q3 summer drives the annual average")

add_table(slide, Inches(0.5), y_start + Inches(0.3), Inches(5.5), Emu(400000),
    ["Quarter", "Load-Wt LMP", "Character"],
    [
        ["Q1 (Jan-Mar)", "$1.3/MWh", "Low demand, moderate wind"],
        ["Q2 (Apr-Jun)", "$3.0/MWh", "Spring shoulder, high renewables"],
        ["Q3 (Jul-Sep)", "$57.0/MWh", "Summer peak (drives annual avg)"],
        ["Q4 (Oct-Dec)", "$8.8/MWh", "Fall transition"],
    ])

add_bullet_box(slide, Inches(0.5), y_start + Inches(2.8), Inches(5.5), Inches(2.0), [
    {"text": "Q3 dominates annual average: peak cooling demand meets tight supply"},
    {"text": "Q1/Q2 near-zero: renewable oversupply in shoulder seasons"},
], font_size=16)

add_figure_placeholder(slide, Inches(6.5), y_start + Inches(0.2), Inches(6.3), Inches(4.8),
                        "[Insert: Quarterly LMP profiles (Fig 10a-d)\nNotebook Cell 55, Sec 10.7]")

add_speaker_notes(slide,
    "Breaking it down by quarter: Q3 summer is by far the highest at $57/MWh - peak cooling demand. "
    "Q1 and Q2 shoulder seasons are near-zero because wind and solar output is high relative to demand. "
    "Q4 falls in between.")

# ============================================================
# SLIDE 6 — Spatial LMP Pattern
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "Spatial LMP Pattern", "Wind-heavy west/north vs load-center east/south")

add_table(slide, Inches(0.3), y_start + Inches(0.3), Inches(5.8), Emu(370000),
    ["Zone", "Mean DA LMP", "% Negative Hrs"],
    [
        ["NORTH", "-$241.7", "41.8%"],
        ["FWEST", "-$135.7", "32.6%"],
        ["WEST", "-$41.5", "28.0%"],
        ["EAST", "+$11.2", "1.6%"],
        ["COAST", "+$11.8", "0.3%"],
        ["SCENT", "+$11.9", "4.9%"],
        ["SOUTH", "+$13.7", "2.4%"],
        ["NCENT", "+$60.0", "5.0%"],
    ])

add_bullet_box(slide, Inches(0.3), y_start + Inches(4.0), Inches(5.8), Inches(1.2), [
    {"text": "Transmission congestion creates price separation"},
    {"text": "Congestion-driven: consistent with physical system"},
], font_size=15)

add_figure_placeholder(slide, Inches(6.5), y_start + Inches(0.2), Inches(6.3), Inches(4.8),
                        "[Insert: Nodal LMP scatter, Q2 normal day, Hour 15\nNotebook Cell 59, Sec 10.9]")

add_speaker_notes(slide,
    "Clear spatial pattern. NORTH and FWEST zones have deeply negative LMPs - wind output can't fully export "
    "through constrained transmission lines. Load centers like COAST, EAST, and NCENT see positive prices. "
    "This congestion-driven price separation is expected.")

# ============================================================
# SLIDE 7 — Benchmarking vs Paper
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "Benchmarking vs Lu et al. 2025", "Same network, different fleet and LMP range")

add_bullet_box(slide, Inches(0.5), y_start + Inches(0.2), Inches(12), Inches(1.0), [
    {"text": "Paper: 2019 SCUC on TX-123BT, all-positive LMPs ($10-220/MWh)"},
    {"text": "Our run: 2019 data with coal retirement, LMP range -$1000 to +$1395/MWh"},
], font_size=17)

add_table(slide, Inches(1.5), y_start + Inches(1.5), Inches(10), Emu(400000),
    ["Aspect", "Aligned?", "Details"],
    [
        ["Network topology", "Yes", "Same 123-bus, 188-line backbone"],
        ["Wind/solar profiles", "Yes", "Same temporal patterns"],
        ["Congestion count", "Yes", "~6-7 avg congested lines"],
        ["LMP levels", "No", "Ours much wider range"],
        ["Generator fleet", "Partial", "282 vs 292 units (no hydro)"],
    ])

add_bullet_box(slide, Inches(0.5), y_start + Inches(4.2), Inches(12), Inches(1.2), [
    {"text": "Key question: Are LMP differences all scenario-driven, or are some model artifacts?",
     "bold": True, "color": DARK_BLUE},
], font_size=18)

add_speaker_notes(slide,
    "Comparing against the paper's 2019 results: topology, renewable profiles, and congestion patterns "
    "align well. LMP levels are different. The question is whether the specific differences are all "
    "scenario-driven, or if some are model artifacts.")


# ============================================================
# ACT 3 DIVIDER
# ============================================================
add_section_divider("Act 3: The Q2/Q4 Question", "Hourly price spikes exceeding paper benchmarks")

# ============================================================
# SLIDE 8 — Q2/Q4 Price Spikes
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "Q2 and Q4: Hourly Price Spikes", "Quarterly averages OK, but hourly spikes far exceed paper ranges")

add_bullet_box(slide, Inches(0.5), y_start + Inches(0.2), Inches(5.5), Inches(2.5), [
    {"text": "Quarterly averages are positive and reasonable"},
    {"text": "But hourly spikes far exceed paper benchmarks:", "bold": True},
    {"text": "Q2: spikes to +$347/MWh vs paper's $16-55 range", "level": 1, "color": RED},
    {"text": "Q4: spikes to +$320/MWh vs paper's $17-40 range", "level": 1, "color": RED},
    {"text": "Paper Table VI trough/normal/peak ranges — our spikes blow through peak ceiling"},
    {"text": "Most hours within range, but spikes are extreme"},
], font_size=16)

add_figure_placeholder(slide, Inches(6.5), y_start + Inches(0.2), Inches(6.3), Inches(2.2),
                        "[Insert: Quarterly plots with paper benchmark bands\nNotebook Cell 55, Sec 10.7]")

add_figure_placeholder(slide, Inches(6.5), y_start + Inches(2.6), Inches(6.3), Inches(2.2),
                        "[Insert: Q2 normal-day hourly LMP vs paper\nNotebook Cell 66, Sec 10.12 (Fig 14)]")

add_speaker_notes(slide,
    "Here's the key question. Quarterly averages look fine - generally positive, seasonally reasonable. "
    "But at hourly resolution, Q2 and Q4 show price spikes well above the paper. "
    "The paper's Q2 peak is around $55/MWh; we're hitting $347. "
    "These show up in the system-level weighted average. "
    "I want to understand whether this is purely from our scenario or something in the model formulation.")

# ============================================================
# SLIDE 9 — Next Steps
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide)
y_start = add_title_bar(slide, "Next Steps", "Investigate Pyomo model formulation")

add_bullet_box(slide, Inches(1), y_start + Inches(0.5), Inches(11), Inches(4.5), [
    {"text": "1. Investigate Pyomo model formulation for Q2/Q4 spikes", "bold": True},
    {"text": "Examine cost expression and generator constraints", "level": 1},
    {"text": "Check commitment decisions during spike hours", "level": 1},
    {"text": "Compare against paper's original SCUC model", "level": 1},
    {"text": ""},
    {"text": "2. Spring negative prices (Mar/Apr/May)", "bold": True},
    {"text": "Still present in the whole-year run", "level": 1},
    {"text": "Will investigate after Pyomo model review", "level": 1},
    {"text": ""},
    {"text": "Goal: Determine if spikes are scenario-driven (correct) or model-driven (fixable)",
     "bold": True, "color": DARK_BLUE},
], font_size=18, bold_first_word=False)

add_speaker_notes(slide,
    "Next step is to go through the paper's original Pyomo SCUC model and compare against our "
    "Prescient configuration. I want to understand what's driving these hourly spikes. "
    "I also still have negative prices in spring months, but will address that after the Pyomo review. "
    "The goal is a clear attribution: scenario effect vs model artifact.")


# ============================================================
# SAVE
# ============================================================
out_path = "/Users/yilu/Documents/GitHub/idaes-gtep/quality_reports/plans/2026-02-26_GTEP_PCM_Update.pptx"
prs.save(out_path)
print(f"Saved: {out_path}")
print(f"Total slides: {len(prs.slides)}")
