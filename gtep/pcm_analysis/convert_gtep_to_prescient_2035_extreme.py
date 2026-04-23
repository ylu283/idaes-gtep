"""
Convert GTEP Stage 3 solution (extreme half-load) to Prescient 2035 input data.

Produces gen.csv, timeseries_pointers.csv, and supporting files for
retirement_allowed_extreme_half_load/Prescient_2_2035/.

Adapts the same pipeline used for the no-extreme case
(convert_gtep_to_prescient_2035.ipynb) with the extreme GTEP investment decisions.

Key difference from no-extreme:
  - GTEP solution: different CT investments (13 different sites),
    6 additional existing generators, different renewable MW allocations
  - Fleet size: 289 generators (vs 278 for no-extreme)
  - All 12 COAL plants kept (extended) in both scenarios
  - Load/wind/solar timeseries are identical between scenarios

Usage:
    python convert_gtep_to_prescient_2035_extreme.py
"""

import json
import shutil
from pathlib import Path

import pandas as pd

# ── Configuration ─────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # idaes-gtep/

EXTREME_DIR = REPO_ROOT / "gtep/data/retirement_allowed_extreme_half_load"
SOLUTION_DISP = EXTREME_DIR / "dispatchable_investments.json"
SOLUTION_RENEW = EXTREME_DIR / "renewable_investments.json"

# Existing generator source (correct 4-segment cost curves, ramp rates)
# Same pool of existing generators for both scenarios
CORRECT_GEN = (
    REPO_ROOT
    / "gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2/gen.csv"
)

# fuel_cost3 lookup (2035 fuel pricing)
FUEL_COST_GEN = REPO_ROOT / "gtep/data/123_Bus_Coal/Prescient/gen.csv"

# Candidate generator parameters
CANDIDATE_GEN = REPO_ROOT / "gtep/data/123_Bus_Coal/candidate_generators_initial_list.csv"

# Base timeseries pointers (extreme case has its own, 1550 rows)
BASE_POINTERS = EXTREME_DIR / "Prescient_2/timeseries_pointers.csv"

# Static files from extreme Prescient_2
STATIC_DIR = EXTREME_DIR / "Prescient_2"

# Timeseries from extreme case
TIMESERIES_DIR = EXTREME_DIR / "Prescient_2/timeseries_2035"

# Output
OUTPUT_DIR = EXTREME_DIR / "Prescient_2_2035"

GTEP_STAGE = 3  # 2035


def parse_gtep_solution():
    """Parse dispatchable + renewable investment decisions for stage 3."""
    with open(SOLUTION_DISP) as f:
        disp_raw = json.load(f)
    with open(SOLUTION_RENEW) as f:
        renew_raw = json.load(f)

    prefix = f"investmentStage[{GTEP_STAGE}]"

    # Dispatchable: flat keys like "investmentStage[3].genOperational.26"
    disp_s3 = {}
    for key, val in disp_raw.items():
        if not key.startswith(prefix):
            continue
        parts = key.split(".")
        decision, gen_id = parts[1], parts[2]
        disp_s3.setdefault(decision, {})[gen_id] = val

    # Active = operational + installed + extended - retired - disabled
    active_thermal = set()
    for d in ["genOperational", "genInstalled", "genExtended"]:
        active_thermal |= {g for g, v in disp_s3.get(d, {}).items() if v}
    active_thermal -= {g for g, v in disp_s3.get("genRetired", {}).items() if v}
    active_thermal -= {g for g, v in disp_s3.get("genDisabled", {}).items() if v}

    # Renewable capacity (continuous MW)
    ren_cap = {}
    for key, val in renew_raw.items():
        if not key.startswith(prefix):
            continue
        parts = key.split(".")
        decision, gen_id = parts[1], parts[2]
        if decision in (
            "renewableOperational",
            "renewableInstalled",
            "renewableExtended",
        ):
            ren_cap[gen_id] = ren_cap.get(gen_id, 0) + val
    # Drop near-zero
    ren_cap = {k: v for k, v in ren_cap.items() if v > 0.01}

    invested = active_thermal | set(ren_cap.keys())

    print(f"Dispatchable active: {len(active_thermal)}")
    print(
        f"  existing={len({g for g in active_thermal if not g.endswith('-c')})},"
        f" candidate={len({g for g in active_thermal if g.endswith('-c')})}"
    )
    print(f"Renewable active: {len(ren_cap)} ({sum(ren_cap.values()):.1f} MW)")
    print(f"Total invested: {len(invested)}")

    return active_thermal, ren_cap, invested


