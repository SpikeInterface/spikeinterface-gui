from typing import TypedDict, Callable
# For Python < 3.11 compatibility
try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

import numpy as np
import time
import panel as pn

pn.extension("tabulator")

from panel.param import param
from panel.custom import ReactComponent
from panel.widgets import Tabulator

from bokeh.models import ColumnDataSource, Patches, HTMLTemplateFormatter

from .view_base import ViewBase



_bg_color = "#181818"


table_stylesheet = """
.bk-data-table {
    background-color: #000000 !important;
    color: #ffffff !important;
    border-color: #333333 !important;
    font-size: 14px !important;
}
.slick-header-columns, .slick-header-column {
    background-color: #1a1a1a !important;
    color: #ffffff !important;
    border-color: #333333 !important;
    font-size: 14px !important;
    font-weight: bold !important;
}
.slick-cell {
    background-color: #000000 !important;
    color: #ffffff !important;
    border-color: #333333 !important;
    font-size: 14px !important;
    line-height: 25px !important;
}
.slick-cell.selected, .slick-cell.active {
    background-color: #2b2b2b !important;
}
.slick-row.odd {
    background-color: #0a0a0a !important;
}
.slick-row.even {
    background-color: #000000 !important;
}
.slick-row:hover {
    background-color: #1a1a1a !important;
}
"""

unit_formatter = HTMLTemplateFormatter(
    template="""
    <div style="color: <%= value ? value.color : '#ffffff' %>;">
        ● <%= value ? value.id : '' %>
    </div>
"""
)

spike_formatter = HTMLTemplateFormatter(
        template="""
        <div style="background-color: <%= value ? value.color : 'transparent' %>; 
                    padding: 2px 5px;
                    border-radius: 3px;
                    color: #ffffff;
                    text-align: center;">
            <%= value ? value.id : '' %>
        </div>
    """
    )

# TODO: fix this (maybe using a Tabulator)
checkbox_formatter_template = """
<input type="checkbox" <%= value ? 'checked' : '' %> onclick="
    var indices = source.selected.indices;
    var idx = cb_obj.parentElement.parentElement.rowIndex - 1;
    if (cb_obj.checked) {
        if (!indices.includes(idx)) indices.push(idx);
    } else {
        var index = indices.indexOf(idx);
        if (index > -1) indices.splice(index, 1);
    }
    source.selected.indices = indices;
    source.change.emit();
">
"""


def insert_warning(view, warning_msg):
    clear_warning(view)
    alert_html = f"""
    <div style="padding: 15px; margin-bottom: 20px; border: 1px solid #d4ac0d; 
                border-radius: 4px; background-color: #fcf3cf; color: #7d6608;
                font-weight: bold; text-align: center; width: 100%;">
        ⚠️ {warning_msg}
    </div>
    """
    view.layout.insert(0, pn.pane.HTML(alert_html))

def clear_warning(view):
    for item in view.layout:
        if isinstance(item, pn.pane.HTML) and "⚠️" in str(item.object):
            view.layout.remove(item)


def slow_lasso(source, callback):
    """
    Implements a slow lasso selection that only triggers a callback every 100ms.

    source: ColumnDataSource
        The source to which the lasso selection is applied.
    callback: function
        The function to trigger on lasso selection.
    """
    from bokeh.models import CustomJS
    # Helper source to trigger Python callback
    trigger_source = ColumnDataSource(data=dict(trigger=[0]))
    callback_code = """
    if (window._lasso_timeout) {
        clearTimeout(window._lasso_timeout);
    }
    window._lasso_timeout = setTimeout(() => {
        // Replace trigger_source data to force Python-side update
        trigger_source.data = {trigger: [Math.random()]};
    }, 100);
    """
    source.selected.js_on_change('indices', CustomJS(args=dict(trigger_source=trigger_source), code=callback_code))
    trigger_source.on_change('data', callback)


