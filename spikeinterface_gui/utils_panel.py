import panel as pn

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



