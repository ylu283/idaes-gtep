"""Update pcm_analysis.ipynb: add benchmark Q1 to all cells + Texas map."""
import json

NB_PATH = "/Users/yilu/Documents/GitHub/idaes-gtep/gtep/pcm_analysis/pcm_analysis.ipynb"

with open(NB_PATH) as f:
    nb = json.load(f)

def src_lines(text):
    """Convert multi-line string to notebook source list with newlines."""
    lines = text.split('\n')
    result = [line + '\n' for line in lines[:-1]]
    if lines[-1]:
        result.append(lines[-1])
    return result

def replace_cell_source(idx, new_source):
    nb['cells'][idx]['source'] = src_lines(new_source)

def insert_cell_after(idx, cell_type, source):
    cell = {
        "cell_type": cell_type,
        "metadata": {},
        "source": src_lines(source),
    }
    if cell_type == "code":
        cell["outputs"] = []
        cell["execution_count"] = None
    nb['cells'].insert(idx + 1, cell)


# ============================================================
# CELL 19: Load benchmark Q1 early + build all_scenarios
# ============================================================
replace_cell_source(19, r"""# Load bus_detail for both 90-day scenarios
bus_dfs = {}
for scenario_name, s in scenarios.items():
    bdf = _prescient_output_to_df(s['bus_detail'])
    print(f"{scenario_name}: {bdf.shape[0]:,} rows, {bdf.shape[1]} columns")
    print(f"  Date range: {bdf['Datetime'].min()} to {bdf['Datetime'].max()}")
    bus_dfs[scenario_name] = bdf

# Load benchmark Q1 data (365-day run, filtered to Jan-Mar)
_bench_available = os.path.exists(results_benchmark)
if _bench_available:
    _bench_bus = _prescient_output_to_df(os.path.join(results_benchmark, 'bus_detail.csv'))
    bus_dfs['Benchmark Q1'] = _bench_bus[_bench_bus['Datetime'].dt.month <= 3].copy()
    del _bench_bus
    print(f"\nBenchmark Q1: {bus_dfs['Benchmark Q1'].shape[0]:,} rows")
    print(f"  Date range: {bus_dfs['Benchmark Q1']['Datetime'].min()} to {bus_dfs['Benchmark Q1']['Datetime'].max()}")
else:
    print("\nBenchmark path not found — benchmark comparisons will be skipped.")

# Master color map for all scenarios
colors_map = {
    'PTDF UC+ED': 'steelblue',
    'Btheta UC-only': 'darkorange',
}
if _bench_available:
    colors_map['Benchmark Q1'] = 'green'

# All scenario names for looping
all_scenario_names = list(scenarios.keys())
if _bench_available:
    all_scenario_names.append('Benchmark Q1')

print(f"\nScenarios for comparison: {all_scenario_names}")""")


