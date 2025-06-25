from pathlib import Path
import spikeinterface as si
from spikeinterface.widgets.sorting_summary import _default_displayed_unit_properties

from spikeinterface_gui.main import run_mainwindow
from spikeinterface_gui.layout_presets import _presets


class Launcher:
    """
    Launcher class for the SpikeInterface GUI.

    Parameters
    ----------
    analyzers_folder : str, list or None
        Path to the folder containing analyzer folders or a list/dict of analyzer paths.
        If None, the user will be prompted to select an analyzer folder.
    root_folder: str|Path| None
        A folder that is explore to construct the list of analyzers.
        When not None analyzer_folders must be None.
    backend : str
        The backend to use for the GUI. Options are "qt" or "panel".
    verbose : bool
        If True, enables verbose logging in the GUI.
    """

    def __init__(self, analyzer_folders=None, root_folder=None, backend="qt", verbose=False):
        from spikeinterface_gui.main import check_folder_is_analyzer

        self.analyzer_folders = None
        if root_folder is not None:
            assert analyzer_folders is None, "When using root_folder, analyzer_folders must be None"
            root_folder = Path(root_folder)
            self.analyzer_folders = [
                f.parent for f in root_folder.glob('**/spikeinterface_info.json') if check_folder_is_analyzer(f.parent)
            ] + [
                f.parent for f in root_folder.glob('**/.zmetadata') if check_folder_is_analyzer(f.parent)
            ]
        elif analyzer_folders is not None:
            if isinstance(analyzer_folders, (list, tuple)):
                self.analyzer_folders = [ p for p in analyzer_folders if check_folder_is_analyzer(p) ]
            elif isinstance(analyzer_folders, dict):
                self.analyzer_folders = { k: p for k, p in analyzer_folders.items() if check_folder_is_analyzer(p)}
        

        self.verbose = verbose
        self.main_windows = []

        if backend == "qt":
            self._qt_make_layout()
        elif backend == "panel":
            self._panel_make_layout()


    ## Qt zone
    def _qt_open_help(self):
        import markdown
        from .myqt import QT

        # Create a help window
        help_window = QT.QDialog(self.window)
        help_window.setWindowTitle("SpikeInterface GUI Help")
        help_window.setModal(False)  # Allow interaction with main window
        help_window.resize(600, 500)

        # Create layout
        layout = QT.QVBoxLayout(help_window)

        # Create text browser for HTML content
        text_browser = QT.QTextBrowser()
        txt = _launcher_help
        html_content = markdown.markdown(txt)
        text_browser.setHtml(html_content)

        # Create close button
        close_button = QT.QPushButton("Close")
        close_button.clicked.connect(help_window.close)

        # Add widgets to layout
        layout.addWidget(text_browser)

        # Create button layout
        button_layout = QT.QHBoxLayout()
        button_layout.addStretch()  # Push button to the right
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        # Show the help window
        help_window.show()

    def _qt_make_layout(self):
        import markdown
        from .myqt import QT
        from .layout_presets import _presets

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

        # Displayed properties input
        self.displayed_properties_input = QT.QLineEdit()
        self.displayed_properties_input.setText("default")

        form_layout.addRow("Displayed unit properties:", self.displayed_properties_input)

        # Layout preset selector
        self.layout_preset_selector = QT.QComboBox()
        self.layout_preset_selector.addItems(list(_presets.keys()))
        form_layout.addRow("Layout preset:", self.layout_preset_selector)

        # Curation checkbox
        self.curation_checkbox = QT.QCheckBox()
        self.curation_checkbox.setChecked(True)
        form_layout.addRow("Enable curation:", self.curation_checkbox)

        # With traces checkbox
        self.with_traces_checkbox = QT.QCheckBox()
        self.with_traces_checkbox.setChecked(True)
        form_layout.addRow("With traces:", self.with_traces_checkbox)

        # Recording selection checkbox and path input
        self.select_recording_checkbox = QT.QCheckBox()

        recording_path_layout = QT.QHBoxLayout()
        self.recording_path_input = QT.QLineEdit()
        self.recording_path_input.setVisible(False)
        browse_recording_button = QT.QPushButton("Browse...")
        browse_recording_button.clicked.connect(self._qt_browse_recording_path)
        browse_recording_button.setVisible(False)
        self.browse_recording_button = browse_recording_button
        recording_select_type = QT.QComboBox()
        recording_select_type.addItems(["raw", "preprocessed"])
        recording_select_type.setVisible(False)
        self.recording_select_type = recording_select_type
        recording_path_layout.addWidget(self.select_recording_checkbox)
        recording_path_layout.addWidget(self.recording_path_input)
        recording_path_layout.addWidget(recording_select_type)
        recording_path_layout.addWidget(browse_recording_button)
        form_layout.addRow("Select recording:", recording_path_layout)

        # Launch button
        self.launch_button = QT.QPushButton("Launch!")

        # Help button
        self.help_button = QT.QPushButton("?")
        self.help_button.clicked.connect(self._qt_open_help)
        form_layout.addRow("Help:", self.help_button)

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
        self.recording_select_type.setVisible(is_visible)

    def _qt_browse_analyzer_path(self):
        from .myqt import QT

        path = QT.QFileDialog.getExistingDirectory(
            self.window, "Select Analyzer Directory", "", QT.QFileDialog.ShowDirsOnly
        )
        if path:
            self.analyzer_path_input.setText(path)

    def _qt_browse_recording_path(self):
        from .myqt import QT

        # Create a dialog that allows selecting both files and directories
        dialog = QT.QFileDialog(self.window)
        dialog.setWindowTitle("Select Recording Directory or File")
        dialog.setFileMode(QT.QFileDialog.AnyFile)
        dialog.setOption(QT.QFileDialog.DontUseNativeDialog, True)
        dialog.setOption(QT.QFileDialog.ShowDirsOnly, False)
        dialog.setOption(QT.QFileDialog.ReadOnly, True)

        if dialog.exec_():
            selected_paths = dialog.selectedFiles()
            if selected_paths:
                path = selected_paths[0]
                self.recording_path_input.setText(path)

    def _qt_on_launch_clicked(self):
        from .myqt import QT

        # Get values from inputs
        if self.analyzer_folders is None:
            analyzer_path = self.analyzer_path_input.text()
        else:
            ind = self.analyzer_path_input.currentIndex()
            if isinstance(self.analyzer_folders, dict):
                k = list(self.analyzer_folders.keys())[ind]
                analyzer_path = str(self.analyzer_folders[k])
            else:
                analyzer_path = self.analyzer_folders[ind]


        if self.select_recording_checkbox.isChecked():
            recording_path = self.recording_path_input.text()
        else:
            recording_path = None

        if self.displayed_properties_input.text() != "default":
            displayed_properties = [
                prop.strip() for prop in self.displayed_properties_input.text().split(",") if prop.strip()
            ]
        else:
            displayed_properties = _default_displayed_unit_properties
        curation = self.curation_checkbox.isChecked()
        with_traces = self.with_traces_checkbox.isChecked()
        layout_preset = self.layout_preset_selector.currentText()
        recording_type = self.recording_select_type.currentText()

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

        # Get reference to existing Qt app
        app = QT.QApplication.instance()

        try:
            analyzer, recording = instantiate_analyzer_and_recording(
                analyzer_path=analyzer_path,
                recording_path=recording_path,
                recording_type=recording_type,
            )

            label.setText("Initializing main window...")
            QT.QApplication.processEvents()  # Update UI
            # Run the main window without starting a new event loop
            main_window = run_mainwindow(
                analyzer,
                recording=recording,
                mode="desktop",
                with_traces=with_traces,
                curation=curation,
                displayed_unit_properties=displayed_properties,
                layout_preset=layout_preset,
                verbose=self.verbose,
                start_app=False,  # Don't start a new event loop, using the one from run_launcher
            )
            # Close dialog
            loading.close()

            # Set the main window as active
            main_window.show()
            # self.main_window.raise_()
            main_window.activateWindow()
            main_window.main_window_closed.connect(self._qt_on_main_window_closed)
            self.main_windows.append(main_window)


        except Exception as e:
            print(f"Error initializing main window: {e}")
            label.setText(f"Error: {e}")
            loading.adjustSize()
    

    def _qt_on_main_window_closed(self, win):
        # this free memory of windows + analyzer + recording
        self.main_windows.remove(win)

    ## Panel zone

    def _panel_make_layout(self):
        import panel as pn

        pn.extension()

        displayed_properties_widget = pn.widgets.TextInput(
            name="Displayed unit properties", value="default", height=50, sizing_mode="stretch_width"
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
            value = self.analyzer_folders[0] if isinstance(self.analyzer_folders, list) \
                else list(self.analyzer_folders.values())[0]
            print(value)
            analyzer_loader = pn.widgets.Select(
                name="Analyzer folder",
                options=self.analyzer_folders,
                value=value,
                height=50,
                width=500,
            )

        self.launch_button = pn.widgets.Button(
            name="Launch!", button_type="primary", height=50, sizing_mode="stretch_width"
        )
        curation_checkbox = pn.widgets.Checkbox(
            name="Enable curation", value=True, height=50, sizing_mode="stretch_width"
        )

        with_traces_checkbox = pn.widgets.Checkbox(
            name="With traces", value=True, height=50, sizing_mode="stretch_width"
        )
        select_recording_checkbox = pn.widgets.Checkbox(
            name="Select recording", value=False, height=50, sizing_mode="stretch_width"
        )
        self.recording_path_widget = pn.widgets.TextInput(
            name="Recording path (optional)", value="", height=50, visible=False, sizing_mode="stretch_width"
        )
        self.recording_select_type = pn.widgets.Select(
            name="Recording type",
            options=["raw", "preprocessed"],
            value="raw",
            visible=False,
            height=50,
            width=200,
        )

        # Add event listeners
        select_recording_checkbox.param.watch(self._panel_on_select_recording, "value")

        # Safe JS-on-click with args:
        self.launch_button.js_on_click(
            args=dict(
                analyzer=analyzer_loader,
                recording_path=self.recording_path_widget,
                recording_type=self.recording_select_type,
                displayed=displayed_properties_widget,
                layout_presets=layout_selector,
                curation=curation_checkbox,
                with_traces=with_traces_checkbox,
                verbose=self.verbose,
            ),
            code="""
                const url = `/gui?` +
                            `analyzer_path=${encodeURIComponent(analyzer.value)}&` +
                            `recording_path=${encodeURIComponent(recording_path.value)}&` +
                            `recording_type=${recording_type.value}&` +
                            `layout_preset=${layout_presets.value}&` +
                            `displayed_properties=${encodeURIComponent(displayed.value)}&` +
                            `curation=${curation.active}&` +
                            `with_traces=${with_traces.active}&` +
                            `verbose=${verbose}`;
                console.log("Launching URL:", url);
                window.open(url, '_blank');
            """,
        )

        helper_tab = pn.pane.Markdown(
            _launcher_help,
            sizing_mode="stretch_width",
        )

        launcher_layout = pn.Column(
            pn.Row(
                analyzer_loader,
                self.recording_path_widget,
                self.recording_select_type,
                sizing_mode="stretch_width",
            ),
            pn.Row(
                displayed_properties_widget,
                sizing_mode="stretch_width",
            ),
            pn.Row(
                curation_checkbox,
                with_traces_checkbox,
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

        self.layout = pn.Tabs(
            ("📊", launcher_layout),
            ("ℹ️", helper_tab),
            dynamic=True,
            tabs_location="left",
        )

    def _panel_on_select_recording(self, event):
        self.recording_path_widget.visible = event.new
        self.recording_select_type.visible = event.new


def panel_gui_view():
    """Create a Panel GUI view for the SpikeInterface GUI with launcher"""
    import panel as pn

    pn.extension()

    # Read query params at runtime
    params = pn.state.session_args
    analyzer_path = params.get("analyzer_path", [None])[0].decode("utf-8")
    recording_path = params.get("recording_path", [None])[0].decode("utf-8")
    recording_type = params.get("recording_type", [None])[0].decode("utf-8")
    displayed_properties = params.get("displayed_properties", [None])[0].decode("utf-8")
    curation = params.get("curation", [False])[0].decode("utf-8") == "true"
    with_traces = params.get("with_traces", [True])[0].decode("utf-8") == "true"
    layout_preset = params.get("layout_preset", [None])[0].decode("utf-8")
    verbose = params.get("verbose", [False])[0].decode("utf-8") == "true"

    try:
        # Instantiate the analyzer based on the provided parameters
        analyzer, recording = instantiate_analyzer_and_recording(
            analyzer_path=analyzer_path, recording_path=recording_path, recording_type=recording_type
        )
        if displayed_properties is not None:
            displayed_properties = [prop.strip() for prop in displayed_properties.split(",") if prop.strip()]

        # instantiate the main window with the loaded analyzer
        win = run_mainwindow(
            analyzer,
            recording=recording,
            mode="web",
            curation=curation,
            displayed_unit_properties=displayed_properties,
            layout_preset=layout_preset,
            with_traces=with_traces,
            verbose=verbose,
            start_app=False,  # Do not start the app loop here
        )
        win.main_layout.servable(title="SpikeInterface GUI")
        main_layout = win.main_layout
    except Exception as e:
        print(f"Error initializing GUI: {e}")
        main_layout = pn.pane.Markdown(
            f"""
            # Loading error!

            An error occurred while initializing the SpikeInterface GUI:  
            **{e}**  
            Please check the console for more details.
            """,
            sizing_mode="stretch_width",
        )
        main_layout.servable(title="SpikeInterface GUI Error")
    return main_layout


def instantiate_analyzer_and_recording(analyzer_path=None, recording_path=None, recording_type="raw"):
    if analyzer_path is None:
        raise ValueError(
            "You must specify the analyzer path in the URL query parameters, e.g., ?analyzer_path=/path/to/analyzer"
        )

    analyzer = si.load(analyzer_path, load_extensions=False)
    recording_processed = None
    if recording_path is not None and recording_path != "":
        try:
            recording = si.load(recording_path)
            if recording_type == "raw":
                from spikeinterface.preprocessing.pipeline import (
                    get_preprocessing_dict_from_analyzer,
                    apply_preprocessing_pipeline,
                )

                preprocessing_pipeline = get_preprocessing_dict_from_analyzer(analyzer_path)
                recording_processed = apply_preprocessing_pipeline(
                    recording,
                    preprocessing_pipeline,
                )
            else:
                recording_processed = recording
        except:
            print(f"Failed to load processed recording from {recording_path}.")

    return analyzer, recording_processed


_launcher_help = """
# SpikeInterface GUI Launcher

This launcher allows you to start the SpikeInterface GUI with a specific analyzer and recording.
You can select an analyzer folder, specify a recording path, choose displayed properties, and set layout presets.
The GUI will open in a new tab with the specified parameters whrn you click "Launch!".

## Instructions

**Analyzer Path**:  

Enter the path to the analyzer folder or select from the dropdown.

**Displayed Unit Properties**:

Enter a comma-separated list of unit properties to display in the GUI.
Use 'default' to show the default properties.

**Layout Preset**:

Select a layout preset for the GUI from the dropdown.

**Curation**:

Check the box to enable curation features in the GUI.

**With Traces**:

Check the box to display traces in the GUI, or uncheck to disable them for performance reasons.

**Select Recording**:

Check the box to enable the recording path input and select a recording to load for the analyzer.
This can be useful when the original recording is not available or it has been moved or renamed.
When selecting this option, you can specify a recording path that will be used to load the recording.

* **Recording Path**: Enter the path to a recording to load and set as the recording for the analyzer.
* **Recording Type**: Choose between "raw" or "preprocessed" recording types.
  - "raw" will load the raw recording and apply the preprocessing pipeline from the analyzer.
  - "preprocessed" will load the recording as is without applying any preprocessing.
"""
