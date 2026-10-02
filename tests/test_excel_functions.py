import pandas as pd

from src.analysis.excel_functions import generate_excel_function_recommendations


def test_excel_functions_are_dataset_aware():
    df = pd.DataFrame({
        "Customer ID": ["A", "B"],
        "Category": ["Tech", "Office"],
        "Sales": [100, 200],
    })
    fields = {
        "ids": ["Customer ID"],
        "dimensions": ["Category"],
        "measures": ["Sales"],
    }
    result = generate_excel_function_recommendations(df, fields)
    functions = " | ".join(result["Recommended Function"].tolist())
    assert "SUMIF" in functions
    assert "XLOOKUP" in functions
    assert "COUNTIF / COUNTIFS" in functions