class CustomCircle:
    """
    Create a custom circle glyph with draggable center and radius.
    """

    def __init__(
        self,
        initial_x=0,
        initial_y=0,
        radius=50,
        num_points_theta=50,
        line_color="#7F7F0C",
        fill_color=None,
        fill_alpha=0.1,
        line_width=2,
    ):
        self.theta = np.linspace(0, 2 * np.pi, num_points_theta)
        xs = initial_x + radius * np.cos(self.theta)
        ys = initial_y + radius * np.sin(self.theta)

        # Calculate diamond position at 45 degrees
        diamond_angle = np.pi / 4  # 45 degrees
        diamond_x = initial_x + radius * np.cos(diamond_angle)
        diamond_y = initial_y + radius * np.sin(diamond_angle)
        diamond_points = self._get_diamond_points(diamond_x, diamond_y)

        self.source = ColumnDataSource(data=dict(
            xs=[xs.tolist()], 
            ys=[ys.tolist()],
            diamond_xs=[diamond_points[0]],
            diamond_ys=[diamond_points[1]]
        ))

        self.circle = Patches(
            xs="xs", ys="ys", line_color=line_color, fill_color=fill_color, line_width=line_width, fill_alpha=fill_alpha
        )
        self.diamond = Patches(
            xs="diamond_xs", ys="diamond_ys", line_color=line_color, fill_color=line_color, line_width=line_width
        )

        self.radius = radius
        self.center = (initial_x, initial_y)

    def add_to_figure(self, figure):
        figure.add_glyph(self.source, self.circle)
        figure.add_glyph(self.source, self.diamond)

    def _get_diamond_points(self, x, y, size=4):
        # Generate diamond points around center (x,y)
        diamond_xs = [x, x + size/2, x, x - size/2]
        diamond_ys = [y + size/2, y, y - size/2, y]
        return [diamond_xs], [diamond_ys]

    def update_position(self, x, y, start_x=None, start_y=None):
        """
        Update the position of the circle and diamond based on the new center coordinates.
        If start_x and start_y are provided, they are used as anchor points for the circle.
        Otherwise, the center of the circle is used as the anchor point.
        """
        if start_x is not None and start_y is not None:
            # Calculate the new center based on the anchor point
            anchor_x = start_x - self.center[0]
            anchor_y = start_y - self.center[1]
        else:
            # Use the current center as the anchor point
            anchor_x = 0
            anchor_y = 0

        # Update circle points
        new_x = x - anchor_x
        new_y = y - anchor_y
        xs = new_x + self.radius * np.cos(self.theta)
        ys = new_y + self.radius * np.sin(self.theta)

        # Update diamond position
        diamond_angle = np.pi / 4  # 45 degrees
        diamond_x = new_x + self.radius * np.cos(diamond_angle)
        diamond_y = new_y + self.radius * np.sin(diamond_angle)
        diamond_points = self._get_diamond_points(diamond_x, diamond_y)

        self.source.data.update(dict(
            xs=[xs.tolist()], 
            ys=[ys.tolist()],
            diamond_xs=diamond_points[0],
            diamond_ys=diamond_points[1]
        ))
        self.center = (new_x, new_y)

    def update_radius(self, radius):
        self.radius = radius
        self.update_position(*self.center)

    def is_position_inside(self, x, y, skip_other_positions=None, skip_distance=5):
        """
        Check if the given position (x, y) is inside the circle.
        If skip_other_positions is provided, check if the position is close to any of them
        usinf the skip_distance.
        """
        # Check if position is inside the circle
        distance = np.sqrt((x - self.center[0]) ** 2 + (y - self.center[1]) ** 2)
        isin = distance <= self.radius
        if skip_other_positions is not None:
            for pos in skip_other_positions:
                dist = np.sqrt((x - pos[0]) ** 2 + (y - pos[1]) ** 2)
                if dist < skip_distance:
                    return False
        return isin

    def is_close_to_border(self, x, y):
        # Check if position is close to the border of the circle
        distance = np.sqrt((x - self.center[0]) ** 2 + (y - self.center[1]) ** 2)
        return abs(distance - self.radius) < 5

    def is_close_to_diamond(self, x, y, threshold=5):
        # Calculate diamond center position
        diamond_angle = np.pi / 4  # 45 degrees
        diamond_x = self.center[0] + self.radius * np.cos(diamond_angle)
        diamond_y = self.center[1] + self.radius * np.sin(diamond_angle)

        # Calculate distance to diamond center
        distance = np.sqrt((x - diamond_x) ** 2 + (y - diamond_y) ** 2)
        return distance < threshold + self.radius * 0.1  # Add diamond size to threshold

    def select(self):
        """Make the circle and diamond borders dashed."""
        self.circle.line_dash = [6]
        self.diamond.line_dash = [6]

    def unselect(self):
        """Make the circle and diamond borders solid."""
        self.circle.line_dash = []
        self.diamond.line_dash = []