def build_gen_csv(invested_gen_set, renewable_capacity):
    """Build gen.csv from base generators + GTEP investment decisions."""
    # 1. Load source data
    correct_gen = pd.read_csv(CORRECT_GEN)
    correct_gen["GEN UID"] = correct_gen["GEN UID"].astype(str)
    print(f"\nBase gen source: {len(correct_gen)} rows")

    fuel_cost_gen = pd.read_csv(FUEL_COST_GEN)
    fuel_cost_gen["GEN UID"] = fuel_cost_gen["GEN UID"].astype(str)
    fuel_cost_lookup = fuel_cost_gen.set_index("GEN UID")["fuel_cost3"].to_dict()

    candidate_gen = pd.read_csv(CANDIDATE_GEN)
    candidate_gen["GEN UID"] = candidate_gen["GEN UID"].astype(str)

    # 2. CT median heat rates for candidate CTs
    existing_ct = correct_gen[correct_gen["Unit Type"] == "CT"]
    ct_hr1 = existing_ct["HR_incr_1"].median()
    ct_hr2 = existing_ct["HR_incr_2"].median()
    ct_hr3 = existing_ct["HR_incr_3"].median()
    ct_ramp = existing_ct["Ramp Rate MW/Min"].median()
    ct_csu = existing_ct["Csu"].median()

    # 3. Combine sources
    target_cols = correct_gen.columns.tolist()
    cand_rows = candidate_gen.copy()
    for col in target_cols:
        if col not in cand_rows.columns:
            cand_rows[col] = pd.NA
    combined = pd.concat(
        [correct_gen, cand_rows[target_cols]], ignore_index=True
    )

    # 4. Synthesize missing generators
    invested_str = {str(g) for g in invested_gen_set}
    combined_uids = set(combined["GEN UID"])
    still_missing = invested_str - combined_uids

    if still_missing:
        print(f"Synthesizing {len(still_missing)} generators not in any source")
        ct_tmpl = correct_gen[correct_gen["Unit Type"] == "CT"].iloc[0].copy()
        wind_tmpl = correct_gen[correct_gen["Unit Type"] == "WIND"].iloc[0].copy()
        pv_tmpl = correct_gen[correct_gen["Unit Type"] == "PV"].iloc[0].copy()

        synth_rows = []
        for gen_id in sorted(still_missing):
            if gen_id.startswith("ct_fe_"):
                row = ct_tmpl.copy()
                bus_id = int(gen_id.split("_")[2])
            elif gen_id.startswith("pv_"):
                row = pv_tmpl.copy()
                bus_id = int(gen_id.replace("pv_", "").replace("-c", ""))
            elif gen_id.startswith("wind_"):
                row = wind_tmpl.copy()
                bus_id = int(gen_id.replace("wind_", "").replace("-c", ""))
            else:
                # Existing generator not in Prescient_2 gen.csv — use CT template
                # and set Bus ID from the gen_id (numeric IDs are existing gens)
                try:
                    bus_id_lookup = int(gen_id)
                except ValueError:
                    print(f"  Skipping unknown type: {gen_id}")
                    continue
                # For existing generators, try to find them in fuel_cost_gen
                if gen_id in fuel_cost_gen["GEN UID"].values:
                    src_row = fuel_cost_gen[
                        fuel_cost_gen["GEN UID"] == gen_id
                    ].iloc[0]
                    row = ct_tmpl.copy()  # base template
                    # Copy what we can from the fuel_cost source
                    for col in target_cols:
                        if col in src_row.index and pd.notna(src_row[col]):
                            row[col] = src_row[col]
                    bus_id = int(src_row.get("Bus ID", bus_id_lookup))
                else:
                    row = ct_tmpl.copy()
                    bus_id = bus_id_lookup

            row["GEN UID"] = gen_id
            row["Bus ID"] = bus_id
            if gen_id in renewable_capacity:
                row["PMax MW"] = renewable_capacity[gen_id]
            synth_rows.append(row)
            print(f"  Synthesized: {gen_id} (Bus {bus_id})")

        synth_df = pd.DataFrame(synth_rows)
        combined = pd.concat([combined, synth_df], ignore_index=True)

    # 5. Filter to invested generators
    gen_df = combined[combined["GEN UID"].isin(invested_str)].copy()
    print(f"Filtered to invested: {len(gen_df)} rows")

    missing_final = invested_str - set(gen_df["GEN UID"])
    if missing_final:
        print(f"WARNING: {len(missing_final)} still missing: {sorted(missing_final)}")
    else:
        print("All invested generators found.")

    # 6. Merge fuel_cost3
    gen_df["fuel_cost3"] = gen_df["GEN UID"].map(fuel_cost_lookup)
    cand_fuel = candidate_gen.set_index("GEN UID")["fuel_cost3"].to_dict()
    gen_df["fuel_cost3"] = gen_df["fuel_cost3"].fillna(gen_df["GEN UID"].map(cand_fuel))

    fuel_defaults = {"G": 22.80128, "C": 18.93942, "N": 7.378403, "W": 0.0, "S": 0.0, "H": 0.0}
    for fuel_code, default in fuel_defaults.items():
        mask = gen_df["fuel_cost3"].isna() & (gen_df["Fuel"] == fuel_code)
        if mask.any():
            gen_df.loc[mask, "fuel_cost3"] = default
            print(f"  Filled fuel_cost3={default} for {mask.sum()} gens (Fuel={fuel_code})")

    # 7. Fill candidate CT parameters
    is_cand_ct = gen_df["GEN UID"].str.startswith("ct_fe_")
    gen_df.loc[is_cand_ct & gen_df["HR_avg_0"].isna(), "HR_avg_0"] = 0
    gen_df.loc[is_cand_ct & gen_df["HR_incr_1"].isna(), "HR_incr_1"] = ct_hr1
    gen_df.loc[is_cand_ct & gen_df["HR_incr_2"].isna(), "HR_incr_2"] = ct_hr2
    gen_df.loc[is_cand_ct & gen_df["HR_incr_3"].isna(), "HR_incr_3"] = ct_hr3
    gen_df.loc[is_cand_ct & gen_df["Output_pct_2"].isna(), "Output_pct_1"] = 0.533333333
    gen_df.loc[is_cand_ct & gen_df["Output_pct_2"].isna(), "Output_pct_2"] = 0.766666667
    gen_df.loc[is_cand_ct & gen_df["Output_pct_3"].isna(), "Output_pct_3"] = 1.0
    for col in ["Start Time Cold Hr", "Start Time Warm Hr", "Start Time Hot Hr"]:
        gen_df.loc[is_cand_ct & gen_df[col].isna(), col] = 1
    for col in ["Start Heat Cold MBTU", "Start Heat Warm MBTU", "Start Heat Hot MBTU"]:
        gen_df.loc[is_cand_ct & gen_df[col].isna(), col] = 1
    gen_df.loc[is_cand_ct & gen_df["Ramp Rate MW/Min"].isna(), "Ramp Rate MW/Min"] = ct_ramp
    if "Csu" in gen_df.columns:
        gen_df.loc[is_cand_ct & gen_df["Csu"].isna(), "Csu"] = ct_csu
    if "Non Fuel Start Cost $" in gen_df.columns:
        gen_df.loc[
            is_cand_ct & gen_df["Non Fuel Start Cost $"].isna(), "Non Fuel Start Cost $"
        ] = 0

    # 8. Recompute HR_avg_0 and HR_incr from C0/C1/C2 cost curves
    gen_df = _recompute_hr(gen_df)

    # 9. Back-calculate Fuel Price from fuel_cost3
    # fuel_cost3 is $/MWh; Prescient computes MC = FP * HR_incr_1 * 0.001
    # So FP = fuel_cost3 / (HR_incr_1 * 0.001)
    is_renewable = gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"])
    gen_df["Fuel Price $/MMBTU"] = gen_df["Fuel Price $/MMBTU"].astype(float)
    thermal_mask = ~is_renewable & (gen_df["HR_incr_1"] > 0)
    gen_df.loc[thermal_mask, "Fuel Price $/MMBTU"] = (
        gen_df.loc[thermal_mask, "fuel_cost3"].astype(float)
        / (gen_df.loc[thermal_mask, "HR_incr_1"].astype(float) * 0.001)
    )
    gen_df.loc[is_renewable, "Fuel Price $/MMBTU"] = 0.00001

    # 10. Fill renewable fields
    is_cand_renew = gen_df["GEN UID"].str.match(r"^(pv|wind)_")
    all_renew = is_renewable | is_cand_renew
    for col in ["HR_avg_0", "HR_incr_1", "HR_incr_2", "HR_incr_3", "HR_incr_4"]:
        if col in gen_df.columns:
            gen_df.loc[all_renew, col] = gen_df.loc[all_renew, col].fillna(0)
    for col in [
        "Start Time Cold Hr", "Start Time Warm Hr", "Start Time Hot Hr",
        "Start Heat Cold MBTU", "Start Heat Warm MBTU", "Start Heat Hot MBTU",
        "Min Down Time Hr", "Min Up Time Hr",
    ]:
        if col in gen_df.columns:
            gen_df.loc[is_cand_renew & gen_df[col].isna(), col] = 0
    if "Non Fuel Start Cost $" in gen_df.columns:
        gen_df.loc[
            is_cand_renew & gen_df["Non Fuel Start Cost $"].isna(),
            "Non Fuel Start Cost $",
        ] = 0
    gen_df.loc[is_cand_renew & gen_df["PMin MW"].isna(), "PMin MW"] = 0
    gen_df.loc[all_renew, "Output_pct_0"] = 0.0

    # 11. Update renewable PMax from GTEP solution
    for gen_id, mw in renewable_capacity.items():
        mask = gen_df["GEN UID"] == str(gen_id)
        if mask.any():
            gen_df.loc[mask, "PMax MW"] = mw

    # 12. Clean up
    gen_df["Bus ID"] = gen_df["Bus ID"].astype(int)
    gtep_cols = [
        "capex1", "capex2", "capex3",
        "fuel_cost1", "fuel_cost2", "fuel_cost3",
        "fixed_ops1", "fixed_ops2", "fixed_ops3",
        "var_ops1", "var_ops2", "var_ops3",
    ]
    gen_df = gen_df.drop(columns=[c for c in gtep_cols if c in gen_df.columns])
    if "BUS ID" not in gen_df.columns:
        gen_df["BUS ID"] = gen_df["Bus ID"]

    return gen_df


