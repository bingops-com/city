"""Optional Matplotlib rendering of exported City results (engine needs no packages)."""

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Tracer les exports City avec Matplotlib")
    parser.add_argument("--results", type=Path, default=Path("results/first-simulation"))
    args = parser.parse_args()
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "city-matplotlib-cache"))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        parser.error("Ce rendu facultatif nécessite Matplotlib ; le moteur et son SVG standard n'en ont pas besoin")
    scenarios = json.loads((args.results / "suite.json").read_text(encoding="utf-8"))["scenario_descriptions"]
    plt.rcParams.update({"font.size": 10, "svg.hashsalt": "city-first-simulation", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold", "figure.facecolor": "white"})
    plots = [("Panier alimentaire proposé", "basket_price_cents", .01, "Monnaie fictive"),
             ("Trésorerie municipale", "city_cash_cents", .01, "Monnaie fictive"),
             ("Besoins alimentaires satisfaits", "food_access_rate", 100, "% des portions quotidiennes"),
             ("Ménages sans logement", "unhoused", 1, "Ménages")]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    colors = ["#315bb6", "#63832c", "#aa5a13", "#8d4dc0", "#147f81", "#c23e4b", "#976420", "#69758c", "#bc397e"]
    for index, name in enumerate(scenarios):
        file = args.results / name / "daily.csv"
        if not file.exists():
            continue
        rows = list(csv.DictReader(file.open(encoding="utf-8")))
        for ax, (title, key, scale, unit) in zip(axes.flat, plots):
            ax.plot([int(r["day"]) for r in rows], [float(r[key]) * scale for r in rows],
                    color=colors[index], linewidth=1.8, label=name, alpha=.85)
    for ax, (title, key, scale, unit) in zip(axes.flat, plots):
        ax.set(title=title, xlabel="Jour simulé", ylabel=unit)
        ax.grid(alpha=.18)
        ax.set_ylim(bottom=0)
    axes.flat[2].set_ylim(0, 105)
    from matplotlib.ticker import MaxNLocator
    axes.flat[3].yaxis.set_major_locator(MaxNLocator(integer=True))
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.suptitle("City — première simulation économique, graine 20261014", fontsize=18)
    fig.legend(handles, labels, loc="outside lower center", ncols=5, frameon=False)
    fig.savefig(args.results / "comparison.svg", metadata={"Date": None})
    fig.savefig(args.results / "comparison.png", dpi=150, metadata={"Software": "City simulation / Matplotlib"})
    plt.close(fig)
    print(args.results / "comparison.svg")


if __name__ == "__main__":
    main()
