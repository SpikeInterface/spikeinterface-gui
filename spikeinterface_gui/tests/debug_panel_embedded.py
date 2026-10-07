import panel as pn
from pathlib import Path
from spikeinterface import load_sorting_analyzer
from spikeinterface_gui import run_mainwindow

pn.extension()


test_folder = Path(__file__).parent / 'my_dataset_small'


analyzer = load_sorting_analyzer(test_folder / "sorting_analyzer")

# State in the parent app
status_md = pn.pane.Markdown("No curation submitted yet.")


def on_curation_saved(curation_data, title):
    """This runs in the parent app's context — pure Python, no JS."""
    status_md.object = f"{title}\n\nReceived curation data:\n```\n{curation_data}\n```"
    # You can do anything here: save to DB, trigger a pipeline, etc.

# Create the embedded GUI with the callback
win = run_mainwindow(
    analyzer,
    mode="web",
    start_app=False,
    panel_window_servable=False,
    curation=True,
    curation_callback=on_curation_saved,
    curation_callback_kwargs={"title": "✅ Curation received!\n"},
)

# Compose the parent layout
parent_layout = pn.Column(
    "# Parent Application",
    status_md,
    pn.layout.Divider(),
    win.main_layout,
    sizing_mode="stretch_both",
)

parent_layout.servable()

pn.serve(parent_layout, port=12345, show=True)