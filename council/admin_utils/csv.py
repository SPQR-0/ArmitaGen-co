def safe_csv(value):
    """Prevent CSV injection (Excel formula injection protection)."""
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value