def _recompute_hr(gen_df):
    """Recompute HR_avg_0 and HR_incr from C0/C1/C2 quadratic cost curves."""
    thermal_with_cost = (
        gen_df["C0"].notna()
        & gen_df["C1"].notna()
        & gen_df["C2"].notna()
        & (gen_df["Fuel Price $/MMBTU"].astype(float) > 0.001)
        & ~gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"])
    )
    for idx in gen_df[thermal_with_cost].index:
        c0, c1, c2 = (
            float(gen_df.at[idx, "C0"]),
            float(gen_df.at[idx, "C1"]),
            float(gen_df.at[idx, "C2"]),
        )
        fp = float(gen_df.at[idx, "Fuel Price $/MMBTU"])
        pmax = float(gen_df.at[idx, "PMax MW"])
        pcts = []
        for i in range(4):
            col = f"Output_pct_{i}"
            if col in gen_df.columns and pd.notna(gen_df.at[idx, col]):
                pcts.append(float(gen_df.at[idx, col]))
            else:
                break
        if len(pcts) < 2 or fp < 0.001 or pmax <= 0:
            continue
        p = [pct * pmax for pct in pcts]
        costs = [c0 + c1 * pi + c2 * pi**2 for pi in p]
        if p[0] > 0:
            gen_df.at[idx, "HR_avg_0"] = costs[0] / (fp * p[0]) * 1000
        for i in range(1, len(p)):
            dp = p[i] - p[i - 1]
            dc = costs[i] - costs[i - 1]
            if dp > 0:
                gen_df.at[idx, f"HR_incr_{i}"] = dc / (fp * dp) * 1000
    return gen_df


