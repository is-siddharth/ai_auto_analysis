import pandas as pd

from src.analysis.kpis import calculate_kpi, generate_kpi_recommendations


def test_kpis_distinguish_ids_from_measures():
    df = pd.DataFrame({
        "Employee ID": [1, 2, 2, 3],
        "Salary": [10, 20, 20, 30],
        "Department": ["A", "A", "B", "B"],
    })
    fields = {
        "ids": ["Employee ID"],
        "measures": ["Salary"],
        "dimensions": ["Department"],
    }
    result = generate_kpi_recommendations(df, fields)
    assert "Total Employees" in result["KPI"].tolist()
    assert "Total Salary" in result["KPI"].tolist()
    assert "SUM(Employee ID)" not in result["Formula Logic"].tolist()


def test_profit_margin_is_only_created_when_supported():
    df = pd.DataFrame({"Sales": [100, 200], "Profit": [10, 20]})
    fields = {"measures": ["Sales", "Profit"]}
    result = generate_kpi_recommendations(df, fields)
    assert "Profit Margin" in result["KPI"].tolist()


def test_selected_kpi_is_calculated_from_data():
    df = pd.DataFrame({"Employee ID": [1, 2, 2, 3], "Salary": [10, 20, 20, 30]})
    fields = {"ids": ["Employee ID"], "measures": ["Salary"]}
    recommendations = generate_kpi_recommendations(df, fields)

    employee_kpi = recommendations.loc[recommendations["KPI"] == "Total Employees"].iloc[0]
    salary_kpi = recommendations.loc[recommendations["KPI"] == "Total Salary"].iloc[0]

    assert calculate_kpi(df, employee_kpi)["Value"] == 3
    assert calculate_kpi(df, salary_kpi)["Value"] == 80


def test_profit_margin_is_calculated_as_ratio():
    df = pd.DataFrame({"Sales": [100, 200], "Profit": [10, 20]})
    recommendations = generate_kpi_recommendations(df, {"measures": ["Sales", "Profit"]})
    margin = recommendations.loc[recommendations["KPI"] == "Profit Margin"].iloc[0]

    assert calculate_kpi(df, margin)["Value"] == 0.1
