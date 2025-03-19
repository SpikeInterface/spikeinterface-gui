import numpy as np

import panel as pn

from bokeh.models import ColumnDataSource, Patches



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


