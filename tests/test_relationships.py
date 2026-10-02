import pandas as pd

from src.profiling.relationships import (
    detect_date_relationships
)


def test_date_relationship_detection():

    df = pd.DataFrame({

        "In_Date": pd.to_datetime([
            "2025-01-01",
            "2025-01-05",
            "2025-01-10"
        ]),

        "Out_Date": pd.to_datetime([
            "2025-01-03",
            "2025-01-08",
            "2025-01-15"
        ])
    })


    result = detect_date_relationships(
        df
    )


    assert not result.empty


    assert (
        result.iloc[0][
            "Start Column"
        ]
        == "In_Date"
    )


    assert (
        result.iloc[0][
            "End Column"
        ]
        == "Out_Date"
    )


    assert (
        result.iloc[0][
            "Violations"
        ]
        == 0
    )


def test_camel_case_date_relationship_detection():

    df = pd.DataFrame({

        "AdmitDate": pd.to_datetime([
            "2025-01-01",
            "2025-01-05"
        ]),

        "DischargeDate": pd.to_datetime([
            "2025-01-03",
            "2025-01-08"
        ])
    })


    result = detect_date_relationships(
        df
    )


    assert not result.empty

    assert (
        result.iloc[0][
            "Start Column"
        ]
        == "AdmitDate"
    )

    assert (
        result.iloc[0][
            "End Column"
        ]
        == "DischargeDate"
    )

    assert (
        result.iloc[0][
            "Violations"
        ]
        == 0
    )
