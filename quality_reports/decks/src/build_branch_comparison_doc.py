"""Generate the main-vs-commitment_period branch comparison docx.

Formatting convention:
  - Underline = adjustments needed on commitment_period (Yi Lu's branch)
  - Italic    = items that should be upstreamed to main
"""

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import os


def add_mixed(doc, fragments, style=None):
    """Add a paragraph with mixed formatting.

    Each fragment is (text, {fmt_flags}) where fmt_flags can include:
      'b' = bold, 'i' = italic, 'u' = underline, 'code' = monospace
    A plain string is treated as (text, {}).
    """
    p = doc.add_paragraph(style=style)
    for frag in fragments:
        if isinstance(frag, str):
            text, fmt = frag, set()
        else:
            text, fmt = frag
        r = p.add_run(text)
        if "b" in fmt:
            r.bold = True
        if "i" in fmt:
            r.italic = True
        if "u" in fmt:
            r.underline = True
        if "code" in fmt:
            r.font.name = "Consolas"
            r.font.size = Pt(9)
    return p


doc = Document()

style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)

# ── Legend ──
legend_p = doc.add_paragraph()
legend_p.add_run("Formatting convention: ").bold = True
r1 = legend_p.add_run("underlined text")
r1.underline = True
legend_p.add_run(" = adjustment needed on commitment_period (Yi Lu); ")
r2 = legend_p.add_run("italic text")
r2.italic = True
legend_p.add_run(" = should be upstreamed to main.")