def build_timeseries_pointers(gen_df):
    """Filter timeseries_pointers.csv to invested generators."""
    ptrs = pd.read_csv(BASE_POINTERS)
    gen_uids = set(gen_df["GEN UID"].astype(str))

    non_gen = ptrs["Category"] != "Generator"
    gen_match = (ptrs["Category"] == "Generator") & (
        ptrs["Object"].astype(str).isin(gen_uids)
    )
    filtered = ptrs[non_gen | gen_match].copy()

    # Add missing DAY_AHEAD pointers for candidate renewables
    cand_rt = filtered[
        (filtered["Simulation"] == "REAL_TIME")
        & (filtered["Category"] == "Generator")
        & (filtered["Object"].astype(str).str.match(r"^(pv|wind)_"))
    ].copy()
    existing_da = filtered[
        (filtered["Simulation"] == "DAY_AHEAD")
        & (filtered["Category"] == "Generator")
        & (filtered["Object"].astype(str).str.match(r"^(pv|wind)_"))
    ]
    if len(cand_rt) > 0 and len(existing_da) == 0:
        da_ptrs = cand_rt.copy()
        da_ptrs["Simulation"] = "DAY_AHEAD"
        da_ptrs["Data File"] = da_ptrs["Data File"].str.replace(
            "REAL_TIME_", "DAY_AHEAD_"
        )
        filtered = pd.concat([filtered, da_ptrs], ignore_index=True)
        print(f"  Added {len(da_ptrs)} DAY_AHEAD pointers for candidate renewables")

    print(f"Timeseries pointers: {len(ptrs)} -> {len(filtered)} rows")
    return filtered


