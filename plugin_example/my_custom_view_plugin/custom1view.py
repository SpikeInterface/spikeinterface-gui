"""
Custom View Example

This module demonstrates how to create a custom view for the SpikeInterface GUI.
The view displays unit information in a simple text format and responds to GUI events.
"""

import numpy as np
from spikeinterface_gui.view_base import ViewBase


class Custom1View(ViewBase):
    """
    Example custom view that displays unit information.
    
    This view demonstrates:
    - How to create layouts for Qt backend
    - How to refresh the view when data changes
    - How to respond to unit selection and visibility changes
    - How to access controller data (units, sorting, etc.)
    """
    
    # Unique identifier for this view (used in layout configurations)
    id = "custom1"
    
    # List of supported backends - this example only implements Qt
    # You can add 'panel' if you also implement the Panel backend methods
    _supported_backend = ['qt']
    
    # Help text displayed to users
    _gui_help_txt = """
    Custom View Example
    
    This is an example custom view that displays:
    - Total number of units
    - Number of visible units
    - List of visible unit IDs
    - Unit firing rates (if available)
    
    The view updates automatically when:
    - Unit visibility changes
    - Manual curation is performed
    """
    
    # Set to None if view doesn't need settings, or define a list of setting dictionaries
    _settings = None
    
    def __init__(self, controller=None, parent=None, backend="qt"):
        """
        Initialize the custom view.
        
        Parameters
        ----------
        controller : Controller
            The main controller object containing all data
        parent : QWidget or None
            Parent widget (for Qt backend)
        backend : str
            Backend to use ('qt' or 'panel')
        """
        super().__init__(controller=controller, parent=parent, backend=backend)
    
    ## Qt Backend Implementation ##
    
    def _qt_make_layout(self):
        """
        Create the Qt layout for the view.
        
        This is called once during initialization. Set up all widgets here.
        """
        from spikeinterface_gui.myqt import QT
        
        # Create main layout
        self.layout = QT.QVBoxLayout()
        self.qt_widget.setLayout(self.layout)
        
        # Add a title label
        title_label = QT.QLabel("<h2>Custom 1 View Example</h2>")
        title_label.setAlignment(QT.Qt.AlignCenter)
        self.layout.addWidget(title_label)
        
        # Add a text browser to display information
        self.text_display = QT.QTextBrowser()
        self.text_display.setStyleSheet("""
            QTextBrowser {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
                font-size: 11pt;
            }
        """)
        self.layout.addWidget(self.text_display)
        
        # Add buttons
        button_layout = QT.QHBoxLayout()
        
        refresh_button = QT.QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        button_layout.addWidget(refresh_button)
        
        show_all_button = QT.QPushButton("Show All Units")
        show_all_button.clicked.connect(self._qt_show_all_units)
        button_layout.addWidget(show_all_button)
        
        hide_all_button = QT.QPushButton("Hide All Units")
        hide_all_button.clicked.connect(self._qt_hide_all_units)
        button_layout.addWidget(hide_all_button)
        
        button_layout.addStretch()
        self.layout.addLayout(button_layout)
        
    def _qt_refresh(self, **kwargs):
        """
        Refresh the view with current data.
        
        This is called whenever the view needs to update its display.
        Called automatically when unit visibility changes, curation updates, etc.
        """
        # Get data from controller
        unit_ids = self.controller.unit_ids
        visible_unit_ids = self.controller.get_visible_unit_ids()
        
        # Build the display text
        html_lines = []
        html_lines.append("<h3>Unit Statistics</h3>")
        html_lines.append(f"<p><b>Total units:</b> {len(unit_ids)}</p>")
        html_lines.append(f"<p><b>Visible units:</b> {len(visible_unit_ids)}</p>")
        
        # Show visible unit IDs
        html_lines.append("<h3>Visible Unit IDs</h3>")
        if len(visible_unit_ids) > 0:
            html_lines.append("<p>")
            for unit_id in visible_unit_ids:
                color = self.get_unit_color(unit_id)
                # Convert QColor to hex for HTML
                color_hex = color.name()
                html_lines.append(f'<span style="color: {color_hex}; font-weight: bold;">●</span> {unit_id} &nbsp;&nbsp;')
            html_lines.append("</p>")
        else:
            html_lines.append("<p><i>No units visible</i></p>")
        
        # Show unit properties if available
        if hasattr(self.controller, 'units_table') and self.controller.units_table is not None:
            html_lines.append("<h3>Unit Properties</h3>")
            
            # Get visible unit properties
            visible_df = self.controller.units_table.loc[visible_unit_ids]
            
            if len(visible_df) > 0 and len(visible_df.columns) > 0:
                html_lines.append("<table border='1' cellpadding='5' style='border-collapse: collapse;'>")
                html_lines.append("<tr style='background-color: #e0e0e0;'>")
                html_lines.append("<th>Unit ID</th>")
                
                # Show first few columns
                columns_to_show = list(visible_df.columns)[:5]
                for col in columns_to_show:
                    html_lines.append(f"<th>{col}</th>")
                html_lines.append("</tr>")
                
                # Show first 10 units
                for idx, (unit_id, row) in enumerate(visible_df.iterrows()):
                    if idx >= 10:
                        html_lines.append(f"<tr><td colspan='{len(columns_to_show)+1}'><i>... and {len(visible_df)-10} more units</i></td></tr>")
                        break
                    
                    html_lines.append("<tr>")
                    html_lines.append(f"<td><b>{unit_id}</b></td>")
                    for col in columns_to_show:
                        value = row[col]
                        if isinstance(value, (int, np.integer)):
                            html_lines.append(f"<td>{value}</td>")
                        elif isinstance(value, (float, np.floating)):
                            html_lines.append(f"<td>{value:.3f}</td>")
                        else:
                            html_lines.append(f"<td>{value}</td>")
                    html_lines.append("</tr>")
                
                html_lines.append("</table>")
            else:
                html_lines.append("<p><i>No properties available</i></p>")
        
        # Update the text display
        html = "\n".join(html_lines)
        self.text_display.setHtml(html)
    
    def _qt_on_unit_visibility_changed(self):
        """
        Called when unit visibility changes.
        
        By default, this refreshes the view. You can override this
        for custom behavior or to optimize performance.
        """
        self.refresh()
    
    def _qt_on_manual_curation_updated(self):
        """
        Called when manual curation is updated (merge, split, etc.).
        
        Refresh the view to show updated unit information.
        """
        self.refresh()
    
    def _qt_on_unit_color_changed(self):
        """
        Called when unit colors change.
        
        Refresh to show updated colors.
        """
        self.refresh()
    
    def _qt_show_all_units(self):
        """Show all units in the dataset."""
        self.controller.set_visible_unit_ids(self.controller.unit_ids)
        self.notify_unit_visibility_changed()
    
    def _qt_hide_all_units(self):
        """Hide all units."""
        self.controller.set_all_unit_visibility_off()
        self.notify_unit_visibility_changed()
    
    ## Panel Backend Implementation (Optional) ##
    # 
    # If you want to support the Panel backend for web deployment,
    # implement these methods:
    #
    # def _panel_make_layout(self):
    #     """Create the Panel layout."""
    #     import panel as pn
    #     self.text_pane = pn.pane.HTML("")
    #     self.layout = pn.Column(self.text_pane)
    #
    # def _panel_refresh(self, **kwargs):
    #     """Refresh the Panel view."""
    #     # Similar to _qt_refresh but update Panel widgets
    #     pass

