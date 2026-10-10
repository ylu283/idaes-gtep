"""Pre-aggregate hourly representative-day data to 2-h / 4-h commitment blocks.

``port`` from the fork: ``gtep/driver_coal_2hr.py@commitment_period`` lines
32-89 (``aggregate_hourly_to_blocks``, ``aggregate_data``,
``aggregate_load_scaling``), copied unchanged except for docstrings and
black formatting. Data-side only; no model change.

Upstream 7b84352 has no time-series aggregation: loads and renewable caps are
read as ``values[commitment_period - 1]`` (``model_library/scaling.py:35``,
``model_library/commitment.py:41``), and ``min_up_time`` / ``min_down_time``
are used as counts of commitment periods
(``model_library/representative_period.py:208-283``), so hours must be
converted to block counts.
"""

import math


def aggregate_hourly_to_blocks(values_24, block_hours):
    """Average 24 hourly values into blocks of ``block_hours``."""
    n_blocks = len(values_24) // block_hours
    return [
        sum(values_24[i * block_hours : (i + 1) * block_hours]) / block_hours
        for i in range(n_blocks)
    ]


def aggregate_data(data_object, block_hours, num_commit):
    """Aggregate ``data_object.representative_data`` in place.

    - ``p_load["values"]``: 24 -> num_commit block averages
    - renewable ``p_max["values"]``: 24 -> num_commit block averages
    - ``min_up_time`` / ``min_down_time``: hours -> ceil(hours / block_hours),
      capped at num_commit
    """
    for rep_data in data_object.representative_data:
        elements = rep_data.data["elements"]

        for load_n in elements["load"]:
            load_entry = elements["load"][load_n]
            if (
                isinstance(load_entry["p_load"], dict)
                and "values" in load_entry["p_load"]
            ):
                load_entry["p_load"]["values"] = aggregate_hourly_to_blocks(
                    load_entry["p_load"]["values"], block_hours
                )

        for gen in elements["generator"]:
            g = elements["generator"][gen]
            if isinstance(g.get("p_max"), dict) and "values" in g["p_max"]:
                g["p_max"]["values"] = aggregate_hourly_to_blocks(
                    g["p_max"]["values"], block_hours
                )

        for gen in elements["generator"]:
            g = elements["generator"][gen]
            if "min_up_time" in g:
                g["min_up_time"] = min(
                    math.ceil(g["min_up_time"] / block_hours), num_commit
                )
            if "min_down_time" in g:
                g["min_down_time"] = min(
                    math.ceil(g["min_down_time"] / block_hours), num_commit
                )


def aggregate_load_scaling(data_object, block_hours):
    """Average ``data_object.load_scaling`` rows in groups of ``block_hours``."""
    df = data_object.load_scaling.copy()
    # hour column is 1-based (1-24); map to block index (1-based)
    df["hour"] = ((df["hour"] - 1) // block_hours) + 1
    group_cols = ["year", "month", "day", "hour"]
    scale_cols = [c for c in df.columns if c not in group_cols]
    data_object.load_scaling = df.groupby(group_cols, as_index=False)[scale_cols].mean()
