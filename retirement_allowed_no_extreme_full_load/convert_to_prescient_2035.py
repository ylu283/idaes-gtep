"""
Convert GTEP Stage 3 solution to Prescient 2035 input data.

Reads dispatchable_investments.json and renewable_investments.json from
the same directory, determines the active fleet, and produces a complete
Prescient_2_2035/ directory ready for simulation.

Adapted from gtep/pcm_analysis/convert_gtep_to_prescient_2035_extreme.py,
simplified for the commitment-period results (no candidate generator
synthesis needed — all active generators are in the existing fleet).

Usage:
    python convert_to_prescient_2035.py
"""

import json
import shutil
from pathlib import Path

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent

SOLUTION_DISP = THIS_DIR / "dispatchable_investments.json"
SOLUTION_RENEW = THIS_DIR / "renewable_investments.json"

CORRECT_GEN = (
    REPO_ROOT
    / "gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2/gen.csv"
)
FUEL_COST_GEN = REPO_ROOT / "gtep/data/123_Bus_Coal/Prescient/gen.csv"

STATIC_DIR = (
    REPO_ROOT / "gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2"
)
TIMESERIES_DIR = STATIC_DIR / "timeseries_2035"
BASE_POINTERS = STATIC_DIR / "timeseries_pointers.csv"

OUTPUT_DIR = THIS_DIR / "Prescient_2_2035"

GTEP_STAGE = 3


def parse_gtep_solution():
    """Parse dispatchable + renewable investment decisions for stage 3."""
    with open(SOLUTION_DISP) as f:
        disp_raw = json.load(f)
    with open(SOLUTION_RENEW) as f:
        renew_raw = json.load(f)

    prefix = f"investmentStage[{GTEP_STAGE}]"

    disp_s3 = {}
    for key, val in disp_raw.items():
        if not key.startswith(prefix):
            continue
        parts = key.split(".")
        decision, gen_id = parts[1], parts[2]
        disp_s3.setdefault(decision, {})[gen_id] = val

    active_thermal = set()
    for d in ["genOperational", "genInstalled", "genExtended"]:
        active_thermal |= {g for g, v in disp_s3.get(d, {}).items() if v}
    active_thermal -= {g for g, v in disp_s3.get("genRetired", {}).items() if v}
    active_thermal -= {g for g, v in disp_s3.get("genDisabled", {}).items() if v}

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
    ren_cap = {k: v for k, v in ren_cap.items() if v > 0.01}

    invested = active_thermal | set(ren_cap.keys())

    print(f"Dispatchable active: {len(active_thermal)}")
    print(f"Renewable active: {len(ren_cap)} ({sum(ren_cap.values()):.1f} MW)")
    print(f"Total invested: {len(invested)}")

    return active_thermal, ren_cap, invested


def build_gen_csv(invested_gen_set, renewable_capacity):
    """Build gen.csv from existing generators filtered to invested set."""
    correct_gen = pd.read_csv(CORRECT_GEN)
    correct_gen["GEN UID"] = correct_gen["GEN UID"].astype(str)
    print(f"\nBase gen source: {len(correct_gen)} rows")

    fuel_cost_gen = pd.read_csv(FUEL_COST_GEN)
    fuel_cost_gen["GEN UID"] = fuel_cost_gen["GEN UID"].astype(str)
    fuel_cost_lookup = fuel_cost_gen.set_index("GEN UID")["fuel_cost3"].to_dict()

    invested_str = {str(g) for g in invested_gen_set}
    gen_df = correct_gen[correct_gen["GEN UID"].isin(invested_str)].copy()
    print(f"Filtered to invested: {len(gen_df)} rows")

    missing = invested_str - set(gen_df["GEN UID"])
    if missing:
        print(f"WARNING: {len(missing)} generators not in source: {sorted(missing)}")

    # Merge fuel_cost3
    gen_df["fuel_cost3"] = gen_df["GEN UID"].map(fuel_cost_lookup)
    fuel_defaults = {
        "G": 22.80128, "C": 18.93942, "N": 7.378403,
        "W": 0.0, "S": 0.0, "H": 0.0,
    }
    for fuel_code, default in fuel_defaults.items():
        mask = gen_df["fuel_cost3"].isna() & (gen_df["Fuel"] == fuel_code)
        if mask.any():
            gen_df.loc[mask, "fuel_cost3"] = default
            print(f"  Filled fuel_cost3={default} for {mask.sum()} gens (Fuel={fuel_code})")

    # Recompute HR_avg_0 and HR_incr from C0/C1/C2 cost curves
    gen_df = _recompute_hr(gen_df)

    # Back-calculate Fuel Price from fuel_cost3
    is_renewable = gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"])
    gen_df["Fuel Price $/MMBTU"] = gen_df["Fuel Price $/MMBTU"].astype(float)
    thermal_mask = ~is_renewable & (gen_df["HR_incr_1"] > 0)
    gen_df.loc[thermal_mask, "Fuel Price $/MMBTU"] = (
        gen_df.loc[thermal_mask, "fuel_cost3"].astype(float)
        / (gen_df.loc[thermal_mask, "HR_incr_1"].astype(float) * 0.001)
    )
    gen_df.loc[is_renewable, "Fuel Price $/MMBTU"] = 0.00001

    # Set renewable Output_pct_0 to 0
    gen_df.loc[is_renewable, "Output_pct_0"] = 0.0

    # Update renewable PMax from GTEP solution
    for gen_id, mw in renewable_capacity.items():
        mask = gen_df["GEN UID"] == str(gen_id)
        if mask.any():
            gen_df.loc[mask, "PMax MW"] = mw

    # Clean up
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
    print(f"Timeseries pointers: {len(ptrs)} -> {len(filtered)} rows")
    return filtered


