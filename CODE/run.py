"""Unified script for story generation and method comparison.

Usage:
    # Generate a single story
    python run.py single                           # Method A, 10 turns
    python run.py single --method B                # Method B, 10 turns
    python run.py single --method A --turns 5      # Method A, 5 turns
    python run.py single --interactive             # Interactive mode

    # Compare Method A vs B (experiments)
    python run.py compare                          # 3 runs, 10 turns
    python run.py compare --runs 10 --turns 10     # 10 runs, 10 turns
    python run.py compare --output results/        # Save to custom folder

    # Analyze results
    python run.py analyze --input final_results/   # Generate charts
"""

import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime

from classes import build_characters_from_config, run_story_session
from persona_utils import load_story_config


# =============================================================================
# FUNCTIONS FOR SINGLE STORY
# =============================================================================

def run_single_story_mode(method, turns, interactive):
    """Runs a single story and saves the results."""
    
    print("=" * 70)
    print(f"THE PATH OF FIVE ELEMENTS - Method {method}")
    if interactive:
        print("INTERACTIVE MODE - You will guide the adventure each turn")
    print("=" * 70)
    
    # Load configuration
    config = load_story_config()
    characters_for_story = build_characters_from_config(config["characters"])
    world_config = config["world"]
    initial_facts = [
        {
            "id": 1,
            "description": config["plot"]["inciting_incident"],
            "turn_created": 0,
        }
    ]
    
    print(f"\nGenerating story with {len(characters_for_story)} protagonists, {turns} turns, Method {method}...")
    print("=" * 70 + "\n")
    
    # Run story
    start_time = time.time()
    final_state, full_story = run_story_session(
        strategy=method,
        max_turns=turns,
        characters=characters_for_story,
        interactive=interactive,
        world_config=world_config,
        initial_facts=initial_facts,
        plot_config=config.get("plot", {}),
    )
    elapsed_time = time.time() - start_time
    
    # Save results
    base_dir = os.path.dirname(os.path.dirname(__file__))  # .../PROGETTO/Story
    state_path = os.path.join(base_dir, "story_state.json")
    story_path = os.path.join(base_dir, "story_text.txt")
    metrics_path = os.path.join(base_dir, "story_metrics.json")
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(final_state, f, ensure_ascii=False, indent=2)
    
    with open(story_path, "w", encoding="utf-8") as f:
        f.write(full_story)
    
    # Calculate metrics
    num_facts = len(final_state.get("facts", []))
    num_items = len(final_state.get("items", []))
    num_inconsistencies = len(final_state.get("inconsistencies", []))
    
    inc_by_type = {}
    for inc in final_state.get("inconsistencies", []):
        inc_type = inc.get("type", "altro")
        inc_by_type[inc_type] = inc_by_type.get(inc_type, 0) + 1
    
    metrics = {
        "total_turns": turns,
        "total_facts": num_facts,
        "total_items": num_items,
        "total_inconsistencies": num_inconsistencies,
        "inconsistencies_by_type": inc_by_type,
        "facts_per_turn": round(num_facts / turns, 2) if turns > 0 else 0,
        "inconsistencies_per_turn": round(num_inconsistencies / turns, 2) if turns > 0 else 0,
        "execution_time_seconds": round(elapsed_time, 2),
        "strategy": method
    }
    
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    
    # Final output
    print("\n" + "=" * 70)
    print(f"Story saved in: {story_path}")
    print(f"State saved in: {state_path}")
    print(f"Metrics saved in: {metrics_path}")
    
    print(f"\nMETRICS:")
    print(f"  - Facts: {num_facts} ({metrics['facts_per_turn']}/turn)")
    print(f"  - Objects: {num_items}")
    print(f"  - Inconsistencies: {num_inconsistencies} ({metrics['inconsistencies_per_turn']}/turn)")
    print(f"  - Time: {round(elapsed_time/60, 1)} minutes")
    
    if inc_by_type:
        for inc_type, count in inc_by_type.items():
            print(f"    - {inc_type}: {count}")
    
    if num_inconsistencies > 0:
        print("\nInconsistencies detected:")
        for inco in final_state["inconsistencies"]:
            inc_type = inco.get('type', 'unknown')
            print(f"  - Turn {inco['turn']} ({inc_type}): {inco['description'][:80]}...")
    
    print("=" * 70)
    return final_state, full_story


# =============================================================================
# FUNCTIONS FOR COMPARISON
# =============================================================================