# ── Title ──
title = doc.add_heading("GTEP Codebase: Branch Comparison and Bug Audit", level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta_run = meta.add_run(
    "Branches: main (upstream IDAES/idaes-gtep) vs commitment_period\n"
    "Scope: gtep_model.py, gtep_data.py, driver files\n"
    "Date: 2026-05-21\n"
    "Author: Yi Lu"
)
meta_run.font.size = Pt(10)
meta_run.font.color.rgb = RGBColor(100, 100, 100)

# ── 1. Overview ──
doc.add_heading("1. Overview", level=1)
doc.add_paragraph(
    "This document compares the main branch and the commitment_period branch "
    "of the idaes-gtep repository. The commitment_period branch extends the GTEP model "
    "to support variable-length commitment periods (1hr / 2hr / 4hr) for sensitivity "
    "analysis. During development and testing on the Notre Dame CRC cluster, 17 bugs "
    "were identified and fixed across the model construction pipeline."
)
add_mixed(doc, [
    "The purpose of this comparison is to: (1) identify bugs fixed on commitment_period "
    "that also exist on main and ",
    ("should be upstreamed", {"i"}),
    ", (2) identify improvements on main that ",
    ("commitment_period should adopt", {"u"}),
    ", and (3) document data-processing differences "
    "between the two branches to facilitate future merges.",
])

# ── 2. Architecture ──
doc.add_heading("2. Architectural Differences", level=1)

tbl = doc.add_table(rows=4, cols=3, style="Light Shading Accent 1")
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
headers = ["Dimension", "main", "commitment_period"]
for i, h in enumerate(headers):
    tbl.rows[0].cells[i].text = h
    for p in tbl.rows[0].cells[i].paragraphs:
        for r in p.runs:
            r.bold = True

rows_data = [
    [
        "Model code organization",
        "Modularized into gtep/model_library/ "
        "(investment.py, dispatch.py, commitment.py, objective.py, etc.)",
        "Single file: gtep_model.py (~3600 lines)",
    ],
    [
        "Temporal parameter ownership",
        "ExpansionPlanningData.__init__ receives stages, num_reps, etc.",
        "Moved to ExpansionPlanningModel.__init__",
    ],
    [
        "Commitment period support",
        "Fixed 1hr commitment periods only",
        "Configurable: 1hr / 2hr / 4hr via driver-level patching",
    ],
]
for i, row in enumerate(rows_data):
    for j, val in enumerate(row):
        tbl.rows[i + 1].cells[j].text = val

# ── 3. Data Processing ──
doc.add_heading("3. Data Processing Differences", level=1)

doc.add_heading("3.1 load_prescient — Parameterization vs Hardcoding", level=2)
add_mixed(doc, [
    "The main branch parameterizes key data-loading options (representative_dates, "
    "representative_weights, options_dict, Path object support), making the data loader "
    "reusable across different case studies. The commitment_period branch hardcodes these "
    "values for the Texas/123-Bus-Coal case study, which is sufficient for the current "
    "experiments but limits reusability. ",
    ("commitment_period should eventually adopt main's parameterized interface.", {"u"}),
])

doc.add_heading("3.2 import_load_scaling — Zone Naming Convention", level=2)
doc.add_paragraph(
    'The main branch uses numeric zone IDs ("1" through "8") as DataFrame column names. '
    "The commitment_period branch uses geographic zone names "
    '("COAST", "EAST", "FWEST", "NCENT", "NORTH", "SCENT", "SOUTH", "WEST"). '
    "This is a data-format dependency rather than a bug — each branch matches its own "
    "input data convention. The commitment_period convention was restored from earlier "
    "commented-out code in the original import_load_scaling implementation."
)

doc.add_heading("3.3 texas_case_study_updates — Type Safety", level=2)
add_mixed(doc, [
    "The commitment_period branch fixes two data-processing bugs in "
    "texas_case_study_updates() that ",
    ("should be upstreamed to main", {"i"}),
    ":",
])
bullets = [
    ("GEN UID type mismatch: pandas may read the GEN UID column as integers, "
     "but the generator dictionary keys are strings. Without explicit astype(str) "
     "conversion, DataFrame lookups silently return empty results, causing "
     "TypeError when float() is applied to an empty Series.", {"i"}),
    ("Empty match protection: The original code calls float() directly on a "
     "filtered DataFrame column. If no rows match (e.g., due to the type mismatch "
     "above), this raises TypeError. The fix uses .iloc[0] with an emptiness check.", {"i"}),
]
for text, fmt in bullets:
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    if "i" in fmt:
        r.italic = True

doc.add_heading("3.4 renewableCapacityNameplate Calculation", level=2)
add_mixed(doc, [
    "The main branch computes renewable nameplate capacity as the maximum p_max "
    "across ALL representative periods. The commitment_period branch only examines "
    "the first representative period (m.md). This may underestimate nameplate capacity "
    "for generators whose maximum output varies seasonally. ",
    ("commitment_period should adopt main's approach of taking the maximum across "
     "all representative periods.", {"u"}),
])

# ── 4. Bug Audit ──
doc.add_heading("4. Bugs Fixed on commitment_period That Also Exist on main", level=1)
add_mixed(doc, [
    "The following bugs were discovered and fixed during CRC testing of the "
    "commitment_period branch. ",
    ("All of these bugs also exist on the main branch and should be upstreamed.", {"i"}),
    " They will manifest when running the Texas case study (scale_texas_loads=True) "
    "or when using data that lacks certain optional fields.",
])

# Bug table — 3 columns now (no severity column; we mark italic in description)
bug_tbl = doc.add_table(rows=9, cols=4, style="Light Shading Accent 1")
bug_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
bug_headers = ["#", "Bug Description", "Severity", "File(s)"]
for i, h in enumerate(bug_headers):
    bug_tbl.rows[0].cells[i].text = h
    for p in bug_tbl.rows[0].cells[i].paragraphs:
        for r in p.runs:
            r.bold = True

bugs = [
    [
        "1",
        "GEN UID type mismatch: int vs str comparison in "
        "texas_case_study_updates() causes silent lookup failures → TypeError",
        "High",
        "gtep_data.py",
    ],
    [
        "2",
        "non_fuel_startup_cost missing: generators without this field cause "
        "KeyError when constructing m.startupCost parameter",
        "High",
        "gtep_data.py",
    ],
    [
        "3",
        "Stage-specific cost params deleted: fixedCost1/2/3, varCost1/2/3, "
        "fuelCost1/2/3 declarations removed in ESR WIP refactor (dfce77d) but "
        "still referenced in investment_stage_rule → AttributeError",
        "High",
        "gtep_model.py",
    ],
    [
        "4",
        "time_keys incompatibility: gridx-prescient 2.2.2 does not convert "
        "time_keys to date strings, causing ValueError in date lookup",
        "Medium",
        "gtep_data.py",
    ],
    [
        "5",
        "Block-level reference errors: load_scaling is declared on the "
        "investmentStage block but accessed via the commitmentPeriod block "
        "(two levels too deep); similarly, loads accessed via dispatchPeriod "
        "block instead of commitmentPeriod block",
        "Medium",
        "gtep_model.py",
    ],
    [
        "6",
        "Missing storage guard: when storage.csv does not exist, m.storage Set "
        "is never created, but CP_flow_balance unconditionally iterates over it "
        "→ AttributeError",
        "Medium",
        "gtep_model.py",
    ],
    [
        "7",
        "rampUpRates/rampDownRates unit annotation: declared as MW/min but "
        "actual values are dimensionless ratios (e.g., 0.1 = 10%/period); "
        "may cause Pyomo unit-consistency check failures",
        "Low",
        "gtep_model.py",
    ],
    [
        "8",
        'Logic bug in texas_case_study_updates: '
        '"if \\"Texas\\" or \\"Coal\\" not in data_path" always evaluates True '
        "(Python operator precedence), making the guard ineffective",
        "Low",
        "gtep_data.py",
    ],
]
for i, row in enumerate(bugs):
    for j, val in enumerate(row):
        cell = bug_tbl.rows[i + 1].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(val)
        r.italic = True  # all bugs in this table are upstream-needed
        if j == 2:
            sev = val.strip()
            if sev == "High":
                r.font.color.rgb = RGBColor(192, 0, 0)
                r.bold = True
            elif sev == "Medium":
                r.font.color.rgb = RGBColor(196, 120, 0)
            elif sev == "Low":
                r.font.color.rgb = RGBColor(80, 80, 80)

# ── 5. Detail on High-Severity Bugs ──
doc.add_heading("5. Detail on High-Severity Bugs", level=1)

doc.add_heading("5.1 GEN UID Type Mismatch (#1)", level=2)
add_mixed(doc, [
    "In texas_case_study_updates(), generator data from gen.csv is merged with "
    "the in-memory model data. The merge uses GEN UID as the join key. When pandas "
    "reads gen.csv, the GEN UID column may be typed as int64. However, the generator "
    "dictionary keys (from Egret/Prescient parsing) are strings. Comparing int to str "
    "in pandas silently produces zero matches. ",
    ("This bug exists on main and should be upstreamed.", {"i"}),
])
doc.add_paragraph("Fix applied on commitment_period:")
fix1 = doc.add_paragraph()
fix1_run = fix1.add_run(
    '    generator_df["GEN UID"] = generator_df["GEN UID"].astype(str)\n'
    "    matched = generator_df.loc[generator_df[\"GEN UID\"] == gen, col]\n"
    "    if not matched.empty:\n"
    '        data[gen][col] = float(matched.iloc[0])'
)
fix1_run.font.name = "Consolas"
fix1_run.font.size = Pt(9)

doc.add_heading("5.2 non_fuel_startup_cost Missing (#2)", level=2)
add_mixed(doc, [
    "The model constructs m.startupCost by reading non_fuel_startup_cost from each "
    "thermal generator's data dictionary. However, not all generators in the RTS-GMLC "
    "dataset have this field populated (the corresponding column in gen.csv may be NaN "
    "or absent). When the field is missing, a KeyError is raised during model construction. ",
    ("This bug exists on main and should be upstreamed.", {"i"}),
])
doc.add_paragraph("Fix applied on commitment_period:")
fix2 = doc.add_paragraph()
fix2_run = fix2.add_run(
    '    gen_data.setdefault("non_fuel_startup_cost", 0)'
)
fix2_run.font.name = "Consolas"
fix2_run.font.size = Pt(9)
doc.add_paragraph(
    "This preserves the original value if present, and defaults to zero (no non-fuel "
    "startup cost) if absent."
)

doc.add_heading("5.3 Stage-Specific Cost Parameters Deleted (#3)", level=2)
add_mixed(doc, [
    "Commit dfce77d (ESR WIP / testing WECC data) removed the declarations of "
    "fixedCost1/2/3, varCost1/2/3, and fuelCost1/2/3 parameters from "
    "model_data_references(). However, these parameters are still referenced in "
    "investment_stage_rule() under the scale_texas_loads branch. This is a classic "
    "incomplete refactoring bug — the declarations were deleted but the usages were not. ",
    ("This bug exists on main and should be upstreamed.", {"i"}),
])
doc.add_paragraph(
    "Fix applied on commitment_period: Restored the parameter declarations in "
    "model_data_references(), reading from generator data fields fixed_ops1/2/3, "
    "var_ops1/2/3, and fuel_cost1/2/3. Uses .get(key, 0) for defensive access "
    "since candidate generators may lack these fields."
)

# ── 6. Block-Level Reference Bugs ──
doc.add_heading("6. Block-Level Reference Bugs (Detail)", level=1)
doc.add_paragraph(
    "The GTEP model uses a nested Pyomo Block hierarchy:"
)
hierarchy = doc.add_paragraph()
h_run = hierarchy.add_run(
    "    m.investmentStage[stage]                    ← load_scaling declared here\n"
    "      └─ .representativePeriod[period]\n"
    "           └─ .commitmentPeriod[cp]             ← loads declared here\n"
    "                └─ .dispatchPeriod[dp]           ← 'b' variable points here"
)
h_run.font.name = "Consolas"
h_run.font.size = Pt(9)

add_mixed(doc, [
    "Two reference bugs were found where code accessed attributes on the wrong "
    "block level. ",
    ("Both bugs exist on main and should be upstreamed:", {"i"}),
])
ref_bugs = [
    ("load_scaling: Declared on investmentStage, but commitment_period_rule accessed "
     "it via 'b' (commitmentPeriod block, two levels too deep). "
     "Fix: b.load_scaling → i_p.load_scaling, where i_p is obtained via "
     "r_p.parent_block() at the function's entry.", {"i"}),
    ("loads: Declared on commitmentPeriod, but CP_flow_balance accessed it via 'b' "
     "(dispatchPeriod block, one level too deep). "
     "Fix: b.loads → c_p.loads.", {"i"}),
]
for text, fmt in ref_bugs:
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    if "i" in fmt:
        r.italic = True

# ── 7. Improvements on main ──
doc.add_heading("7. Improvements on main That commitment_period Should Adopt", level=1)

imp_tbl = doc.add_table(rows=5, cols=3, style="Light Shading Accent 1")
imp_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
imp_headers = ["#", "Improvement", "Priority"]
for i, h in enumerate(imp_headers):
    imp_tbl.rows[0].cells[i].text = h
    for p in imp_tbl.rows[0].cells[i].paragraphs:
        for r in p.runs:
            r.bold = True

imps = [
    [
        "1",
        "renewableCapacityNameplate: take max p_max across all representative "
        "periods instead of only the first one — affects model correctness",
        "High",
    ],
    [
        "2",
        "load_prescient parameterization: representative_dates, "
        "representative_weights, options_dict as function arguments",
        "Low",
    ],
    [
        "3",
        "load_default_data_settings: defensive key-existence checks before "
        'accessing nested dicts (if "elements" in data.keys())',
        "Low",
    ],
    [
        "4",
        "Code modularization: split model code into model_library/ submodules "
        "(investment, dispatch, commitment, objective, storage, transmission)",
        "Low",
    ],
]
for i, row in enumerate(imps):
    for j, val in enumerate(row):
        cell = imp_tbl.rows[i + 1].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(val)
        r.underline = True  # all improvements here are user's action items

# ── 8. Current Pipeline Status ──
doc.add_heading("8. Current Pipeline Status (commitment_period branch)", level=1)

doc.add_paragraph(
    "After 17 rounds of debugging, the full model-construction pipeline passes "
    "successfully for all three temporal configurations (1hr, 2hr, 4hr commitment periods):"
)

status = doc.add_paragraph()
s_run = status.add_run(
    "load_prescient ✓ → texas_case_study_updates ✓ → model_data_references ✓\n"
    "→ investment_stages ✓ → commitment_period ✓ → dispatch ✓\n"
    "→ create_model ✓ → BigM transformation ✓ → Gurobi solve ✗ (environment issue)"
)
s_run.font.name = "Consolas"
s_run.font.size = Pt(10)

doc.add_paragraph(
    "The remaining failure is an environment configuration issue on the CRC cluster: "
    "GurobiDirect cannot locate the Gurobi solver binary. This is not a code bug. "
    "Model construction times (for 3 investment stages, 4 representative days, "
    "292 generators):"
)

time_tbl = doc.add_table(rows=4, cols=3, style="Light Shading Accent 1")
time_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
time_headers = ["Configuration", "create_model (s)", "BigM transform (s)"]
for i, h in enumerate(time_headers):
    time_tbl.rows[0].cells[i].text = h
    for p in time_tbl.rows[0].cells[i].paragraphs:
        for r in p.runs:
            r.bold = True

times = [
    ["1hr commitment", "214.71", "903.59"],
    ["2hr commitment", "114.07", "466.70"],
    ["4hr commitment", "68.48", "280.05"],
]
for i, row in enumerate(times):
    for j, val in enumerate(row):
        time_tbl.rows[i + 1].cells[j].text = val

# ── 9. Recommended Actions ──
doc.add_heading("9. Recommended Next Steps", level=1)

# Upstream actions (italic)
p1 = doc.add_paragraph(style="List Number")
r1 = p1.add_run(
    "Upstream high-severity fixes (#1–3) to main via pull request — these affect "
    "any run using scale_texas_loads=True or data with missing optional fields."
)
r1.italic = True

# User action (underline)
p2 = doc.add_paragraph(style="List Number")
r2 = p2.add_run(
    "Adopt renewableCapacityNameplate improvement from main into commitment_period "
    "to ensure correct nameplate capacity across seasonal variation."
)
r2.underline = True

# Neutral
p3 = doc.add_paragraph(style="List Number")
p3.add_run(
    "Resolve CRC Gurobi environment issue (gurobipy version matching with "
    "module-loaded Gurobi) to unblock solver testing."
)

# Neutral
p4 = doc.add_paragraph(style="List Number")
p4.add_run(
    "Once solver runs, validate model feasibility and solution quality across "
    "1hr/2hr/4hr commitment period configurations."
)

# ── Save ──
out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_path = os.path.join(
    out_dir, "2026-05-21_main_vs_commitment_period_branch_comparison.docx"
)
doc.save(out_path)
print(f"Saved to {out_path}")