def copy_static_files():
    """Copy bus, branch, simulation_objects, and timeseries files."""
    for fname in ["bus.csv", "branch.csv"]:
        shutil.copy2(STATIC_DIR / fname, OUTPUT_DIR / fname)
        print(f"  Copied {fname}")

    for fname in [
        "DAY_AHEAD_load.csv", "REAL_TIME_load.csv",
        "DAY_AHEAD_wind.csv", "REAL_TIME_wind.csv",
        "DAY_AHEAD_solar.csv", "REAL_TIME_solar.csv",
    ]:
        src = TIMESERIES_DIR / fname
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / fname)
            print(f"  Copied {fname} (from timeseries_2035/)")
        else:
            src_alt = STATIC_DIR / fname
            if src_alt.exists():
                shutil.copy2(src_alt, OUTPUT_DIR / fname)
                print(f"  Copied {fname} (from Prescient_2/)")
            else:
                print(f"  WARNING: {fname} not found")

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

    bus_df = pd.read_csv(OUTPUT_DIR / "bus.csv")
    invalid_buses = set(gen_df["Bus ID"].astype(int)) - set(bus_df["Bus ID"])
    if invalid_buses:
        errors.append(f"Invalid bus IDs: {sorted(invalid_buses)}")

    thermal = gen_df[~gen_df["Unit Type"].isin(["WIND", "PV", "HYDRO"])]
    if (thermal["Fuel Price $/MMBTU"] <= 0).any():
        errors.append("Thermal gens with zero fuel price")
    if (thermal["HR_incr_1"] <= 0).any():
        errors.append("Thermal gens with zero HR_incr_1")

    expected_mc = {"CT": 22.80, "COAL": 18.94, "NUC": 7.38}
    for ut, exp in expected_mc.items():
        sub = gen_df[gen_df["Unit Type"] == ut]
        if len(sub) > 0:
            mc = sub["Fuel Price $/MMBTU"] * sub["HR_incr_1"] * 0.001
            if abs(mc.mean() - exp) > 1.0:
                errors.append(f"{ut} MC mismatch: {mc.mean():.2f} vs {exp}")

    gen_ptrs = ptrs_df[ptrs_df["Category"] == "Generator"]
    orphans = set(gen_ptrs["Object"].astype(str)) - set(gen_df["GEN UID"].astype(str))
    if orphans:
        warnings.append(f"Orphan pointers: {len(orphans)}")

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
        "scenario": THIS_DIR.name,
        "gtep_stage": GTEP_STAGE,
        "conversion_date": datetime.now().strftime("%Y-%m-%d"),
        "source_solution": str(SOLUTION_DISP.name),
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
            "Commitment-period GTEP results with placeholder costs (all=1). "
            "No new investments or retirements — 13 COAL extensions. "
            "PCM differences across 1HR/2HR/4HR come from dispatch feasibility, "
            "not fleet composition."
        ),
    }
    with open(OUTPUT_DIR / "conversion_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote conversion_manifest.json")


def main():
    print("=" * 70)
    print(f"GTEP -> Prescient 2035 Conversion ({THIS_DIR.name})")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "results").mkdir(exist_ok=True)

    print("\n-- 1. Parse GTEP Solution --")
    active_thermal, ren_cap, invested = parse_gtep_solution()

    print("\n-- 2. Build gen.csv --")
    gen_df = build_gen_csv(invested, ren_cap)
    gen_df.to_csv(OUTPUT_DIR / "gen.csv", index=False)
    print(f"Wrote gen.csv: {len(gen_df)} generators")

    print("\nFleet by type:")
    for ut in sorted(gen_df["Unit Type"].unique()):
        sub = gen_df[gen_df["Unit Type"] == ut]
        print(f"  {ut:6s}: {len(sub):4d} gens, {sub['PMax MW'].sum():10,.0f} MW")
    print(f"  {'TOTAL':6s}: {len(gen_df):4d} gens, {gen_df['PMax MW'].sum():10,.0f} MW")

    print("\nMC validation (FP * HR_incr_1 * 0.001):")
    for ut, exp in [("NUC", 7.38), ("COAL", 18.94), ("CT", 22.80)]:
        sub = gen_df[gen_df["Unit Type"] == ut]
        if len(sub):
            mc = (sub["Fuel Price $/MMBTU"] * sub["HR_incr_1"] * 0.001).mean()
            print(f"  {ut}: ${mc:.2f}/MWh (expected ${exp})")

    print("\n-- 3. Timeseries Pointers --")
    ptrs_df = build_timeseries_pointers(gen_df)
    ptrs_df.to_csv(OUTPUT_DIR / "timeseries_pointers.csv", index=False)

    print("\n-- 4. Copy Static & Timeseries Files --")
    copy_static_files()

    print("\n-- 5. Validate --")
    valid = validate(gen_df, ptrs_df)

    print("\n-- 6. Manifest --")
    write_manifest(gen_df, ptrs_df, valid)

    print("\n" + "=" * 70)
    print(f"Output: {OUTPUT_DIR}")
    print(f"Generators: {len(gen_df)}")
    print(f"Validation: {'PASSED' if valid else 'FAILED'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