def copy_static_files():
    """Copy bus, branch, simulation_objects, and timeseries files."""
    # bus.csv and branch.csv from extreme Prescient_2
    for fname in ["bus.csv", "branch.csv"]:
        shutil.copy2(STATIC_DIR / fname, OUTPUT_DIR / fname)
        print(f"  Copied {fname}")

    # Timeseries from extreme timeseries_2035/
    for fname in [
        "DAY_AHEAD_load.csv", "REAL_TIME_load.csv",
        "DAY_AHEAD_wind.csv", "REAL_TIME_wind.csv",
        "DAY_AHEAD_solar.csv", "REAL_TIME_solar.csv",
    ]:
        src = TIMESERIES_DIR / fname
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / fname)
            print(f"  Copied {fname}")
        else:
            print(f"  WARNING: {fname} not found")

    # simulation_objects.csv — update dates to 2035
    sim_obj = pd.read_csv(STATIC_DIR / "simulation_objects.csv")
    sim_obj.loc[
        sim_obj["Simulation_Parameters"] == "Date_From", "DAY_AHEAD"
    ] = "1/1/2035 0:00"
    sim_obj.loc[
        sim_obj["Simulation_Parameters"] == "Date_From", "REAL_TIME"
    ] = "1/1/2035 0:00"
    sim_obj.loc[
        sim_obj["Simulation_Parameters"] == "Date_To", "DAY_AHEAD"
    ] = "12/31/2035 0:00"
    sim_obj.loc[
        sim_obj["Simulation_Parameters"] == "Date_To", "REAL_TIME"
    ] = "12/31/2035 0:00"
    sim_obj.to_csv(OUTPUT_DIR / "simulation_objects.csv", index=False)
    print("  Wrote simulation_objects.csv (dates -> 2035)")


