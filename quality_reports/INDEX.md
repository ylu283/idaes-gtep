# Quality Reports Index

Last updated: 2026-04-10

## Latest By Topic

| Topic | Latest Report | Latest Deck | Notes |
|---|---|---|---|
| Prescient vs paper UC comparison | `reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md` | `decks/2026-03-11_Benchmarking_Update_PCM_vs_Paper.pptx` | Core model-assumption divergence audit |
| Curtailment penalty setup/results | `reports/curtailment_penalty_experiment_setup_2026-02-28.md` | (none) | Experiment rationale and run setup |
| Curtailment PPT content review | `reports/2026-03-11_curtailment_ppt_content_review.md` | `decks/2026-03-11_Benchmarking_Update_PCM_vs_Paper.pptx` | Review + applied slide updates for curtailment mechanics/results |
| Model update + curtailment deep dive | `reports/2026-03-11_model_update_curtailment_slide_content_review.md` | `decks/2026-03-11_Model_Update_and_Curtailment_DeepDive.pptx` | Review + slide content for model update deep dive |
| IDAES meeting plan slide | (none) | `decks/2026-03-26_idaes_meeting_plan_slide.pptx` | One-slide timeline for conversion check, PCM run, analysis, and Apr 23 meeting |
| GTEP non-PCM explainer | `reports/2026-03-24_gtep_non_pcm_model_explainer_and_conversion_spec.md` | (none) | Clear-language model walkthrough + expansion-result production path |
| GTEP to Prescient mapping spec | `reports/2026-03-24_gtep_to_prescient_pcm_data_mapping_spec.md` | (none) | Required columns/files and pseudo-code conversion workflow |
| GTEP 2035 conversion domain review | `reports/2026-04-01_gtep_2035_conversion_domain_review.md` | (none) | Critical bug fix audit: cost curve encoding, source file selection |
| 2035 Full-Year PCM Analysis | `reports/2026-04-07_prescient_2035_annual_pcm_analysis.md` | (none) | 365-day Prescient PTDF analysis, NUC/COAL zero-dispatch documented |
| 2035 conversion audit | `reports/2026-04-10_prescient_2035_conversion_audit.md` | (none) | Full audit: data sources, fuel_cost3 tracing, uniform MC, HR_avg_0 fix |
| GTEP model overview | `reports/2026-04-10_gtep_model_overview.md` | (none) | Structure, temporal hierarchy, objective, constraints, data pipeline |
| GTEP variables & parameters | `reports/2026-04-10_gtep_model_variables_parameters.md` | (none) | Complete reference: all sets, params, vars, expressions with line numbers |
| GTEP equations | `reports/2026-04-10_gtep_model_equations.md` | (none) | Mathematical formulation of all active constraints |
| GTEP assumptions & limitations | `reports/2026-04-10_gtep_model_assumptions.md` | (none) | Cost model, temporal, network, data flow assumptions; known TODOs |
| Lab progress notes | `lab_logs/lab_log_2026-04-02.md` | (none) | Fuel price units fix and fact-check |

## Legacy Path Map (Phased, Non-Breaking Migration)

| Old Path | New Canonical Path | Status |
|---|---|---|
| `quality_reports/plans/2026-02-26_IDAES_Update_Kay.pptx` | `quality_reports/decks/2026-02-26_IDAES_Update_Kay.pptx` | moved |
| `quality_reports/plans/2026-03-03_Benchmarking_Update_PCM_vs_Paper.pptx` | `quality_reports/decks/2026-03-03_Benchmarking_Update_PCM_vs_Paper.pptx` | moved |
| `quality_reports/plans/create_presentation.py` | `quality_reports/decks/src/create_presentation.py` | moved |
| `quality_reports/plans/create_benchmark_update_presentation.py` | `quality_reports/decks/src/create_benchmark_update_presentation.py` | moved |
| `quality_reports/plans/build_benchmark_update_slide_data.py` | `quality_reports/decks/src/build_benchmark_update_slide_data.py` | moved |
| `quality_reports/plans/data/benchmark_update_slide_data.json` | `quality_reports/decks/data/benchmark_update_slide_data.json` | moved |
| `quality_reports/session_logs/model_comparison_prescient_vs_paper_uc_2026-02-28.md` | `quality_reports/reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md` | moved |
| `quality_reports/session_logs/curtailment_penalty_experiment_setup_2026-02-28.md` | `quality_reports/reports/curtailment_penalty_experiment_setup_2026-02-28.md` | moved |
| `quality_reports/session_logs/lab_log_2026-03-01.md` | `quality_reports/lab_logs/lab_log_2026-03-01.md` | moved |

## Current Session-Log Scope

Keep only transient logs in:
- `quality_reports/session_logs/2026-03-04_curtailment_notebook_update.md`
- `quality_reports/session_logs/2026-03-05_curtailment_notebook_debug.md`
- `quality_reports/session_logs/2026-03-11_report_accuracy_review.md`
- `quality_reports/session_logs/2026-03-24_gtep_prescient_conversion_worklog.md`
- `quality_reports/session_logs/2026-04-01_gtep_2035_pcm_conversion.md`
- `quality_reports/session_logs/2026-04-02_fuel_price_units_fix.md`
- `quality_reports/session_logs/2026-04-07_prescient_2035_annual_analysis.md`
- `quality_reports/session_logs/2026-04-10_gtep_model_documentation.md`
- `quality_reports/session_logs/2026-04-10_hr_avg0_fix.md`