def run_single_experiment(strategy, turns, run_id):
    """Runs a single story for the experiment and returns metrics."""
    print(f"\n{'='*70}")
    print(f"RUN #{run_id} - Method {strategy} - {turns} turns")
    print(f"{'='*70}")
    
    config = load_story_config()
    characters = config["characters"]
    world_config = config["world"]
    plot_config = config.get("plot")
    
    initial_facts = [
        {
            "id": 1,
            "description": plot_config["inciting_incident"],
            "turn_created": 0,
        }
    ]
    
    prepared_chars = build_characters_from_config(characters)
    
    start_time = time.time()
    story_state, full_story = run_story_session(
        strategy=strategy,
        max_turns=turns,
        characters=prepared_chars,
        interactive=False,
        world_config=world_config,
        initial_facts=initial_facts,
        plot_config=plot_config,
    )
    elapsed_time = time.time() - start_time
    
    # Calculate metrics
    total_facts = len(story_state["facts"])
    total_objects = len(story_state["items"])
    total_inconsistencies = len(story_state.get("inconsistencies", []))
    
    inc_by_type = {}
    repeated_inconsistencies = 0
    seen_violations = set()
    
    for inc in story_state.get("inconsistencies", []):
        inc_type = inc.get("type", "altro")
        inc_by_type[inc_type] = inc_by_type.get(inc_type, 0) + 1
        
        desc_lower = inc.get("description", "").lower()
        for keyword in ["cannocchial", "telescop", "pistol", "orologio"]:
            if keyword in desc_lower:
                if keyword in seen_violations:
                    repeated_inconsistencies += 1
                seen_violations.add(keyword)
    
    turn_lengths = []
    for entry in story_state["history"]:
        turn_lengths.append(len(entry["assistant"].split()))
    
    avg_turn_length = sum(turn_lengths) / len(turn_lengths) if turn_lengths else 0
    
    metrics = {
        "run_id": run_id,
        "strategy": strategy,
        "turns": turns,
        "timestamp": datetime.now().isoformat(),
        "execution_time_seconds": round(elapsed_time, 2),
        "total_facts": total_facts,
        "facts_per_turn": round(total_facts / turns, 2),
        "total_objects": total_objects,
        "total_inconsistencies": total_inconsistencies,
        "inconsistency_rate": round(total_inconsistencies / turns, 2),
        "repeated_inconsistencies": repeated_inconsistencies,
        "inconsistencies_by_type": inc_by_type,
        "avg_turn_length_words": round(avg_turn_length, 2),
        "turn_lengths": turn_lengths,
        "story_text": full_story,
        "story_state": {
            "facts": story_state["facts"],
            "items": story_state["items"],
            "inconsistencies": story_state.get("inconsistencies", []),
        }
    }
    
    print(f"\nMETRICS RUN #{run_id}:")
    print(f"  - Facts: {total_facts} ({metrics['facts_per_turn']}/turn)")
    print(f"  - Objects: {total_objects}")
    print(f"  - Inconsistencies: {total_inconsistencies} ({metrics['inconsistency_rate']}/turn)")
    print(f"  - Repeated inconsistencies: {repeated_inconsistencies}")
    print(f"  - Avg turn length: {round(avg_turn_length)} words")
    print(f"  - Execution time: {round(elapsed_time/60, 1)} minutes")
    
    return metrics