class SelectableTabulator(pn.viewable.Viewer):
    """
    A Tabulator that allows for selection of rows and cells.

    This class extends the Tabulator class and adds functionality for keyboard shortcuts and click events:
    - Keyboard shortcuts for selecting the first, last, next, and previous rows.
    - Click events for selecting rows and cells.
    - Double-click and ctrl-click events for selecting single rows (with callback)

    Supports custom column callbacks for specific columns and conditional shortcuts.

    Parameters
    ----------
    *args, **kwargs
        Arguments passed to the Tabulator constructor.
    parent_view: ViewBase | None
        The parent view that will be notified of selection changes.
    refresh_table_function: Callable | None
        A function to call when the table a new selection is made via keyboard shortcuts.
    on_only_function: Callable | None
        A function to call when the table a ctrl+selection is made via keyboard shortcuts or a double-click.
    conditional_shortcut: Callable | None
        A function that returns True if the shortcuts should be enabled, False otherwise.
    column_callbacks: dict[Callable] | None
        A dictionary of column names and their corresponding callback functions.
        This function should take the row argument.
    """
    def __init__(
        self, 
        *args,
        skip_sort_columns: list[str] = [],
        parent_view: ViewBase | None = None,
        refresh_table_function: Callable | None = None,
        on_only_function: Callable | None = None,
        conditional_shortcut: Callable | None = None,
        column_callbacks: dict[str, Callable] | None = None,
        **kwargs
    ):
        self._formatters = kwargs.get("formatters", {})
        self._editors = kwargs.get("editors", {})
        self._frozen_columns = kwargs.get("frozen_columns", [])
        if "sortable" in kwargs:
            self._sortable = kwargs.pop("sortable")
        else:
            self._sortable = True
        # disable frontend sorting
        value = args[0] if len(args) > 0 else kwargs.get("value")
        columns = [
            {"title": k, "field": k, "headerSort": False} for k in value.columns
        ]
        self.tabulator = Tabulator(*args, **kwargs, configuration={"columns": columns})
        self._original_value = self.tabulator.value.copy()
        self.tabulator.formatters = self._formatters        
        self.tabulator.on_click(self._on_click)
        super().__init__()
        self.original_indices = self.value.index.values
   
        self._parent_view = parent_view
        self._refresh_table_function = refresh_table_function
        self._on_only_function = on_only_function
        self._conditional_shortcut = conditional_shortcut if conditional_shortcut is not None else lambda: True
        self._column_callbacks = column_callbacks if column_callbacks is not None else {}

        self._last_selected_row = None
        self._last_clicked = None
        self._selection = []
        shortcuts = [
            KeyboardShortcut(name="first", key="Home", shiftKey=False),
            KeyboardShortcut(name="last", key="End", shiftKey=False),
            KeyboardShortcut(name="next", key="ArrowDown", ctrlKey=False),
            KeyboardShortcut(name="previous", key="ArrowUp", ctrlKey=False),
            KeyboardShortcut(name="next_only", key="ArrowDown", ctrlKey=True),
            KeyboardShortcut(name="previous_only", key="ArrowUp", ctrlKey=True),
            KeyboardShortcut(name="append_next", key="ArrowDown", shiftKey=True),
            KeyboardShortcut(name="append_previous", key="ArrowUp", shiftKey=True),
        ]
        self.shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
        self.shortcuts_component.on_msg(self._handle_shortcut)

        if self._sortable:
            # make a dropdown with the columns
            columns = list(self.tabulator.value.columns)
            columns = [col for col in columns if col not in skip_sort_columns]
            self.sort_dropdown = pn.widgets.Select(
                name="Sort by",
                options=["-"] + columns,
                value="-",
                sizing_mode="stretch_width",
            )
            self.direction_dropdown = pn.widgets.Select(
                name="Direction",
                options=["↑", "↓"],
                value="↓",
                sizing_mode="stretch_width",
            )
            sort_row = pn.Row(
                self.sort_dropdown,
                self.direction_dropdown,
                sizing_mode="stretch_width",
            )
            components = [self.shortcuts_component, sort_row, self.tabulator]
            self.sort_dropdown.param.watch(self._on_sort_change, "value")
            self.direction_dropdown.param.watch(self._on_sort_change, "value")
        else:
            components = [self.shortcuts_component, self.tabulator]

        self._layout = pn.Column(
            *components,
            sizing_mode="stretch_width"
        )

    @property
    def selection(self):
        return self.tabulator.selection

    @selection.setter
    def selection(self, val):
        self.tabulator.selection = val

    @property
    def param(self):
        return self.tabulator.param

    @property
    def sorters(self):
        return self.tabulator.sorters

    @sorters.setter
    def sorters(self, val):
        self.tabulator.sorters = []

    @property
    def value(self):
        self.tabulator.sorters = []
        return self.tabulator.value


    @value.setter
    def value(self, val):
        self.tabulator.formatters = self._formatters
        self.tabulator.editors = self._editors
        self.tabulator.frozen_columns = self._frozen_columns
        self.tabulator.sorters = []
        self.tabulator.value = val

    def __panel__(self):
        return self._layout

    def reset(self):
        """
        Reset the table to its original state.
        """
        self.tabulator.value = self._original_value
        self.tabulator.selection = []
        self._last_selected_row = None
        self._last_clicked = None
        self.tabulator.sorters = []
        self.selection = []

    def _on_sort_change(self, event):
        """
        Handle the sort change event. This is called when the sort dropdown is changed.
        """
        self.tabulator.sorters = []
        if self.sort_dropdown.value == "-":
            # sort by index
            df = self._original_value
        else:
            if self.sort_dropdown.value == self.tabulator.value.index.name:
                df = self.tabulator.value.sort_index(
                    ascending=(self.direction_dropdown.value == "↑")
                )
            else:
                df = self.tabulator.value.sort_values(
                    by=self.sort_dropdown.value,
                    ascending=(self.direction_dropdown.value == "↑")
                )
        self.tabulator.value = df

    def _on_click(self, event):
        """
        Handle the selection change event. This is called when a row or cell is clicked.
        """
        self.tabulator.sorters = []
        row = event.row
        col = event.column
        time_clicked = time.perf_counter()
        double_clicked = False
        if self._last_clicked is not None:
            if (time_clicked - self._last_clicked) < 0.8 and self._last_selected_row == row:
                double_clicked = True
                self.selection = [row]
                if self._on_only_function is not None:
                    self._on_only_function()
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
        if not double_clicked:
            current_selection = self.selection
            if row in current_selection:
                current_selection.remove(row)
            else:
                current_selection.append(row)
            self.selection = current_selection

            if col in self._column_callbacks:
                callback = self._column_callbacks[col]
                if callable(callback):
                    callback(row)

        self._last_selected_row = row
        self._last_clicked = time_clicked

        if self._parent_view is not None:
            self._parent_view.notify_active_view_updated()

    def _get_next_row(self):
        selected_rows = self.selection
        if len(selected_rows) == 0:
            next_row = 0
        else:
            if self._last_selected_row is not None:
                next_row = self._last_selected_row + 1
            else:
                next_row = max(selected_rows) + 1
        next_row = min(next_row, len(self.value) - 1)
        return next_row

    def _get_previous_row(self):
        selected_rows = self.selection
        if len(selected_rows) == 0:
            previous_row = len(self.value) - 1
        else:
            if self._last_selected_row is not None:
                previous_row = self._last_selected_row  - 1
            else:
                previous_row = min(selected_rows) - 1
        previous_row = max(0, previous_row)
        return previous_row

    def _handle_shortcut(self, event):
        if self._conditional_shortcut():
            if event.data == "first":
                first_row = 0
                self.selection = [first_row]
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = first_row
            elif event.data == "last":
                last_row = len(self.value) - 1
                self.selection = [last_row]
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = last_row
            elif event.data == "next":
                next_row = self._get_next_row()
                self.selection = [next_row]
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = next_row
            elif event.data == "previous":
                previous_row = self._get_previous_row()
                self.selection = [previous_row]
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = previous_row
            elif event.data == "next_only":
                next_row = self._get_next_row()
                # this should go in self._on_only_function()
                self.selection = [next_row]
                # self.notify_unit_visibility_changed()
                if self._on_only_function is not None:
                    self._on_only_function()
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = next_row
            elif event.data == "previous_only":
                previous_row = self._get_previous_row()
                self.selection = [previous_row]
                if self._on_only_function is not None:
                    self._on_only_function()
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = previous_row
            elif event.data == "append_next":
                next_row = self._get_next_row()
                current_row = self._last_selected_row
                current_selection = list(self.selection)
                if next_row not in self.selection:
                    current_selection.append(next_row)
                elif current_row in self.selection:
                    current_selection.remove(current_row)
                self.selection = current_selection
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = next_row
            elif event.data == "append_previous":
                previous_row = self._get_previous_row()
                current_row = self._last_selected_row
                current_selection = list(self.selection)
                if previous_row not in self.selection:
                    current_selection.append(previous_row)
                elif current_row in self.selection:
                    current_selection.remove(current_row)
                self.selection = current_selection
                if self._refresh_table_function is not None:
                    self._refresh_table_function()
                self._last_selected_row = previous_row


