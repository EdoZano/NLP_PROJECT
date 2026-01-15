
# Once Upon a Time — NLP Project

Prompt-Based Error Learning for Historically Constrained Narrative Generation.

This bundle contains the full codebase used for the experiments (Method A vs. Method B), the final experimental outputs, and the generated plots.

## Contents

- `CODE/`: source code and scripts
- `CODE/final_results/`: final A/B experiment logs and aggregated results
- `CODE/analysis_graphs/`: final plots (PNG) and `analysis_report.txt`
- `CODE/report_finale.md`: project write-up (paper/report in Markdown)
- `CODE/qualitative_examples.md`: qualitative examples

## Setup

From `NLP_PROJECT/CODE/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

From `NLP_PROJECT/CODE/`:

```powershell
# Generate a single story
python run.py single

# Run A/B comparison (writes JSON logs into an output directory)
python run.py compare --output_dir final_results

# Regenerate plots and analysis report from results
python analyze_metrics.py --input final_results --output analysis_graphs
```

## Deliverables

- Results: `CODE/final_results/comparison_results.json` and `CODE/final_results/comparison_results_full.json`
- Plots/report: `CODE/analysis_graphs/*.png` and `CODE/analysis_graphs/analysis_report.txt`

## Paper

The project report is included as `CODE/report_finale.md`.

