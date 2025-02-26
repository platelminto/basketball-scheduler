import json
import sys


def analyze_grid_search_results(summary_file, top_n=10):
    """
    Analyze grid search results, sorting by avg_attempts.

    Args:
        summary_file: Path to the summary JSON file
        top_n: Number of top results to show
    """
    # Load the summary file
    with open(summary_file, "r") as f:
        summary = json.load(f)

    # Extract results and filter to only successful combinations
    results = []
    for combo_key, data in summary.items():
        if data["success_rate"] > 0:  # Only include successful parameter sets
            results.append(
                {
                    "combo_key": combo_key,
                    "params": data["params"],
                    "success_rate": data["success_rate"],
                    "avg_attempts": data["avg_attempts"],
                    "min_attempts": data["min_attempts"],
                    "max_attempts": data["max_attempts"],
                }
            )

    # Sort by average attempts (lowest first)
    sorted_results = sorted(results, key=lambda x: x["avg_attempts"])

    # Display the top N results
    print(f"\nTop {min(top_n, len(sorted_results))} parameter combinations:\n")

    for i, result in enumerate(sorted_results[:top_n]):
        print(
            f"Rank {i+1}: avg_attempts={result['avg_attempts']:.1f}, success_rate={result['success_rate']*100:.0f}%"
        )
        print(f"Parameters:")
        for key, value in result["params"].items():
            print(f"  {key}: {value}")
        print()

    return sorted_results


if __name__ == "__main__":
    # Use command line argument if provided, otherwise prompt
    if len(sys.argv) > 1:
        summary_file = sys.argv[1]
    else:
        summary_file = "grid_search_results_20250227_001333_summary.json"

    top_n = 20
    if len(sys.argv) > 2:
        top_n = int(sys.argv[2])

    analyze_grid_search_results(summary_file, top_n)
