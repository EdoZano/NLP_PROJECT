"""
Script to analyze metrics and generate comparative graphs.
Reads results from comparison_results.json and produces visualizations.

Usage:
    python analyze_metrics.py --input comparison_results/comparison_results.json
    python analyze_metrics.py --input comparison_results/ --output graphs/
"""

import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

def load_comparison_data(input_path):
    """Load comparison data."""
    path = Path(input_path)
    
    if path.is_file():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif path.is_dir():
        # Try full file first (has story_state)
        results_file_full = path / "comparison_results_full.json"
        if results_file_full.exists():
            with open(results_file_full, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Otherwise use light version
        results_file = path / "comparison_results.json"
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    raise FileNotFoundError(f"Results file not found in: {input_path}")

def plot_inconsistencies_comparison(data, output_dir):
    """Bar chart: total inconsistencies Method A vs B."""
    stats_a = data["summary"]["method_A_stats"]
    stats_b = data["summary"]["method_B_stats"]
    
    categories = ['Total\nInconsistencies', 'Repeated\nInconsistencies', 'Inconsistency\nRate/Turn']
    method_a_values = [
        stats_a['avg_inconsistencies'],
        stats_a['avg_repeated_inconsistencies'],
        stats_a['avg_inconsistency_rate'] * 10  # Scaled for visibility
    ]
    method_b_values = [
        stats_b['avg_inconsistencies'],
        stats_b['avg_repeated_inconsistencies'],
        stats_b['avg_inconsistency_rate'] * 10
    ]
    
    x = np.arange(len(categories))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, method_a_values, width, label='Method A (with learning)', color='#2ecc71')
    bars2 = ax.bar(x + width/2, method_b_values, width, label='Method B (without learning)', color='#e74c3c')
    
    ax.set_ylabel('Average Value')
    ax.set_title('Inconsistencies Comparison: Method A vs B')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add values above bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}',
                   ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / 'inconsistencies_comparison.png', dpi=300)
    print(f"Saved: inconsistencies_comparison.png")
    plt.close()

def plot_facts_objects_comparison(data, output_dir):
    """Bar chart: facts and objects."""
    stats_a = data["summary"]["method_A_stats"]
    stats_b = data["summary"]["method_B_stats"]
    
    categories = ['Facts', 'Objects']
    method_a_values = [stats_a['avg_facts'], stats_a['avg_objects']]
    method_b_values = [stats_b['avg_facts'], stats_b['avg_objects']]
    
    x = np.arange(len(categories))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(8, 6))
    bars1 = ax.bar(x - width/2, method_a_values, width, label='Method A', color='#3498db')
    bars2 = ax.bar(x + width/2, method_b_values, width, label='Method B', color='#9b59b6')
    
    ax.set_ylabel('Average Count')
    ax.set_title('Facts and Objects Tracking: Method A vs B')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / 'facts_objects_comparison.png', dpi=300)
    print(f"Saved: facts_objects_comparison.png")
    plt.close()

def plot_turn_length_distribution(data, output_dir):
    """Boxplot: turn length distribution."""
    all_lengths_a = []
    all_lengths_b = []
    
    for run in data["method_A"]:
        all_lengths_a.extend(run["turn_lengths"])
    
    for run in data["method_B"]:
        all_lengths_b.extend(run["turn_lengths"])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot([all_lengths_a, all_lengths_b], 
                     tick_labels=['Method A', 'Method B'],
                     patch_artist=True)
    
    colors = ['#2ecc71', '#e74c3c']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    
    ax.set_ylabel('Turn Length (words)')
    ax.set_title('Turn Length Distribution')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / 'turn_length_distribution.png', dpi=300)
    print(f"Saved: turn_length_distribution.png")
    plt.close()

