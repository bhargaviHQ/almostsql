def format_table(rows, columns):
    if not rows:
        return "No results found"
    
    # Ensure rows is a list of tuples and columns is a list of column names
    if not isinstance(rows, list) or not all(isinstance(row, tuple) for row in rows) or not isinstance(columns, list):
        return "Unexpected result format"
    
    headers = columns
    formatted_rows = [list(row) for row in rows]
    
    # Calculate column widths
    col_widths = [max(len(str(row[i])) for row in [headers] + formatted_rows) for i in range(len(headers))]
    
    # Build table
    table = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+\n"
    table += "|" + "|".join(f" {h:<{w}} " for h, w in zip(headers, col_widths)) + "|\n"
    table += "+" + "+".join("-" * (w + 2) for w in col_widths) + "+\n"
    for row in formatted_rows:
        table += "|" + "|".join(f" {str(r):<{w}} " for r, w in zip(row, col_widths)) + "|\n"
    table += "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    return table