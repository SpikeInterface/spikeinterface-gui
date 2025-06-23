from pathlib import Path
import spikeinterface as si
from spikeinterface.widgets.sorting_summary import _default_displayed_unit_properties

from spikeinterface_gui.main import run_mainwindow
from spikeinterface_gui.layout_presets import _presets


class Launcher:
    def __init__(self, analyzers_folder=None, backend="qt", verbose=False):
        from spikeinterface_gui.main import check_folder_is_analyzer

        if analyzers_folder is not None:
            self.analyzer_folders = [
                p for p in Path(analyzers_folder).iterdir() if p.is_dir() and check_folder_is_analyzer(p)
            ]
        else:
            self.analyzer_folders = None

        self.analyzer_path = None
        self.recording_path = None
        self.curation = True
        self.displayed_properties = None
        self.verbose = verbose

        if backend == "qt":
            self._qt_make_layout()
        elif backend == "panel":
            self._panel_make_layout()

    def _load_analyzer(self):
        if self.verbose:
            print(f"Loading analyzer from {self.analyzer_path}...")
        self.analyzer = si.load(self.analyzer_path, load_extensions=False)
        if self.verbose:
            print(f"Analyzer loaded: {self.analyzer}")

    def _qt_make_layout(self):
        from .myqt import QT
        from .layout_presets import _presets
        from .main import run_mainwindow

        # Get the Qt app instance created by run_launcher
        app = QT.QApplication.instance()

        # Create main window and central widget
        self.window = QT.QMainWindow()
        central_widget = QT.QWidget()
        self.window.setCentralWidget(central_widget)
        layout = QT.QVBoxLayout()
        central_widget.setLayout(layout)

        # Create form layout for inputs
        form_layout = QT.QFormLayout()

        # Analyzer path input
        if self.analyzer_folders is None:
            path_layout = QT.QHBoxLayout()
            self.analyzer_path_input = QT.QLineEdit()
            browse_button = QT.QPushButton("Browse...")
            browse_button.clicked.connect(self._qt_browse_analyzer_path)
            path_layout.addWidget(self.analyzer_path_input)
            path_layout.addWidget(browse_button)
            form_layout.addRow("Analyzer path:", path_layout)
        else:
            self.analyzer_path_input = QT.QComboBox()
            self.analyzer_path_input.addItems([str(p) for p in self.analyzer_folders])
            form_layout.addRow("Analyzer folder:", self.analyzer_path_input)

        # Recording selection checkbox and path input
        self.select_recording_checkbox = QT.QCheckBox()
        self.select_recording_checkbox.setToolTip(
            "Check this box to select a recording to load for the analyzer.\n"
            "The preprocessing pipeline will be applied to the recording if available."
        )
        form_layout.addRow("Select recording:", self.select_recording_checkbox)

        recording_path_layout = QT.QHBoxLayout()
        self.recording_path_input = QT.QLineEdit()
        self.recording_path_input.setVisible(False)
        browse_recording_button = QT.QPushButton("Browse...")
        browse_recording_button.clicked.connect(self._qt_browse_recording_path)
        browse_recording_button.setVisible(False)
        self.browse_recording_button = browse_recording_button
        recording_path_layout.addWidget(self.recording_path_input)
        recording_path_layout.addWidget(browse_recording_button)
        form_layout.addRow("Recording path (optional):", recording_path_layout)

        # Displayed properties input
        self.displayed_properties_input = QT.QLineEdit()
        self.displayed_properties_input.setText("default")
        self.displayed_properties_input.setToolTip(
            "Comma-separated list of unit properties to display.\n"
            "Use 'default' to show the default properties.\n"
            "Example: 'amplitude, snr, firing_rate'\n"
        )

        form_layout.addRow("Displayed unit properties:", self.displayed_properties_input)

        # Layout preset selector
        self.layout_preset_selector = QT.QComboBox()
        self.layout_preset_selector.addItems(list(_presets.keys()))
        form_layout.addRow("Layout preset:", self.layout_preset_selector)

        # Curation checkbox
        self.curation_checkbox = QT.QCheckBox()
        self.curation_checkbox.setChecked(self.curation)
        self.curation_checkbox.setToolTip("Enable or disable curation features in the GUI")
        form_layout.addRow("Enable curation:", self.curation_checkbox)

        # Launch button
        self.launch_button = QT.QPushButton("Launch!")

        # Add layouts to main layout
        layout.addLayout(form_layout)
        layout.addWidget(self.launch_button)

        # Connect signals
        self.select_recording_checkbox.stateChanged.connect(self._qt_on_select_recording)
        self.launch_button.clicked.connect(self._qt_on_launch_clicked)

        # Show window
        self.window.setWindowTitle("SpikeInterface GUI Launcher")
        self.window.resize(600, 400)
        # Set window icon
        icon_file = Path(__file__).absolute().parent / "img" / "si.png"
        if icon_file.exists():
            self.window.setWindowIcon(QT.QIcon(str(icon_file)))

        self.window.show()

    def _qt_on_select_recording(self, state):
        is_visible = bool(state)
        self.recording_path_input.setVisible(is_visible)
        self.browse_recording_button.setVisible(is_visible)

    def _qt_browse_analyzer_path(self):
        from .myqt import QT

        path = QT.QFileDialog.getExistingDirectory(
            self.window, "Select Analyzer Directory", "", QT.QFileDialog.ShowDirsOnly
        )
        if path:
            self.analyzer_path_input.setText(path)

    def _qt_browse_recording_path(self):
        from .myqt import QT

        path = QT.QFileDialog.getExistingDirectory(
            self.window, "Select Recording Directory", "", QT.QFileDialog.ShowDirsOnly
        )
        if path:
            self.recording_path_input.setText(path)

    def _qt_on_launch_clicked(self):
        from .myqt import QT

        # Get values from inputs
        if self.analyzer_folders is None:
            self.analyzer_path = self.analyzer_path_input.text()
        else:
            self.analyzer_path = str(self.analyzer_folders[self.analyzer_path_input.currentIndex()])

        if self.select_recording_checkbox.isChecked():
            self.recording_path = self.recording_path_input.text()
        else:
            self.recording_path = None

        if self.displayed_properties_input.text() != "default":
            self.displayed_properties = [
                prop.strip() for prop in self.displayed_properties_input.text().split(",") if prop.strip()
            ]
        self.curation = self.curation_checkbox.isChecked()

        # Create loading dialog with spinner
        loading = QT.QDialog(self.window)
        loading.setWindowTitle("Loading")
        loading.setModal(True)  # Keep it modal but allow closing

        # Create layout
        layout = QT.QVBoxLayout(loading)

        # Simple static circle
        circle = QT.QFrame()
        circle.setFixedSize(40, 40)
        circle.setStyleSheet(
            """
            QFrame {
                border: 3px solid #999;
                border-radius: 20px;
                margin: 10px;
            }
        """
        )
        layout.addWidget(circle, 0, QT.Qt.AlignHCenter)

        # Add label with initial text
        label = QT.QLabel("Initializing...")
        label.setStyleSheet("color: #333333; margin: 10px; font-size: 14px;")
        layout.addWidget(label, 0, QT.Qt.AlignHCenter)

        # Add spacing
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Set size and position
        loading.setFixedSize(450, 160)
        loading.move(
            self.window.x() + (self.window.width() - loading.width()) // 2,
            self.window.y() + (self.window.height() - loading.height()) // 2,
        )

        loading.show()

        # Load the analyzer
        if self.verbose:
            print(f"Loading analyzer from {self.analyzer_path}...")
        label.setText("Loading analyzer...")
        QT.QApplication.processEvents()  # Update UI
        self._load_analyzer()

        label.setText("Initializing main window...")
        QT.QApplication.processEvents()  # Update UI

        # Get reference to existing Qt app
        app = QT.QApplication.instance()

        try:
            # Run the main window without starting a new event loop
            self.main_window = run_mainwindow(
                self.analyzer,
                mode="desktop",
                with_traces=True,
                curation=self.curation,
                displayed_unit_properties=self.displayed_properties,
                layout_preset=self.layout_preset_selector.currentText(),
                recording=None if not self.recording_path else self.recording_path,
                start_app=False,  # Don't start a new event loop, using the one from run_launcher
            )
            # Close dialog
            loading.close()

            # Set the main window as active
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception as e:
            print(f"Error initializing main window: {e}")
            label.setText(f"Error: {e}")
            loading.adjustSize()

    def _panel_make_layout(self):
        import panel as pn

        pn.extension()

        displayed_properties_widget = pn.widgets.TextInput(
            name="Displayed unit properties", value="default", height=50, sizing_mode="stretch_width"
        )
        displayed_properties_widget.tooltip = (
            "Comma-separated list of unit properties to display.\n"
            "Use 'default' to show the default properties.\n"
            "Example: 'amplitude, snr, firing_rate'\n"
        )

        analyzer_path_widget = pn.widgets.TextInput(
            name="Analyzer path", value="", height=50, sizing_mode="stretch_width"
        )

        layout_presets = list(_presets.keys())
        layout_selector = pn.widgets.Select(
            name="Layout preset",
            options=layout_presets,
            value=layout_presets[0] if layout_presets else None,
            height=50,
            sizing_mode="stretch_width",
        )
        if self.analyzer_folders is None:
            analyzer_loader = analyzer_path_widget
        else:
            analyzer_loader = pn.widgets.Select(
                name="Analyzer folder",
                options=self.analyzer_folders,
                value=self.analyzer_folders[0],
                height=50,
                width=500,
            )

        self.launch_button = pn.widgets.Button(
            name="Launch!", button_type="primary", height=50, sizing_mode="stretch_width"
        )
        curation_checkbox = pn.widgets.Checkbox(
            name="Enable curation", value=True, height=50, sizing_mode="stretch_width"
        )
        curation_checkbox.tooltip = ("Enable or disable curation features in the GUI",)

        select_recording_checkbox = pn.widgets.Checkbox(
            name="Select recording", value=False, height=50, sizing_mode="stretch_width"
        )
        select_recording_checkbox.tooltip = (
            "Check this box to select a recording to load for the analyzer.\n"
            "The preprocessing pipeline will be applied to the recording if available."
        )
        self.recording_path_widget = pn.widgets.TextInput(
            name="Recording path (optional)", value="", height=50, visible=False, sizing_mode="stretch_width"
        )

        # Add event listeners
        select_recording_checkbox.param.watch(self._panel_on_select_recording, "value")

        # Safe JS-on-click with args:
        self.launch_button.js_on_click(
            args=dict(
                analyzer=analyzer_loader,
                recording_path=self.recording_path_widget,
                displayed=displayed_properties_widget,
                layout_presets=layout_selector,
                curation=curation_checkbox,
            ),
            code="""
                const url = `/gui?` +
                            `analyzer_path=${encodeURIComponent(analyzer.value)}&` +
                            `recording_path=${encodeURIComponent(recording_path.value)}&` +
                            `layout_preset=${layout_presets.value}&` +
                            `displayed_properties=${encodeURIComponent(displayed.value)}&` +
                            `curation=${curation.active}`;
                console.log("Launching URL:", url);
                window.open(url, '_blank');
            """,
        )

        self.layout = pn.Column(
            pn.Row(
                analyzer_loader,
                self.recording_path_widget,
                sizing_mode="stretch_width",
            ),
            pn.Row(
                displayed_properties_widget,
                sizing_mode="stretch_width",
            ),
            pn.Row(
                curation_checkbox,
                select_recording_checkbox,
                sizing_mode="stretch_width",
            ),
            pn.Row(
                layout_selector,
                self.launch_button,
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown("Click 'Launch!' to initialize the GUI"),
            sizing_mode="stretch_width",
        )

    def _panel_on_select_recording(self, event):
        self.recording_path_widget.visible = event.new


def panel_gui_view():
    """Create a Panel GUI view for the SpikeInterface GUI with launcher"""
    import panel as pn

    pn.extension()

    # Read query params at runtime
    params = pn.state.session_args
    analyzer_path = params.get("analyzer_path", [None])[0].decode("utf-8")
    recording_path = params.get("recording_path", [None])[0].decode("utf-8")
    displayed_properties = params.get("displayed_properties", [None])[0].decode("utf-8")
    curation = bool(params.get("curation", [False])[0].decode("utf-8"))
    layout_preset = params.get("layout_preset", [None])[0].decode("utf-8")

    try:
        if analyzer_path is None:
            raise ValueError(
                "You must specify the analyzer path in the URL query parameters, e.g., ?analyzer_path=/path/to/analyzer"
            )

        if displayed_properties is not None:
            displayed_properties = [prop.strip() for prop in displayed_properties.split(",") if prop.strip()]

        analyzer = si.load(analyzer_path, load_extensions=False)
        if recording_path is not None and recording_path != "":
            from spikeinterface.preprocessing.pipeline import (
                get_preprocessing_dict_from_analyzer,
                apply_preprocessing_pipeline,
            )

            try:
                recording = si.load(recording_path)
                preprocessing_pipeline = get_preprocessing_dict_from_analyzer(analyzer_path)
                recording_processed = apply_preprocessing_pipeline(
                    recording,
                    preprocessing_pipeline,
                )
                analyzer.set_temporary_recording(recording_processed)
            except:
                print(f"Failed to load processed recording from {recording_path}.")

        # instantiate the main window with the loaded analyzer
        win = run_mainwindow(
            analyzer,
            mode="web",
            with_traces=True,
            curation=curation,
            displayed_unit_properties=displayed_properties,
            layout_preset=layout_preset,
            start_app=False,  # Do not start the app loop here
        )
        win.main_layout.servable(title="SpikeInterface GUI")
    except Exception as e:
        print(f"Error initializing GUI: {e}")
        win = pn.pane.Markdown(
            f"""
            # Loading error!

            An error occurred while initializing the SpikeInterface GUI:  
            **{e}**  
            Please check the console for more details.
            """,
            sizing_mode="stretch_width",
        )
        win.servable(title="SpikeInterface GUI Error")
    return win