def plot_facts_accumulation(data, output_dir):
    """Line chart: facts accumulation over time for each run."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Method A
    for i, run in enumerate(data["method_A"]):
        # Skip if no story_state (light version)
        if "story_state" not in run:
            continue
        facts_per_turn = {}
        for fact in run["story_state"]["facts"]:
            turn = fact.get("turn_created", 0)
            facts_per_turn[turn] = facts_per_turn.get(turn, 0) + 1
        
        if facts_per_turn:
            turns = sorted(facts_per_turn.keys())
            cumulative = np.cumsum([facts_per_turn[t] for t in turns])
            ax1.plot(turns, cumulative, marker='o', label=f'Run {i+1}', alpha=0.7)
    
    ax1.set_xlabel('Turn')
    ax1.set_ylabel('Accumulated Facts')
    ax1.set_title('Method A: Facts Accumulation')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Method B
    for i, run in enumerate(data["method_B"]):
        # Skip if no story_state (light version)
        if "story_state" not in run:
            continue
        facts_per_turn = {}
        for fact in run["story_state"]["facts"]:
            turn = fact.get("turn_created", 0)
            facts_per_turn[turn] = facts_per_turn.get(turn, 0) + 1
        
        if facts_per_turn:
            turns = sorted(facts_per_turn.keys())
            cumulative = np.cumsum([facts_per_turn[t] for t in turns])
            ax2.plot(turns, cumulative, marker='o', label=f'Run {i+1}', alpha=0.7)
    
    ax2.set_xlabel('Turn')
    ax2.set_ylabel('Accumulated Facts')
    ax2.set_title('Method B: Facts Accumulation')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / 'facts_accumulation.png', dpi=300)
    print(f"Saved: facts_accumulation.png")
    plt.close()

def plot_inconsistencies_by_turn(data, output_dir):
    """Chart: when inconsistencies appear."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Method A
    turns_a = []
    for run in data["method_A"]:
        # Skip if no story_state
        if "story_state" not in run:
            continue
        for inc in run["story_state"]["inconsistencies"]:
            turns_a.append(inc["turn"])
    
    if turns_a:
        ax1.hist(turns_a, bins=range(0, max(turns_a)+2), edgecolor='black', color='#2ecc71', alpha=0.7)
    ax1.set_xlabel('Turn')
    ax1.set_ylabel('Number of Inconsistencies')
    ax1.set_title('Method A: Inconsistencies Distribution by Turn')
    ax1.grid(axis='y', alpha=0.3)
    
    # Method B
    turns_b = []
    for run in data["method_B"]:
        # Skip if no story_state
        if "story_state" not in run:
            continue
        for inc in run["story_state"]["inconsistencies"]:
            turns_b.append(inc["turn"])
    
    if turns_b:
        ax2.hist(turns_b, bins=range(0, max(turns_b)+2), edgecolor='black', color='#e74c3c', alpha=0.7)
    ax2.set_xlabel('Turn')
    ax2.set_ylabel('Number of Inconsistencies')
    ax2.set_title('Method B: Inconsistencies Distribution by Turn')
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / 'inconsistencies_by_turn.png', dpi=300)
    print(f"Saved: inconsistencies_by_turn.png")
    plt.close()

def generate_summary_report(data, output_dir):
    """Generate text summary report."""
    report_path = Path(output_dir) / "analysis_report.txt"
    
    stats_a = data["summary"]["method_A_stats"]
    stats_b = data["summary"]["method_B_stats"]
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("COMPARATIVE ANALYSIS REPORT: METHOD A vs B\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Experiment date: {data['experiment']['date']}\n")
        f.write(f"Runs per method: {data['experiment']['runs_per_method']}\n")
        f.write(f"Turns per story: {data['experiment']['turns_per_story']}\n\n")
        
        f.write("AGGREGATED METRICS\n")
        f.write("-"*70 + "\n\n")
        
        f.write(f"{'Metric':<40} {'Method A':<15} {'Method B':<15}\n")
        f.write("-"*70 + "\n")
        f.write(f"{'Avg facts':<40} {stats_a['avg_facts']:<15} {stats_b['avg_facts']:<15}\n")
        f.write(f"{'Avg objects':<40} {stats_a['avg_objects']:<15} {stats_b['avg_objects']:<15}\n")
        f.write(f"{'Avg inconsistencies':<40} {stats_a['avg_inconsistencies']:<15} {stats_b['avg_inconsistencies']:<15}\n")
        f.write(f"{'Avg repeated inconsistencies':<40} {stats_a['avg_repeated_inconsistencies']:<15} {stats_b['avg_repeated_inconsistencies']:<15}\n")
        f.write(f"{'Inconsistency rate/turn':<40} {stats_a['avg_inconsistency_rate']:<15} {stats_b['avg_inconsistency_rate']:<15}\n")
        f.write(f"{'Avg turn length':<40} {stats_a['avg_turn_length']:<15} {stats_b['avg_turn_length']:<15}\n\n")
        
        # Calculate improvement
        if stats_b['avg_inconsistencies'] > 0:
            improvement_inc = ((stats_b['avg_inconsistencies'] - stats_a['avg_inconsistencies']) / stats_b['avg_inconsistencies'] * 100)
            f.write(f"IMPROVEMENT Method A over B:\n")
            f.write(f"  - Inconsistency reduction: {improvement_inc:.1f}%\n")
        
        if stats_b['avg_repeated_inconsistencies'] > 0:
            improvement_rep = ((stats_b['avg_repeated_inconsistencies'] - stats_a['avg_repeated_inconsistencies']) / stats_b['avg_repeated_inconsistencies'] * 100)
            f.write(f"  - Repeated inconsistency reduction: {improvement_rep:.1f}%\n")
    
    print(f"Saved: analysis_report.txt")

def analyze_and_plot(input_path, output_dir):
    """Main function for complete analysis."""
    print(f"\nMETRICS ANALYSIS")
    print(f"   Input: {input_path}")
    print(f"   Output: {output_dir}\n")
    
    # Load data
    data = load_comparison_data(input_path)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate all charts
    print("Generating charts...")
    plot_inconsistencies_comparison(data, output_path)
    plot_facts_objects_comparison(data, output_path)
    plot_turn_length_distribution(data, output_path)
    plot_facts_accumulation(data, output_path)
    plot_inconsistencies_by_turn(data, output_path)
    
    # Generate text report
    generate_summary_report(data, output_path)
    
    print(f"\nANALYSIS COMPLETE")
    print(f"   Charts saved in: {output_path}")
    print(f"   Text report: {output_path / 'analysis_report.txt'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze metrics and generate charts")
    parser.add_argument("--input", type=str, required=True, help="File or directory with comparison_results.json")
    parser.add_argument("--output", type=str, default="analysis_graphs", help="Output directory for charts")
    
    args = parser.parse_args()
    
    analyze_and_plot(args.input, args.output)
