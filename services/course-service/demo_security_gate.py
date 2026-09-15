import ast


def parse_demo_value(value):
    """Parse a Python literal without executing arbitrary code."""
    return ast.literal_eval(value)
