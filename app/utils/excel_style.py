from openpyxl.utils import get_column_letter

def clone_row_styles(src_ws, dst_ws, src_row: int, dst_row: int, max_col: int):
    if src_row in src_ws.row_dimensions:
        dst_ws.row_dimensions[dst_row].height = src_ws.row_dimensions[src_row].height
    for col in range(1, max_col+1):
        c = get_column_letter(col)
        src_cell = src_ws[f"{c}{src_row}"]
        dst_cell = dst_ws[f"{c}{dst_row}"]
        if src_cell.has_style:
            dst_cell._style = src_cell._style
        dst_cell.number_format = src_cell.number_format
