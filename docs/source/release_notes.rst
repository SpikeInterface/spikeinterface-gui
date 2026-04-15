.. _release_notes:

Release Notes
=============

.. _release0.13.1:

0.13.1
------

*Release date: April 1st, 2026*

Bug fixes
~~~~~~~~~

* Fix quality curation when other labels are given by user (PR #260)
* Update channel visibility when unit is changed in unitview (#259)

Performance
~~~~~~~~~~~

* Only init views in layout in desktop mode (PR #257)


.. _release0.13.0:

0.13.0
------

*Release date: March 23rd, 2026*

New views
~~~~~~~~~

* **EventView** (PR #218): new view showing aligned spike rasters and PSTHs around events; events can be passed to ``run_mainwindow`` as a plain dict or as a ``spikeinterface.BaseEvent`` object
* **AmplitudeScalingsView** (PR #230): new view showing amplitude scaling factors
* **MainChannelTemplate view** (PR #233): shows the main channel waveform template

Curation
~~~~~~~~

* Renamed ``CurationModel`` to ``Curation`` to align with the updated SpikeInterface API (PR #252)
* Added ``curation_callback`` and ``set_external_curation`` for programmatic curation control (PR #241)
* Validate curation data and support curation format v1/v2 (PR #211)
* Remove default ``num_chan`` (sparsity) column from unit list; add a "clear" label shortcut (PR #244)
* Fixed ``include_deleted`` behavior and unit order in merge list (PR #245)
* Added "remove from merge list" to unit list right-click context menu (PR #232)

Trace and scatter views
~~~~~~~~~~~~~~~~~~~~~~~

* **Valid periods regions in scatter plots** (PR #254): shaded valid-period regions on scatter views (e.g. amplitude, ISI); can be disabled in settings
* **Event navigation in Trace/TraceMap views** (PR #218): previous/next event buttons with event-type selector; event overlays on trace and trace map views
* Fixed binning and limits in ``basescatterview`` (PRs #235, #246)
* Fixed ``tracemapview`` for multi-shank probes (PR #248)
* Selectively update y-range only when unit or time changes (PR #248)

UX improvements
~~~~~~~~~~~~~~~

* **Focus mode** (PR #227): toggle to focus the display on a single unit
* **Waveform display mode** is now a persistent setting (PR #238)
* ``user_main_settings`` parameter exposed so callers can pre-configure GUI settings programmatically (PR #243)
* Fixed relative spike rate plot (PR #212)
* Allow ``nan`` metric values in MetricsView (PR #217)
* Make ``template_metrics`` dependency optional (PR #247)

Backend and architecture
~~~~~~~~~~~~~~~~~~~~~~~~

* **Plugin architecture** (PR #219): full plugin system with ``get_all_possible_views()``; plugin documentation page added
* ``skip_extensions`` parameter now passed through to the CLI entry point (PR #216)
* Allow remote S3 paths for loading (PR #214)
* ``external_data`` support in controller: pass arbitrary external data into the GUI (PR #231)
* Panel backend: multi-thread/multi-process server support (PR #240); fix color-by-visibility (PR #250)
* Removed pandas dependency
* Renamed ``crosscorrelogramview`` → ``correlogramview``
* Added codespell CI workflow (PR #215)


.. _release0.12.0:

0.12.0
------

*Release date: November 13, 2025*

New views
~~~~~~~~~

* **Unit splitting**: full splitting workflow in ``ScatterViews``, ``CurationView``, and ``CorrelogramsView``; lasso-select spikes, confirm or get notified on failure
* **Metrics view**: new view displaying quality/template metrics for selected units (Qt and Panel backends)
* **Binned spikes view**: new ``BinnedSpikesView`` showing spike rate over time

Curation
~~~~~~~~

* **Curation format v2**: updated curation format with validation; raises error on invalid curation dict
* **Auto-merge presets**: added SpikeInterface automerge presets including ``similarity``
* **Curation file CLI arg**: load a pre-existing curation file with ``--curation-file``
* **Exit dialog**: warning shown if the user has unsaved curation when closing

UX improvements
~~~~~~~~~~~~~~~

* **User settings**: save and restore default settings via a config folder
* **Waveform improvements**: option to plot sample waveforms; x/y scalebars; improved geometry mode with ``allow_long_zone``; separate auto-move and auto-zoom settings
* **Custom layout**: JSON layout support via ``--layout`` CLI argument; refactored greedy layout algorithm
* **Busy indicator**: context manager for busy indicator during long operations (traces, merges, compute)
* **Recording times**: ``main_setting`` option to use recording times

Backend and architecture
~~~~~~~~~~~~~~~~~~~~~~~~

* **Only load required extensions**: skip analyzer extensions not needed by the displayed views
* **Performance (Panel/web)**: caching correlograms, pre-initializing probe view ranges, faster unit list refresh, skip unrequested views
* **ReadTheDocs**: added full documentation deployment

Bug fixes
~~~~~~~~~

* ``nanmin``/``nanmax`` for spike location extrema; channel ordering in probe map; lasso selection and split shortcut; noise levels when analyzer has no noise; spike rate for short recordings; ``return_scaled`` → ``return_in_uV`` API change


.. _release0.11.0:

0.11.0
------

*Release date: June 25, 2025*

Backend and architecture
~~~~~~~~~~~~~~~~~~~~~~~~

* **Dual-backend architecture**: major refactoring to support both a Qt desktop backend and a Panel/Bokeh web backend from the same codebase
* **Launcher**: GUI launcher for desktop (Qt) and web (Panel) modes; supports ``analyzer_folders`` dict; prints server address
* **Layout presets**: 8-zone layout system with configurable presets; GridStack for web layout

UX improvements
~~~~~~~~~~~~~~~

* **Color modes**: configurable color mode in main settings
* **Waveform overlap**: show overlapping waveforms with ``Ctrl+O``; ``Alt+Scroll`` to widen narrow waveforms
* **Exclude deleted units from merge view**: option to hide already-deleted units in ``MergeView``
* **Probe view**: better automatic ROI when multiple units are selected
* ``with_traces=False`` **option**: option to not show traces in the main window

Performance and bug fixes
~~~~~~~~~~~~~~~~~~~~~~~~~

* Faster waveform loading; faster spike amplitude and correlograms; export curation to download JSON
* Manual unit label fix; ``time_info_updated`` signal to avoid recursive calls


.. _release0.10.0:

0.10.0
------

*Release date: February 12, 2025*

* **Lasso selection in spike amplitude view**: visually select spikes with a lasso tool; enable/disable lasso button
* ``--recording`` **CLI option**: pass a recording path from the command line
* ``--recording-base-folder`` **option**: flexible recording path resolution
* **Unit list improvements**: column drag-and-drop reordering; fix string column sorting
* ``compute_merge_unit_groups``: now uses the function directly from SpikeInterface
* **Improved unit tables**: better column display


.. _release0.9.1:

0.9.1
-----

*Release date: October 9, 2024*

* **ProbeGroup support**: handle multi-shank probes via ``ProbeGroup``
* **Probe view**: second ROI with ``Ctrl``-click to add ROI for units
* **Similarity view**: ``Ctrl``-click for append mode
* ``--no-traces`` **CLI option**: start the GUI without loading traces; small trace cache added
* **Python version**: updated support for Python 3.9+ and 3.11
* **Bug fixes**: spike list and visible spikes; documentation updates


.. _release0.9.0:

0.9.0
-----

*Release date: July 19, 2024*

New views
~~~~~~~~~

* **TraceMapView**: new view showing a heatmap of traces on the probe
* ``WaveformHeatMapView`` **made optional**: avoid accidentally triggering expensive recomputation

Curation
~~~~~~~~

* **Curation GUI**: full curation interface with merge, delete, label operations, keyboard shortcuts (``d`` delete, ``Space`` toggle visibility, ``m`` merge), and curation export aligned with SpikeInterface curation format
* **Sortable unit and pair lists**: click column headers to sort; pair list shows merge candidates
* **Proposed merges**: compute and propose merge groups based on multiple methods/criteria

Backend and architecture
~~~~~~~~~~~~~~~~~~~~~~~~

* **SortingAnalyzer support**: complete refactor to use the new ``SortingAnalyzer`` API from SpikeInterface (replaces ``WaveformExtractor``)
* **View dependency on extensions**: views only shown/enabled if the required analyzer extension is computed
* ``noise_levels`` **optional**: noise display on spike amplitude view is optional if not computed


.. _release0.8.0:

0.8.0
-----

*Release date: March 12, 2024*

* API compatibility update: ``sample_ind`` → ``sample_index``
* Minor fixes and README/documentation improvements


.. _release0.7.0:

0.7.0
-----

*Release date: July 7, 2023*

* Requires SpikeInterface >= 0.98
* **Improved channel visibility on unit selection**
* **More intuitive channel ordering** when using ROI in probe view
* Removed auto channel visibility triggered by spike list selection
* API update: ``sample_ind`` → ``sample_index``
* Documentation improvements


.. _release0.6.0:

0.6.0
-----

*Release date: February 10, 2023*

* **Sparsity from WaveformExtractor**: use sparsity defined in the waveform extractor when available
* Performance optimizations at startup


.. _release0.5.1:

0.5.1
-----

*Release date: October 21, 2022*

* Migrated packaging from ``setup.py`` to ``pyproject.toml``
* Anticipate upcoming SpikeInterface API changes
* Small bug fixes


.. _release0.5.0:

0.5.0
-----

*Release date: September 2, 2022*

* **Compatibility with SpikeInterface 0.95.0**: updates for the SI master refactor
* **Speed improvements**: faster startup and faster multi-unit selection
* Correlogram: ``symmetrize=True`` by default
* Background color change and small fixes


.. _release0.4.1:

0.4.1
-----

*Release date: April 15, 2022*

* API fix: ``localize_unit`` → ``localize_units``
* Bug fix: ``QColor`` cast issue


.. _release0.4.0:

0.4.0
-----

*Release date: February 4, 2022*

New views
~~~~~~~~~

* **Spike amplitude view**: new view showing spike amplitudes over time with amplitude histogram
* **Metrics in unit list**: quality/template metrics displayed as columns in the unit list

Bug fixes
~~~~~~~~~

* Switched to ``localize_units`` from SpikeInterface
* Fixed label order in trace view
* Avoid refreshing channel visibility on spike select
* Various small fixes


.. _release0.3.0:

0.3.0
-----

*Release date: October 12, 2021*

* **Speed improvements**: removed internal spike ``selected``/``visible`` tracking for faster performance
* Improved waveform width handling
* Improved spike list view
* ProbeView bug fix: ``on_unit_visibility_changed``
* Code cleanup


.. _release0.2.0:

0.2.0
-----

*Release date: October 7, 2021*

* **Compute button**: trigger waveform/extension computation from within the GUI
* **Help in dock title bar**: contextual help accessible from view title bars
* **Speed improvements**: startup speed and probe view refresh speed
* Configurable sparsity threshold
* Color and sparsity improvements


.. _release0.1.0:

0.1.0
-----

*Release date: September 22, 2021*

* Initial release
