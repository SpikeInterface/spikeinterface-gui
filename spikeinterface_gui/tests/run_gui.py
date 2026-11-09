"""
Launch the GUI on a test dataset from tests/datasets, built on first use.

    python run_gui.py                          # desktop, small dataset, with curation
    python run_gui.py --mode web --events samples
    python run_gui.py --comparison --mode web
    python run_gui.py --launcher
    panel serve run_gui.py --autoreload        # web, default options
"""
from argparse import ArgumentParser

from spikeinterface import load_sorting_analyzer

from spikeinterface_gui import run_mainwindow, run_mainwindow_comparison, run_launcher
from spikeinterface_gui.tests.testingtools import (
    DATASETS_FOLDER, get_dataset_folder, make_curation_dict, prepare_analyzer_for_gui, set_comparison_labels,
)

parser = ArgumentParser(description=__doc__.split("\n\n")[0])
parser.add_argument('--mode', default="desktop", choices=["desktop", "web"])
parser.add_argument('--comparison', action="store_true", help='Compare two analyzers')
parser.add_argument('--dataset', default="small",
                    help='small | medium-split | multiprobe | big, or small | medium with --comparison')
parser.add_argument('--regenerate', action="store_true", help='Rebuild the dataset')
parser.add_argument('--events', choices=["times", "samples"], help='Simulate events, given as times or samples')
parser.add_argument('--no-curation', action="store_true", help='Disable curation')
parser.add_argument('--iterative', action="store_true", help='Run iterative curation')
parser.add_argument('--layout', default="default", help='Layout preset')
parser.add_argument('--lazy', action="store_true", help='Lazy load')
parser.add_argument('--port', default=0, type=int, help='Port for the web server')
parser.add_argument('--no-start', action="store_true", help='Do not start the app')
parser.add_argument('--launcher', action="store_true", help='Open the launcher on all datasets in tests/datasets')


def main(args, start_app=True):
    if args.launcher:
        return run_launcher(mode=args.mode, root_folder=DATASETS_FOLDER, port=args.port, verbose=True)

    folder = get_dataset_folder(args.dataset, comparison=args.comparison, regenerate=args.regenerate)

    if args.comparison:
        analyzer1 = load_sorting_analyzer(folder / "sorting_analyzer_1", lazy=args.lazy)
        analyzer2 = load_sorting_analyzer(folder / "sorting_analyzer_2", lazy=args.lazy)
        set_comparison_labels(analyzer1, analyzer2)
        return run_mainwindow_comparison(
            analyzer1, analyzer2, analyzer1_name="sorter1", analyzer2_name="sorter2",
            mode=args.mode, start_app=start_app, verbose=True, port=args.port,
        )

    analyzer = load_sorting_analyzer(folder / "sorting_analyzer", load_extensions=False, lazy=args.lazy)
    extra_unit_properties, events = prepare_analyzer_for_gui(analyzer, events=args.events)
    curation = not args.no_curation
    return run_mainwindow(
        analyzer,
        mode=args.mode,
        start_app=start_app,
        verbose=True,
        curation=curation,
        curation_dict=make_curation_dict(analyzer) if curation else None,
        iterative_curation=args.iterative,
        extra_unit_properties=extra_unit_properties,
        layout_preset=args.layout,
        events=events,
        port=args.port,
    )


if __name__ == '__main__':
    args = parser.parse_args()
    win = main(args, start_app=not args.no_start)
elif __name__.startswith("bokeh"):
    # panel serve: the window registers itself as servable
    win = main(parser.parse_args(["--mode", "web"]), start_app=False)