def validate(gen_df, ptrs_df):
    """Run validation checks on the converted data."""
    errors, warnings = [], []

    # Required files
    required = [
        "gen.csv", "branch.csv", "bus.csv", "simulation_objects.csv",
        "timeseries_pointers.csv",
        "DAY_AHEAD_load.csv", "REAL_TIME_load.csv",
        "DAY_AHEAD_wind.csv", "REAL_TIME_wind.csv",
        "DAY_AHEAD_solar.csv", "REAL_TIME_solar.csv",
    ]
    for fname in required:
        if not (OUTPUT_DIR / fname).exists():
            errors.append(f"Missing: {fname}")

    # Bus ID integrity
    bus_df = pd.read_csv(OUTPUT_DIR / "bus.csv")
    invalid_buses = set(gen_df["Bus ID"].astype(int)) - set(bus_df["Bus ID"])
    if invalid_buses:
        errors.append(f"Invalid bus IDs: {sorted(invalid_buses)}")

    # Thermal cost curves
    thermal = gen_df[~gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"])]
    if (thermal["Fuel Price $/MMBTU"] <= 0).any():
        errors.append("Thermal gens with zero fuel price")
    if (thermal["HR_incr_1"] <= 0).any():
        errors.append("Thermal gens with zero HR_incr_1")

    # MC validation
    expected_mc = {"CT": 22.80, "COAL": 18.94, "NUC": 7.38}
    for ut, exp in expected_mc.items():
        sub = gen_df[gen_df["Unit Type"] == ut]
        if len(sub) > 0:
            mc = sub["Fuel Price $/MMBTU"] * sub["HR_incr_1"] * 0.001
            if abs(mc.mean() - exp) > 1.0:
                errors.append(f"{ut} MC mismatch: {mc.mean():.2f} vs {exp}")

    # Orphan pointers
    gen_ptrs = ptrs_df[ptrs_df["Category"] == "Generator"]
    orphans = set(gen_ptrs["Object"].astype(str)) - set(gen_df["GEN UID"].astype(str))
    if orphans:
        warnings.append(f"Orphan pointers: {len(orphans)}")

    # Zero PMax renewables
    zero_pmax = gen_df[
        gen_df["Unit Type"].isin(["WIND", "PV"]) & (gen_df["PMax MW"] <= 0.01)
    ]
    if len(zero_pmax) > 0:
        warnings.append(f"{len(zero_pmax)} renewables with near-zero PMax")

    print(f"\nValidation: {len(errors)} errors, {len(warnings)} warnings")
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings:
        print(f"  WARN: {w}")
    return len(errors) == 0


def write_manifest(gen_df, ptrs_df, valid):
    """Write conversion_manifest.json."""
    from datetime import datetime

    manifest = {
        "scenario": "retirement_allowed_extreme_half_load",
        "gtep_stage": GTEP_STAGE,
        "conversion_date": datetime.now().strftime("%Y-%m-%d"),
        "source_solution": str(SOLUTION_DISP.relative_to(REPO_ROOT)),
        "source_gen": "no_extreme Prescient_2/gen.csv (correct cost curves)"
        " + 123_Bus_Coal/Prescient/gen.csv (fuel_cost3)",
        "counts": {
            "total_generators": len(gen_df),
            "thermal": len(
                gen_df[~gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"])]
            ),
            "renewable": len(
                gen_df[gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"])]
            ),
            "timeseries_pointer_rows": len(ptrs_df),
        },
        "total_installed_renewable_mw": round(
            gen_df.loc[
                gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"]), "PMax MW"
            ].sum(),
            1,
        ),
        "validation_passed": valid,
        "note": (
            "Extreme GTEP solution differs from no-extreme in CT investment "
            "locations and renewable MW allocations. Same COAL/NUC fleet "
            "(all 12 COAL extended). Load/wind/solar timeseries identical "
            "between scenarios."
        ),
    }
    with open(OUTPUT_DIR / "conversion_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote conversion_manifest.json")


def main():
    print("=" * 70)
    print("GTEP -> Prescient 2035 Conversion (EXTREME CASE)")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "results").mkdir(exist_ok=True)

    # 1. Parse GTEP solution
    print("\n── 1. Parse GTEP Solution ──")
    active_thermal, ren_cap, invested = parse_gtep_solution()

    # 2. Build gen.csv
    print("\n── 2. Build gen.csv ──")
    gen_df = build_gen_csv(invested, ren_cap)
    gen_df.to_csv(OUTPUT_DIR / "gen.csv", index=False)
    print(f"Wrote gen.csv: {len(gen_df)} generators")

    # Fleet summary
    print("\nFleet by type:")
    for ut in sorted(gen_df["Unit Type"].unique()):
        sub = gen_df[gen_df["Unit Type"] == ut]
        print(f"  {ut:6s}: {len(sub):4d} gens, {sub['PMax MW'].sum():10,.0f} MW")
    print(f"  {'TOTAL':6s}: {len(gen_df):4d} gens, {gen_df['PMax MW'].sum():10,.0f} MW")

    # MC check
    print("\nMC validation (FP * HR_incr_1 * 0.001):")
    for ut, exp in [("NUC", 7.38), ("COAL", 18.94), ("CT", 22.80)]:
        sub = gen_df[gen_df["Unit Type"] == ut]
        if len(sub):
            mc = (sub["Fuel Price $/MMBTU"] * sub["HR_incr_1"] * 0.001).mean()
            print(f"  {ut}: ${mc:.2f}/MWh (expected ${exp})")

    # 3. Timeseries pointers
    print("\n── 3. Timeseries Pointers ──")
    ptrs_df = build_timeseries_pointers(gen_df)
    ptrs_df.to_csv(OUTPUT_DIR / "timeseries_pointers.csv", index=False)

    # 4. Static + timeseries files
    print("\n── 4. Copy Static & Timeseries Files ──")
    copy_static_files()

    # 5. Validate
    print("\n── 5. Validate ──")
    valid = validate(gen_df, ptrs_df)

    # 6. Manifest
    print("\n── 6. Manifest ──")
    write_manifest(gen_df, ptrs_df, valid)

    # 7. Summary
    print("\n" + "=" * 70)
    print(f"Output: {OUTPUT_DIR}")
    print(f"Generators: {len(gen_df)}")
    print(f"Validation: {'PASSED' if valid else 'FAILED'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