def compare_methods_mode(runs_per_method, turns, output_dir):
    """Runs full comparison between Method A and B."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {
        "experiment": {
            "date": datetime.now().isoformat(),
            "runs_per_method": runs_per_method,
            "turns_per_story": turns,
        },
        "method_A": [],
        "method_B": [],
    }
    
    # Method A
    print(f"\n{'#'*70}")
    print(f"# STARTING TEST METHOD A (with learning)")
    print(f"{'#'*70}")
    
    for i in range(runs_per_method):
        metrics = run_single_experiment("A", turns, i+1)
        results["method_A"].append(metrics)
        
        with open(output_path / f"method_A_run_{i+1}.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    # Method B
    print(f"\n{'#'*70}")
    print(f"# STARTING TEST METHOD B (without learning)")
    print(f"{'#'*70}")
    
    for i in range(runs_per_method):
        metrics = run_single_experiment("B", turns, i+1)
        results["method_B"].append(metrics)
        
        with open(output_path / f"method_B_run_{i+1}.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    # Aggregated statistics
    def calc_stats(method_data):
        return {
            "avg_facts": round(sum(m["total_facts"] for m in method_data) / len(method_data), 2),
            "avg_objects": round(sum(m["total_objects"] for m in method_data) / len(method_data), 2),
            "avg_inconsistencies": round(sum(m["total_inconsistencies"] for m in method_data) / len(method_data), 2),
            "avg_repeated_inconsistencies": round(sum(m["repeated_inconsistencies"] for m in method_data) / len(method_data), 2),
            "avg_inconsistency_rate": round(sum(m["inconsistency_rate"] for m in method_data) / len(method_data), 3),
            "avg_turn_length": round(sum(m["avg_turn_length_words"] for m in method_data) / len(method_data), 2),
        }
    
    results["summary"] = {
        "method_A_stats": calc_stats(results["method_A"]),
        "method_B_stats": calc_stats(results["method_B"]),
    }
    
    # Save results
    with open(output_path / "comparison_results_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    results_light = {
        "experiment": results["experiment"],
        "method_A": [{k: v for k, v in run.items() if k not in ["story_text", "story_state"]} 
                     for run in results["method_A"]],
        "method_B": [{k: v for k, v in run.items() if k not in ["story_text", "story_state"]} 
                     for run in results["method_B"]],
        "summary": results["summary"]
    }
    with open(output_path / "comparison_results.json", "w", encoding="utf-8") as f:
        json.dump(results_light, f, indent=2, ensure_ascii=False)
    
    # Print results
    print(f"\n{'='*70}")
    print("COMPARATIVE RESULTS")
    print(f"{'='*70}")
    print(f"\n{'Metric':<35} {'Method A':<15} {'Method B':<15}")
    print("-" * 70)
    
    stats_a = results["summary"]["method_A_stats"]
    stats_b = results["summary"]["method_B_stats"]
    
    print(f"{'Avg facts':<35} {stats_a['avg_facts']:<15} {stats_b['avg_facts']:<15}")
    print(f"{'Avg objects':<35} {stats_a['avg_objects']:<15} {stats_b['avg_objects']:<15}")
    print(f"{'Avg inconsistencies':<35} {stats_a['avg_inconsistencies']:<15} {stats_b['avg_inconsistencies']:<15}")
    print(f"{'Avg repeated inconsistencies':<35} {stats_a['avg_repeated_inconsistencies']:<15} {stats_b['avg_repeated_inconsistencies']:<15}")
    print(f"{'Inconsistency rate/turn':<35} {stats_a['avg_inconsistency_rate']:<15} {stats_b['avg_inconsistency_rate']:<15}")
    print(f"{'Avg turn length (words)':<35} {stats_a['avg_turn_length']:<15} {stats_b['avg_turn_length']:<15}")
    
    improvement_inc = ((stats_b['avg_inconsistencies'] - stats_a['avg_inconsistencies']) / stats_b['avg_inconsistencies'] * 100) if stats_b['avg_inconsistencies'] > 0 else 0
    improvement_rep = ((stats_b['avg_repeated_inconsistencies'] - stats_a['avg_repeated_inconsistencies']) / stats_b['avg_repeated_inconsistencies'] * 100) if stats_b['avg_repeated_inconsistencies'] > 0 else 0
    
    print("\n" + "="*70)
    print(f"Method A reduces inconsistencies by {improvement_inc:.1f}%")
    print(f"Method A reduces repeated inconsistencies by {improvement_rep:.1f}%")
    print("="*70)
    
    print(f"\nResults saved in: {output_path}")
    
    return results


# =============================================================================
# FUNCTION FOR ANALYSIS
# =============================================================================

def analyze_mode(input_dir, output_dir):
    """Runs analyze_metrics.py with specified parameters."""
    import subprocess
    import sys
    
    cmd = [sys.executable, "analyze_metrics.py", "--input", input_dir, "--output", output_dir]
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unified script for story generation and method comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py single                        # One story with Method A
  python run.py single --method B --turns 5   # One story with Method B, 5 turns
  python run.py single --interactive          # Interactive mode
  python run.py compare --runs 10 --turns 10  # Full comparison
  python run.py analyze --input final_results # Generate charts
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Subparser for 'single'
    single_parser = subparsers.add_parser("single", help="Generate a single story")
    single_parser.add_argument("--method", type=str, choices=["A", "B"], default="A",
                               help="Method to use: A (with learning) or B (baseline). Default: A")
    single_parser.add_argument("--turns", type=int, default=10,
                               help="Number of turns. Default: 10")
    single_parser.add_argument("--interactive", "-i", action="store_true",
                               help="Interactive mode (enter input at each turn)")
    
    # Subparser for 'compare'
    compare_parser = subparsers.add_parser("compare", help="Compare Method A vs B")
    compare_parser.add_argument("--runs", type=int, default=3,
                                help="Number of runs per method. Default: 3")
    compare_parser.add_argument("--turns", type=int, default=10,
                                help="Number of turns per story. Default: 10")
    compare_parser.add_argument("--output", type=str, default="comparison_results",
                                help="Output directory. Default: comparison_results")
    
    # Subparser for 'analyze'
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results and generate charts")
    analyze_parser.add_argument("--input", type=str, default="final_results",
                                help="Directory with results. Default: final_results")
    analyze_parser.add_argument("--output", type=str, default="analysis_graphs",
                                help="Output directory for charts. Default: analysis_graphs")
    
    args = parser.parse_args()
    
    if args.command == "single":
        run_single_story_mode(args.method, args.turns, args.interactive)
    
    elif args.command == "compare":
        print(f"\nCOMPARISON METHOD A vs B")
        print(f"   - Runs per method: {args.runs}")
        print(f"   - Turns per story: {args.turns}")
        print(f"   - Output directory: {args.output}")
        
        input("\nPress ENTER to start...")
        compare_methods_mode(args.runs, args.turns, args.output)
    
    elif args.command == "analyze":
        analyze_mode(args.input, args.output)
    
    else:
        parser.print_help()