# Shortcut handler, taken from https://github.com/holoviz/panel/issues/3193#issuecomment-2357189979
class KeyboardShortcut(TypedDict):
    name: str
    key: str
    altKey: NotRequired[bool]
    ctrlKey: NotRequired[bool]
    metaKey: NotRequired[bool]
    shiftKey: NotRequired[bool]


class KeyboardShortcuts(ReactComponent):
    """
    Class to install global keyboard shortcuts into a Panel app.

    Pass in shortcuts as a list of KeyboardShortcut dictionaries, and then handle shortcut events in Python
    by calling `on_msg` on this component. The `name` field of the matching KeyboardShortcut will be sent as the `data`
    field in the `DataEvent`.

    Example:
    >>> shortcuts = [
        KeyboardShortcut(name="save", key="s", ctrlKey=True),
        KeyboardShortcut(name="print", key="p", ctrlKey=True),
    ]
    >>> shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
    >>> def handle_shortcut(event: DataEvent):
            if event.data == "save":
                print("Save shortcut pressed!")
            elif event.data == "print":
                print("Print shortcut pressed!")
    >>> shortcuts_component.on_msg(handle_shortcut)
    """
    _model_name = "KeyboardShortcuts"
    _model_module = "keyboard_shortcuts"
    _model_module_version = "0.0.1"

    shortcuts = param.List(item_type=dict)

    _esm = """
    // Hash a shortcut into a string for use in a dictionary key (booleans / null / undefined are coerced into 1 or 0)
    function hashShortcut({ key, altKey, ctrlKey, metaKey, shiftKey }) {
      return `${key}.${+!!altKey}.${+!!ctrlKey}.${+!!metaKey}.${+!!shiftKey}`;
    }

    export function render({ model }) {
      const [shortcuts] = model.useState("shortcuts");

      const keyedShortcuts = {};
      for (const shortcut of shortcuts) {
        // For shortcuts that use ctrlKey, also register them with metaKey
        if (shortcut.ctrlKey) {
          const metaShortcut = {...shortcut, ctrlKey: false, metaKey: true};
          keyedShortcuts[hashShortcut(metaShortcut)] = shortcut.name;
        }
        keyedShortcuts[hashShortcut(shortcut)] = shortcut.name;
      }

      function onKeyDown(e) {
        console.log(e);
        const name = keyedShortcuts[hashShortcut(e)];
        if (name) {
          e.preventDefault();
          e.stopPropagation();
          model.send_msg(name);
          return;
        }
      }

      React.useEffect(() => {
        window.addEventListener('keydown', onKeyDown);
        return () => {
          window.removeEventListener('keydown', onKeyDown);
        };
      });

      return <></>;
    }
    """
