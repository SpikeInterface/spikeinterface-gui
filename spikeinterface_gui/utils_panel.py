from typing import TypedDict, NotRequired
import numpy as np

import panel as pn
from panel.param import param
from panel.custom import ReactComponent

from bokeh.models import ColumnDataSource, Patches, HTMLTemplateFormatter


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
        self.source = ColumnDataSource(data=dict(xs=[xs.tolist()], ys=[ys.tolist()]))
        self.circle = Patches(
            xs="xs", ys="ys", line_color=line_color, fill_color=fill_color, line_width=line_width, fill_alpha=fill_alpha
        )
        self.radius = radius
        self.center = (initial_x, initial_y)

    def update_position(self, x, y):
        # Update circle points
        xs = x + self.radius * np.cos(self.theta)
        ys = y + self.radius * np.sin(self.theta)
        self.source.data.update(dict(xs=[xs.tolist()], ys=[ys.tolist()]))
        self.center = (x, y)

    def update_radius(self, radius):
        self.radius = radius
        self.update_position(*self.center)

    def is_position_inside(self, x, y):
        # Check if position is inside the circle
        distance = np.sqrt((x - self.center[0]) ** 2 + (y - self.center[1]) ** 2)
        return distance <= self.radius

    def is_close_to_border(self, x, y):
        # Check if position is close to the border of the circle
        distance = np.sqrt((x - self.center[0]) ** 2 + (y - self.center[1]) ** 2)
        print(f"Distance to border: {distance} (radius: {self.radius})")
        return abs(distance - self.radius) < 5


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