# ============================================================
# CELL 21: 9.1 Negative LMP prevalence — 3-way
# ============================================================
replace_cell_source(21, r"""lmp_col_name = 'LMP DA'

for scenario_name in all_scenario_names:
    bus_df = bus_dfs[scenario_name]
    total_hours = len(bus_df)
    neg_hours = (bus_df[lmp_col_name] < 0).sum()
    deep_neg = (bus_df[lmp_col_name] < -100).sum()
    floor_hours = (bus_df[lmp_col_name] == -1000).sum()

    _sys_demand = bus_df['Demand'].sum()
    if _sys_demand > 1.0:
        _sys_wt_lmp = (bus_df['Demand'] * bus_df[lmp_col_name]).sum() / _sys_demand
    else:
        _sys_wt_lmp = bus_df[lmp_col_name].mean()

    print(f"\n=== {scenario_name} ===")
    print(f"Total bus-hours:        {total_hours:>12,}")
    print(f"LMP < 0:                {neg_hours:>12,}  ({100*neg_hours/total_hours:.1f}%)")
    print(f"LMP < -$100:            {deep_neg:>12,}  ({100*deep_neg/total_hours:.1f}%)")
    print(f"LMP = -$1000 (floor):   {floor_hours:>12,}  ({100*floor_hours/total_hours:.1f}%)")
    print(f"Load-weighted mean LMP: ${_sys_wt_lmp:.2f}/MWh")
    print(f"Simple mean LMP:        ${bus_df[lmp_col_name].mean():.2f}/MWh")
    print(f"Median LMP:             ${bus_df[lmp_col_name].median():.2f}/MWh")

# Side-by-side histograms
n_scen = len(all_scenario_names)
fig, axes = plt.subplots(1, n_scen, figsize=(6 * n_scen, 5), sharey=True)
if n_scen == 1:
    axes = [axes]
for ax, scenario_name in zip(axes, all_scenario_names):
    bus_df = bus_dfs[scenario_name]
    c = colors_map[scenario_name]
    ax.hist(bus_df[lmp_col_name], bins=200, edgecolor='none', alpha=0.7, color=c)
    ax.set_yscale('log')
    ax.axvline(0, color='red', linestyle='--', linewidth=1)
    ax.axvline(-1000, color='darkred', linestyle=':', linewidth=1.5)
    ax.set_xlabel('DA LMP ($/MWh)')
    ax.set_ylabel('Bus-hour count (log scale)')
    ax.set_title(f'{scenario_name}')
plt.suptitle('Distribution of Day-Ahead LMPs', fontsize=13)
plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# CELL 23: 9.2 Spatial — 3-way zone bar charts
# ============================================================
replace_cell_source(23, r"""zone_colors = {
    'FWEST': '#d62728', 'NORTH': '#ff7f0e', 'WEST': '#e377c2',
    'NCENT': '#2ca02c', 'EAST': '#1f77b4', 'SCENT': '#9467bd',
    'SOUTH': '#8c564b', 'COAST': '#17becf'
}

bus_lmp_stats_all = {}
for scenario_name in all_scenario_names:
    bus_df = bus_dfs[scenario_name]
    stats = bus_df.groupby('Bus')[lmp_col_name].agg(['mean', 'median', 'min', 'max', 'count'])
    stats['zone'] = stats.index.map(lambda b: bus_name_to_zone.get(b, '?'))
    stats['pct_negative'] = bus_df.groupby('Bus').apply(
        lambda g: (g[lmp_col_name] < 0).mean() * 100
    )
    stats['pct_floor'] = bus_df.groupby('Bus').apply(
        lambda g: (g[lmp_col_name] == -1000).mean() * 100
    )
    bus_lmp_stats_all[scenario_name] = stats

# Zone-level comparison
n_scen = len(all_scenario_names)
fig, axes = plt.subplots(1, n_scen, figsize=(6 * n_scen, 6))
if n_scen == 1:
    axes = [axes]
for ax, scenario_name in zip(axes, all_scenario_names):
    stats = bus_lmp_stats_all[scenario_name]
    zone_stats = stats.groupby('zone').agg(
        mean_lmp=('mean', 'mean'),
        avg_pct_floor=('pct_floor', 'mean'),
    ).sort_values('mean_lmp')
    colors = [zone_colors.get(z, 'gray') for z in zone_stats.index]
    ax.barh(zone_stats.index, zone_stats['mean_lmp'], color=colors)
    ax.axvline(0, color='black', linewidth=0.5)
    ax.set_xlabel('Mean DA LMP ($/MWh)')
    ax.set_title(f'{scenario_name}\nMean DA LMP by Zone')
plt.tight_layout()
plt.show()
plt.close('all')

# Worst 10 buses per scenario
for scenario_name in all_scenario_names:
    stats = bus_lmp_stats_all[scenario_name]
    worst_10 = stats.sort_values('mean').head(10)
    print(f"\n=== {scenario_name}: 10 Worst Buses ===")
    print(worst_10[['zone', 'mean', 'median', 'pct_negative', 'pct_floor']].to_string(
        float_format=lambda x: f'{x:.1f}'
    ))""")


# ============================================================
# CELL 25: 9.3 Temporal — 3-way overlays
# ============================================================
replace_cell_source(25, r"""fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# (a) Load-weighted LMP by hour of day
ax = axes[0, 0]
for scenario_name in all_scenario_names:
    bus_df = bus_dfs[scenario_name].copy()
    bus_df['Hour'] = bus_df['Datetime'].dt.hour
    bus_df['_wt_lmp'] = bus_df['Demand'] * bus_df[lmp_col_name]
    _h = bus_df.groupby('Hour').agg(_wt_sum=('_wt_lmp', 'sum'), _d_sum=('Demand', 'sum'))
    hourly_avg = (_h['_wt_sum'] / _h['_d_sum']).replace([np.inf, -np.inf], 0).fillna(0)
    ax.plot(hourly_avg.index, hourly_avg.values, 'o-', color=colors_map[scenario_name],
            linewidth=2, label=scenario_name, markersize=4)
ax.axhline(0, color='black', linewidth=0.5)
ax.set_xlabel('Hour of Day')
ax.set_ylabel('Load-Weighted DA LMP ($/MWh)')
ax.set_title('System Load-Weighted DA LMP by Hour')
ax.set_xticks(range(0, 24))
ax.legend(fontsize=8)

# (b) Load-weighted LMP by month
ax = axes[0, 1]
bar_w = 0.8 / len(all_scenario_names)
for i, scenario_name in enumerate(all_scenario_names):
    bus_df = bus_dfs[scenario_name].copy()
    bus_df['Month'] = bus_df['Datetime'].dt.month
    bus_df['_wt_lmp'] = bus_df['Demand'] * bus_df[lmp_col_name]
    _m = bus_df.groupby('Month').agg(_wt_sum=('_wt_lmp', 'sum'), _d_sum=('Demand', 'sum'))
    monthly_avg = (_m['_wt_sum'] / _m['_d_sum']).replace([np.inf, -np.inf], 0).fillna(0)
    offset = (i - len(all_scenario_names)/2 + 0.5) * bar_w
    ax.bar(monthly_avg.index + offset, monthly_avg.values, width=bar_w,
           color=colors_map[scenario_name], label=scenario_name, alpha=0.8)
ax.axhline(0, color='black', linewidth=0.5)
ax.set_xlabel('Month')
ax.set_ylabel('Load-Weighted DA LMP ($/MWh)')
ax.set_title('Monthly Load-Weighted DA LMP')
ax.set_xticks([1, 2, 3])
ax.set_xticklabels(['Jan', 'Feb', 'Mar'])
ax.legend(fontsize=8)

# (c) % buses negative by hour — all scenarios
ax = axes[1, 0]
for scenario_name in all_scenario_names:
    bus_df = bus_dfs[scenario_name].copy()
    bus_df['Hour'] = bus_df['Datetime'].dt.hour
    pct_neg = bus_df.groupby('Hour').apply(lambda g: (g[lmp_col_name] < 0).mean() * 100)
    ax.plot(pct_neg.index, pct_neg.values, 'o-', color=colors_map[scenario_name],
            linewidth=2, label=scenario_name, markersize=4)
ax.set_xlabel('Hour of Day')
ax.set_ylabel('% of bus-hours with LMP < 0')
ax.set_title('Negative LMP Frequency by Hour')
ax.set_xticks(range(0, 24))
ax.legend(fontsize=8)

# (d) Heatmap for first scenario (PTDF)
ax = axes[1, 1]
bus_df = bus_dfs['PTDF UC+ED'].copy()
bus_df['Hour'] = bus_df['Datetime'].dt.hour
bus_df['Month'] = bus_df['Datetime'].dt.month
bus_df['_wt_lmp'] = bus_df['Demand'] * bus_df[lmp_col_name]
_mh = bus_df.groupby(['Month', 'Hour']).agg(_wt_sum=('_wt_lmp', 'sum'), _d_sum=('Demand', 'sum'))
_mh_lmp = (_mh['_wt_sum'] / _mh['_d_sum']).replace([np.inf, -np.inf], 0).fillna(0)
pivot = _mh_lmp.unstack()
im = ax.imshow(pivot.values, aspect='auto', cmap='RdYlGn',
               vmin=-200, vmax=100, origin='lower')
ax.set_xlabel('Hour of Day')
ax.set_ylabel('Month')
ax.set_yticks(range(pivot.shape[0]))
ax.set_yticklabels(['Jan', 'Feb', 'Mar'][:pivot.shape[0]])
ax.set_title('PTDF UC+ED: Load-Weighted LMP Heatmap')
plt.colorbar(im, ax=ax, label='$/MWh')

plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# CELL 27: 9.4 Overgeneration — 3-way
# ============================================================
replace_cell_source(27, r"""sys_hourlys = {}
for scenario_name in all_scenario_names:
    if scenario_name in scenarios:
        rp = scenarios[scenario_name]['results_path']
    else:
        rp = results_benchmark

    bus_df = bus_dfs[scenario_name].copy()
    hourly_summary = pd.read_csv(os.path.join(rp, 'hourly_summary.csv'))
    hourly_summary['Datetime'] = (
        pd.to_datetime(hourly_summary['Date'])
        + pd.to_timedelta(hourly_summary['Hour'], 'hour')
    )
    # Filter benchmark to Q1
    if scenario_name == 'Benchmark Q1':
        hourly_summary = hourly_summary[pd.to_datetime(hourly_summary['Date']).dt.month <= 3]

    bus_df['_wt_lmp'] = bus_df['Demand'] * bus_df[lmp_col_name]
    sys_hourly = bus_df.groupby('Datetime').agg(
        sys_demand=('Demand', 'sum'),
        sys_overgen=('Overgeneration', 'sum'),
        _wt_lmp_sum=('_wt_lmp', 'sum'),
    ).reset_index()
    sys_hourly['sys_mean_lmp'] = np.where(
        sys_hourly['sys_demand'] > 1.0,
        sys_hourly['_wt_lmp_sum'] / sys_hourly['sys_demand'],
        0
    )
    sys_hourly.drop(columns='_wt_lmp_sum', inplace=True)

    sys_hourly = sys_hourly.merge(
        hourly_summary[['Datetime', 'RenewablesUsed', 'OverGeneration']],
        on='Datetime', how='left'
    )
    sys_hourlys[scenario_name] = sys_hourly

# Scatter plots: 2 rows x N scenarios
n_scen = len(all_scenario_names)
fig, axes = plt.subplots(2, n_scen, figsize=(6 * n_scen, 10))
if n_scen == 1:
    axes = axes.reshape(2, 1)
for col_idx, scenario_name in enumerate(all_scenario_names):
    sh = sys_hourlys[scenario_name]
    c = colors_map[scenario_name]

    ax = axes[0, col_idx]
    ax.scatter(sh['sys_overgen'], sh['sys_mean_lmp'], s=5, alpha=0.4, color=c)
    ax.set_xlabel('System Overgeneration (MW)')
    ax.set_ylabel('Load-Weighted DA LMP ($/MWh)')
    r = sh[['sys_mean_lmp', 'sys_overgen']].corr().iloc[0, 1]
    ax.set_title(f'{scenario_name}\nLMP vs Overgen (r={r:+.3f})')

    ax = axes[1, col_idx]
    ax.scatter(sh['RenewablesUsed'], sh['sys_mean_lmp'], s=5, alpha=0.4, color=c)
    ax.set_xlabel('Renewables Used (MW)')
    ax.set_ylabel('Load-Weighted DA LMP ($/MWh)')
    r2 = sh[['sys_mean_lmp', 'RenewablesUsed']].dropna().corr().iloc[0, 1]
    ax.set_title(f'{scenario_name}\nLMP vs Renewables (r={r2:+.3f})')

plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# CELL 29: 9.5 Thermal — 3-way
# ============================================================
replace_cell_source(29, r"""# Load thermal dispatch for all scenarios
thermal_dfs = {}
renew_dfs = {}
for scenario_name in all_scenario_names:
    if scenario_name in scenarios:
        tp = scenarios[scenario_name]['thermal_detail']
        rp = scenarios[scenario_name]['renew_detail']
    else:
        tp = os.path.join(results_benchmark, 'thermal_detail.csv')
        rp = os.path.join(results_benchmark, 'renewables_detail.csv')

    tdf = _prescient_output_to_df(tp)
    tdf['Generator'] = tdf['Generator'].astype(str)
    if scenario_name == 'Benchmark Q1':
        tdf = tdf[tdf['Datetime'].dt.month <= 3]
    thermal_dfs[scenario_name] = tdf

    rdf = _prescient_output_to_df(rp)
    rdf['Generator'] = rdf['Generator'].astype(str)
    if scenario_name == 'Benchmark Q1':
        rdf = rdf[rdf['Datetime'].dt.month <= 3]
    renew_dfs[scenario_name] = rdf

# Coal & nuclear fleet
coal_nuc_gens = gen_meta[gen_meta['Fuel'].isin(['C', 'N'])][
    ['GEN UID', 'Bus ID', 'Fuel', 'PMax MW', 'PMin MW',
     'Min Down Time Hr', 'Min Up Time Hr']
].copy()
coal_nuc_gens['PMin_ratio'] = (coal_nuc_gens['PMin MW'] / coal_nuc_gens['PMax MW'] * 100).round(1)

print("=== Coal & Nuclear Fleet ===")
print(coal_nuc_gens.to_string(index=False))
print(f"\nTotal coal+nuc PMax: {coal_nuc_gens['PMax MW'].sum():.0f} MW")
print(f"Total coal+nuc PMin: {coal_nuc_gens['PMin MW'].sum():.0f} MW")

coal_nuc_ids = set(coal_nuc_gens['GEN UID'].astype(str))
for scenario_name in all_scenario_names:
    neg_lmp_hours = set(
        sys_hourlys[scenario_name][sys_hourlys[scenario_name]['sys_mean_lmp'] < 0]['Datetime']
    )
    thermal_cn = thermal_dfs[scenario_name][
        thermal_dfs[scenario_name]['Generator'].isin(coal_nuc_ids)
    ].copy()
    thermal_cn['is_neg_lmp'] = thermal_cn['Datetime'].isin(neg_lmp_hours)
    thermal_cn['is_committed'] = thermal_cn['Dispatch'] > 0

    neg_dispatch = thermal_cn[thermal_cn['is_neg_lmp']].groupby('Generator').agg(
        mean_dispatch=('Dispatch', 'mean'),
        pct_committed=('is_committed', 'mean'),
    ).reset_index()
    neg_dispatch['pct_committed'] *= 100

    print(f"\n=== {scenario_name}: Coal/Nuclear During Negative LMP Hours ({len(neg_lmp_hours)} hours) ===")
    print(f"  Mean committed dispatch: {neg_dispatch['mean_dispatch'].mean():.1f} MW per unit")""")


# ============================================================
# CELL 31: 9.6 Curtailment — 3-way
# ============================================================
replace_cell_source(31, r"""print("=== Simulation-Wide Summary ===\n")
for scenario_name in all_scenario_names:
    if scenario_name in scenarios:
        rp = scenarios[scenario_name]['results_path']
    else:
        rp = results_benchmark
    sim_output = pd.read_csv(os.path.join(rp, 'overall_simulation_output.csv'))
    label = scenario_name
    if scenario_name == 'Benchmark Q1':
        label += ' (365d total, not Q1-filtered)'
    print(f"{label}:")
    print(f"  Total renewables curtailment: {sim_output['Total renewables curtailment'].iloc[0]:,.0f} MWh")
    print(f"  Total over generation:        {sim_output['Total over generation'].iloc[0]:,.1f} MWh")
    print(f"  Total demand:                 {sim_output['Total demand'].iloc[0]:,.0f} MWh")
    print(f"  Renewables penetration:       {sim_output['Overall renewables penetration rate'].iloc[0]*100:.1f}%")
    print()""")


# ============================================================
# CELL 33: 9.7 Congestion — 3-way
# ============================================================
replace_cell_source(33, r"""congestion_freqs = {}
for scenario_name in all_scenario_names:
    if scenario_name in scenarios:
        rp = scenarios[scenario_name]['results_path']
    else:
        rp = results_benchmark

    line_df = _prescient_output_to_df(os.path.join(rp, 'line_detail.csv'))
    line_df['Line'] = line_df['Line'].astype(int)
    if scenario_name == 'Benchmark Q1':
        line_df = line_df[line_df['Datetime'].dt.month <= 3]

    line_rated = line_df.merge(
        branch_df[['UID', 'From Bus', 'To Bus', 'Cont Rating']],
        left_on='Line', right_on='UID', how='left'
    )
    line_rated = line_rated[line_rated['Cont Rating'] > 0].copy()
    line_rated['utilization'] = line_rated['Flow'].abs() / line_rated['Cont Rating']
    line_rated['at_capacity'] = line_rated['utilization'] >= 0.95

    congestion_freq = line_rated.groupby('Line').agg(
        pct_at_capacity=('at_capacity', 'mean'),
        from_bus=('From Bus', 'first'),
        to_bus=('To Bus', 'first'),
        rating=('Cont Rating', 'first'),
    ).reset_index()
    congestion_freq['pct_at_capacity'] *= 100
    congestion_freq['from_name'] = congestion_freq['from_bus'].map(bus_id_to_name)
    congestion_freq['to_name'] = congestion_freq['to_bus'].map(bus_id_to_name)
    congestion_freq['from_zone'] = congestion_freq['from_bus'].map(bus_id_to_zone)
    congestion_freq['to_zone'] = congestion_freq['to_bus'].map(bus_id_to_zone)
    congestion_freqs[scenario_name] = congestion_freq

    n_congested = (congestion_freq['pct_at_capacity'] > 10).sum()
    top5 = congestion_freq.sort_values('pct_at_capacity', ascending=False).head(5)
    print(f"\n=== {scenario_name}: {n_congested} lines at >=95% capacity >10% of hours ===")
    print(top5[['Line', 'from_name', 'from_zone', 'to_name', 'to_zone',
                 'rating', 'pct_at_capacity']].to_string(index=False, float_format=lambda x: f'{x:.1f}'))

# Side-by-side congestion histograms
n_scen = len(all_scenario_names)
fig, axes = plt.subplots(1, n_scen, figsize=(6 * n_scen, 5), sharey=True)
if n_scen == 1:
    axes = [axes]
for ax, scenario_name in zip(axes, all_scenario_names):
    cf = congestion_freqs[scenario_name]
    c = colors_map[scenario_name]
    ax.hist(cf['pct_at_capacity'], bins=50, color=c, edgecolor='none', alpha=0.8)
    ax.set_xlabel('% of Hours at >= 95% Capacity')
    ax.set_ylabel('Number of Lines')
    ax.set_title(f'{scenario_name}')
plt.suptitle('Transmission Line Congestion Frequency', fontsize=13)
plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# INSERT NEW CELLS: Texas Map (after cell 33, now index 33)
# ============================================================
# Insert markdown cell
insert_cell_after(33, "markdown", """### 9.7b Geographic Map: Bus Locations, Zones, and Worst LMP Buses

Texas map showing all 123 buses colored by ERCOT zone, transmission lines, and the 5 worst-LMP buses highlighted. Congested lines (>50% of hours at capacity) shown in red.""")

# Insert code cell for map (after the markdown we just inserted at 34)
insert_cell_after(34, "code", r"""from matplotlib.collections import LineCollection

# Build bus coordinate lookup
bus_coords = {}
for _, row in bus_meta.iterrows():
    bus_coords[row['Bus ID']] = (row['Bus Long'], row['Bus Lat'])

# Build line segments from branch data
line_segments = []
line_ids = []
for _, row in branch_df.iterrows():
    fid, tid = int(row['From Bus']), int(row['To Bus'])
    if fid in bus_coords and tid in bus_coords:
        line_segments.append([bus_coords[fid], bus_coords[tid]])
        line_ids.append(int(row['UID']))

# Zone centroids for labels
zone_centroids = {}
for _, row in bus_meta.iterrows():
    z = row['Zone']
    if z not in zone_centroids:
        zone_centroids[z] = {'lons': [], 'lats': []}
    zone_centroids[z]['lons'].append(row['Bus Long'])
    zone_centroids[z]['lats'].append(row['Bus Lat'])
for z in zone_centroids:
    zone_centroids[z] = (
        np.mean(zone_centroids[z]['lons']),
        np.mean(zone_centroids[z]['lats'])
    )

n_scen = len(all_scenario_names)
fig, axes = plt.subplots(1, n_scen, figsize=(7 * n_scen, 8))
if n_scen == 1:
    axes = [axes]

for ax, scenario_name in zip(axes, all_scenario_names):
    stats = bus_lmp_stats_all[scenario_name]
    cf = congestion_freqs[scenario_name]

    # Build congestion lookup by line UID
    cong_lookup = dict(zip(cf['Line'], cf['pct_at_capacity']))

    # Draw all transmission lines — gray for normal, red for congested
    normal_segs, congested_segs, congested_widths = [], [], []
    for seg, lid in zip(line_segments, line_ids):
        pct = cong_lookup.get(lid, 0)
        if pct > 50:
            congested_segs.append(seg)
            congested_widths.append(1 + pct / 20)
        else:
            normal_segs.append(seg)

    if normal_segs:
        lc_normal = LineCollection(normal_segs, colors='lightgray', linewidths=0.5, zorder=1)
        ax.add_collection(lc_normal)
    if congested_segs:
        lc_cong = LineCollection(congested_segs, colors='red', linewidths=congested_widths,
                                  alpha=0.6, zorder=2)
        ax.add_collection(lc_cong)

    # Plot all buses colored by zone
    for _, row in bus_meta.iterrows():
        bname_matches = [bdn for bdn in stats.index if row['Bus Name'] in bdn]
        z = row['Zone']
        c = zone_colors.get(z, 'gray')
        ax.scatter(row['Bus Long'], row['Bus Lat'], c=c, s=25, zorder=3,
                   edgecolors='white', linewidths=0.3)

    # Highlight 5 worst buses
    worst_5 = stats.sort_values('mean').head(5)
    for bus_name in worst_5.index:
        bid = bus_name_to_id.get(bus_name)
        if bid and bid in bus_coords:
            lon, lat = bus_coords[bid]
            ax.scatter(lon, lat, marker='*', s=250, c='red', edgecolors='black',
                       linewidths=1, zorder=5)
            ax.annotate(bus_name.replace(' 345', ''),
                        (lon, lat), fontsize=6, fontweight='bold',
                        xytext=(5, 5), textcoords='offset points',
                        color='darkred', zorder=6)

    # Zone labels
    for z, (cx, cy) in zone_centroids.items():
        ax.text(cx, cy, z, fontsize=9, fontweight='bold', color='gray',
                ha='center', va='center', alpha=0.7, zorder=4,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.5))

    ax.set_xlim(-107, -93)
    ax.set_ylim(25.5, 37)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(f'{scenario_name}\n(red lines = >50% hours congested, stars = 5 worst LMP buses)')
    ax.set_aspect('equal')

# Legend
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
legend_elements = [Patch(facecolor=zone_colors[z], label=z) for z in sorted(zone_colors)]
legend_elements.append(Line2D([0], [0], color='red', linewidth=2, label='Congested line'))
legend_elements.append(Line2D([0], [0], marker='*', color='red', markersize=12,
                               linestyle='', label='5 worst LMP buses'))
axes[-1].legend(handles=legend_elements, loc='lower right', fontsize=7, ncol=2)

plt.suptitle('TX-123BT System: Bus Locations, Zones, and Congestion', fontsize=14)
plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# CELL 37 (was 35 before inserts, now 37): 9.8 Worst bus — 3-way
# Note: 2 cells inserted above, so indices shift by +2
# ============================================================
# Adjust index: original cell 35 is now at 37
replace_cell_source(37, r"""for scenario_name in all_scenario_names:
    stats = bus_lmp_stats_all[scenario_name]
    worst_bus = stats['mean'].idxmin()
    zone = bus_name_to_zone.get(worst_bus, '?')
    bus_id = bus_name_to_id.get(worst_bus)

    print(f"\n=== {scenario_name}: Worst Bus ===")
    print(f"  {worst_bus} (Bus {bus_id}, Zone: {zone})")
    print(f"  Mean DA LMP: ${stats.loc[worst_bus, 'mean']:.1f}/MWh")
    print(f"  % hours LMP < 0: {stats.loc[worst_bus, 'pct_negative']:.1f}%")
    print(f"  % hours at floor: {stats.loc[worst_bus, 'pct_floor']:.1f}%")

    local_gens = gen_meta[gen_meta['Bus ID'] == bus_id]
    print(f"  Connected generators: {len(local_gens)}")
    if len(local_gens) > 0:
        print(local_gens[['GEN UID', 'Fuel', 'PMax MW']].to_string(index=False))

# Worst bus deep dive — overlay all scenarios
stats_ptdf = bus_lmp_stats_all['PTDF UC+ED']
worst_bus_name = stats_ptdf['mean'].idxmin()

# 2-week window around worst period in PTDF
bus_data_ptdf = bus_dfs['PTDF UC+ED'][bus_dfs['PTDF UC+ED']['Bus'] == worst_bus_name].set_index('Datetime').sort_index()
worst_day = bus_data_ptdf[lmp_col_name].rolling(24, min_periods=1).mean().idxmin()
window_start = max(worst_day - pd.Timedelta(days=7), bus_data_ptdf.index.min())
window_end = min(worst_day + pd.Timedelta(days=7), bus_data_ptdf.index.max())

fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)

ax = axes[0]
for scenario_name in all_scenario_names:
    bus_data = bus_dfs[scenario_name][bus_dfs[scenario_name]['Bus'] == worst_bus_name].set_index('Datetime').sort_index()
    c = colors_map[scenario_name]
    ax.plot(bus_data.loc[window_start:window_end, lmp_col_name],
            color=c, linewidth=0.8, label=scenario_name, alpha=0.8)
ax.axhline(0, color='red', linewidth=0.5, linestyle='--')
ax.axhline(-1000, color='darkred', linewidth=0.5, linestyle=':')
ax.set_ylabel('DA LMP ($/MWh)')
ax.set_title(f'Worst Bus: {worst_bus_name} — 2-Week Window')
ax.legend(fontsize=8)

ax = axes[1]
for scenario_name in all_scenario_names:
    bus_data = bus_dfs[scenario_name][bus_dfs[scenario_name]['Bus'] == worst_bus_name].set_index('Datetime').sort_index()
    c = colors_map[scenario_name]
    ax.plot(bus_data.loc[window_start:window_end, 'Demand'],
            color=c, linewidth=0.8, label=scenario_name, alpha=0.8)
ax.set_ylabel('Local Demand (MW)')
ax.set_xlabel('Date')
ax.legend(fontsize=8)

plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# CELL 39 (was 37, now 39): 9.9 Worst vs best — 3-way
# ============================================================
replace_cell_source(39, r"""for scenario_name in all_scenario_names:
    stats = bus_lmp_stats_all[scenario_name]
    worst = stats['mean'].idxmin()
    best = stats['mean'].idxmax()

    print(f"\n=== {scenario_name} ===")
    comparison = pd.DataFrame({
        'Metric': ['Zone', 'Mean DA LMP', '% LMP < 0', '% at floor'],
        worst: [
            bus_name_to_zone.get(worst, '?'),
            f"${stats.loc[worst, 'mean']:.1f}",
            f"{stats.loc[worst, 'pct_negative']:.1f}%",
            f"{stats.loc[worst, 'pct_floor']:.1f}%",
        ],
        best: [
            bus_name_to_zone.get(best, '?'),
            f"${stats.loc[best, 'mean']:.1f}",
            f"{stats.loc[best, 'pct_negative']:.1f}%",
            f"{stats.loc[best, 'pct_floor']:.1f}%",
        ],
    })
    print(comparison.to_string(index=False))

# Rolling LMP for worst bus — all scenarios
worst_bus = bus_lmp_stats_all['PTDF UC+ED']['mean'].idxmin()
fig, ax = plt.subplots(figsize=(16, 5))
for scenario_name in all_scenario_names:
    bus_df = bus_dfs[scenario_name]
    c = colors_map[scenario_name]
    ts = bus_df[bus_df['Bus'] == worst_bus].set_index('Datetime')[lmp_col_name].sort_index()
    ax.plot(ts.index, ts.rolling(24).mean(),
            color=c, alpha=0.7, linewidth=0.8, label=f'{scenario_name}')
ax.axhline(0, color='black', linewidth=0.5)
ax.set_ylabel('DA LMP ($/MWh, 24h rolling avg)')
ax.set_title(f'Worst Bus ({worst_bus}): 24h Rolling LMP — All Scenarios')
ax.legend(fontsize=8)
plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# CELL 45 (was 43, now 45): 10.2 Cost — add benchmark
# ============================================================
replace_cell_source(45, r"""# Load sim outputs for all scenarios
sim_outputs = {}
for scenario_name in all_scenario_names:
    if scenario_name in scenarios:
        rp = scenarios[scenario_name]['results_path']
    else:
        rp = results_benchmark
    sim_outputs[scenario_name] = pd.read_csv(os.path.join(rp, 'overall_simulation_output.csv'))

fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# (a) Stacked bar: fixed vs variable costs
ax = axes[0]
labels = all_scenario_names
x = range(len(labels))
fixed = []
variable = []
for sn in labels:
    so = sim_outputs[sn]
    scale = 90 / 365 if sn == 'Benchmark Q1' else 1.0  # pro-rata benchmark
    fixed.append(so['Total fixed costs'].iloc[0] / 1e9 * scale)
    variable.append(so['Total generation costs'].iloc[0] / 1e9 * scale)
bar_colors = [colors_map[sn] for sn in labels]
ax.bar(x, fixed, label='Fixed Costs', color=bar_colors, alpha=0.6, edgecolor='black', linewidth=0.5)
ax.bar(x, variable, bottom=fixed, label='Variable Costs', color=bar_colors, alpha=0.9, edgecolor='black', linewidth=0.5)
ax.set_ylabel('Cost ($B, 90-day equivalent)')
ax.set_title('Cost Decomposition')
ax.set_xticks(x)
ax.set_xticklabels([s.replace(' ', '\n') for s in labels], fontsize=8)
ax.legend()

# (b) Reliability metrics
ax = axes[1]
bar_w = 0.35
load_shed = []
overgen = []
for sn in labels:
    so = sim_outputs[sn]
    scale = 90 / 365 if sn == 'Benchmark Q1' else 1.0
    load_shed.append(so['Total load shedding'].iloc[0] * scale)
    overgen.append(so['Total over generation'].iloc[0] / 1e3 * scale)
ax.bar([v - bar_w/2 for v in x], load_shed, bar_w, label='Load Shedding (MWh)', color='red', alpha=0.7)
ax2 = ax.twinx()
ax2.bar([v + bar_w/2 for v in x], overgen, bar_w, label='Overgeneration (GWh)', color='purple', alpha=0.7)
ax.set_ylabel('Load Shedding (MWh)')
ax2.set_ylabel('Overgeneration (GWh)')
ax.set_title('Reliability Metrics (90-day equivalent)')
ax.set_xticks(x)
ax.set_xticklabels([s.replace(' ', '\n') for s in labels], fontsize=8)
ax.legend(loc='upper left')
ax2.legend(loc='upper right')

plt.tight_layout()
plt.show()
plt.close('all')

# Print key differences
for sn in labels:
    so = sim_outputs[sn]
    scale = 90 / 365 if sn == 'Benchmark Q1' else 1.0
    print(f"\n{sn}:")
    print(f"  Total costs (90d eq): ${so['Total costs'].iloc[0] * scale / 1e9:.3f}B")
    print(f"  Avg price: ${so['Cumulative average price'].iloc[0]:.2f}/MWh")
    print(f"  On/offs (90d eq): {so['Total on/offs'].iloc[0] * scale:,.0f}")""")


# ============================================================
# CELL 47 (was 45, now 47): 10.3 LMP CDF — add benchmark
# ============================================================
replace_cell_source(47, r"""fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# (a) CDF comparison — all scenarios
ax = axes[0]
for scenario_name in all_scenario_names:
    bus_df = bus_dfs[scenario_name]
    c = colors_map[scenario_name]
    all_lmps = bus_df[lmp_col_name].dropna().sort_values()
    cdf = np.arange(1, len(all_lmps) + 1) / len(all_lmps)
    ax.plot(all_lmps, cdf, color=c, linewidth=1, label=scenario_name, alpha=0.8)
ax.axvline(0, color='black', linestyle='--', linewidth=0.5)
ax.set_xlabel('DA LMP ($/MWh)')
ax.set_ylabel('Cumulative Probability')
ax.set_title('CDF of Bus-Hour DA LMPs')
ax.legend(fontsize=8)
ax.set_xlim(-1100, 500)

# (b) Box plots
ax = axes[1]
data_for_box = []
labels_box = []
box_colors = []
for scenario_name in all_scenario_names:
    bus_df = bus_dfs[scenario_name]
    clipped = bus_df[lmp_col_name].clip(-200, 200)
    data_for_box.append(clipped.values)
    labels_box.append(scenario_name.replace(' ', '\n'))
    box_colors.append(colors_map[scenario_name])

bp = ax.boxplot(data_for_box, labels=labels_box, patch_artist=True,
                whis=[5, 95], showfliers=False)
for patch, c in zip(bp['boxes'], box_colors):
    patch.set_facecolor(c)
    patch.set_alpha(0.6)
ax.set_ylabel('DA LMP ($/MWh)')
ax.set_title('LMP Distribution (5th-95th percentile)')
ax.axhline(0, color='red', linestyle='--', linewidth=0.5)

plt.tight_layout()
plt.show()
plt.close('all')""")


# ============================================================
# CELL 53 (was 51, now 53): Simplify Section 10.6
# ============================================================
replace_cell_source(53, r"""# Benchmark Q1 was already loaded in cell 19 — use it directly
# Daily demand-weighted LMP comparison (all 3 scenarios)
print("=== Q1 Load-Weighted System LMP ===")
for scenario_name in all_scenario_names:
    sh = sys_hourlys[scenario_name]
    total_d = sh['sys_demand'].sum()
    if total_d > 0:
        wt_lmp = (sh['sys_mean_lmp'] * sh['sys_demand']).sum() / total_d
    else:
        wt_lmp = 0
    print(f"  {scenario_name}: ${wt_lmp:.2f}/MWh")

fig, ax = plt.subplots(figsize=(16, 5))
for scenario_name in all_scenario_names:
    sh = sys_hourlys[scenario_name].copy().sort_values('Datetime')
    sh['_date'] = sh['Datetime'].dt.date
    sh['_wt'] = sh['sys_mean_lmp'] * sh['sys_demand']
    daily = sh.groupby('_date').agg(_wt_sum=('_wt', 'sum'), _d_sum=('sys_demand', 'sum'))
    daily_lmp = daily['_wt_sum'] / daily['_d_sum']
    c = colors_map[scenario_name]
    ax.plot(range(len(daily_lmp)), daily_lmp.values, color=c, linewidth=1.5,
            label=scenario_name, alpha=0.8,
            linestyle='--' if 'Benchmark' in scenario_name else '-')

ax.axhline(0, color='black', linewidth=0.3)
ax.set_xlabel('Day of Q1')
ax.set_ylabel('Daily Load-Weighted System LMP ($/MWh)')
ax.set_title('Q1 Daily System LMP: 3-Way Comparison')
ax.legend(fontsize=9)
plt.tight_layout()
plt.show()
plt.close('all')

# Negative LMP comparison
print("\n=== Q1 Negative LMP Prevalence ===")
for scenario_name in all_scenario_names:
    bdf = bus_dfs[scenario_name]
    neg_pct = (bdf[lmp_col_name] < 0).mean() * 100
    print(f"  {scenario_name}: {neg_pct:.1f}% bus-hours negative")

# Overgeneration comparison
print("\n=== Q1 Total Overgeneration ===")
for scenario_name in all_scenario_names:
    sh = sys_hourlys[scenario_name]
    print(f"  {scenario_name}: {sh['sys_overgen'].sum():,.0f} MWh")""")


# ============================================================
# Save
# ============================================================
with open(NB_PATH, 'w') as f:
    json.dump(nb, f, indent=1)

print(f"Updated {NB_PATH}")
print(f"Total cells: {len(nb['cells'])}")
print(f"  Markdown: {sum(1 for c in nb['cells'] if c['cell_type'] == 'markdown')}")
print(f"  Code: {sum(1 for c in nb['cells'] if c['cell_type'] == 'code')}")
