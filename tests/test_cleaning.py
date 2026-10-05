import pandas as pd

from src.profiling.cleaning import (
    apply_cleaning_actions,
    automated_cleaning_action_ids,
    recommend_cleaning_actions,
)


def test_cleaning_recommends_safe_actions_without_modifying_input():
    df = pd.DataFrame(
        {
            "ID": [1, 1, 2, 3],
            "Segment": ["Retail ", "Retail ", "Corporate", "   "],
            "Sales": [100, 100, 200, None],
        }
    )
    original = df.copy(deep=True)

    recommendations = recommend_cleaning_actions(df)

    assert "remove_exact_duplicates" in recommendations["Action ID"].tolist()
    assert "trim_whitespace::Segment" in recommendations["Action ID"].tolist()
    assert "blank_text_to_missing::Segment" in recommendations["Action ID"].tolist()
    pd.testing.assert_frame_equal(df, original)


def test_apply_cleaning_actions_changes_only_approved_items():
    df = pd.DataFrame(
        {
            "ID": [1, 1, 2],
            "Segment": ["Retail ", "Retail ", "Corporate"],
            "Sales": [100, 100, 200],
        }
    )
    recommendations = recommend_cleaning_actions(df)

    cleaned, audit = apply_cleaning_actions(
        df,
        recommendations,
        ["trim_whitespace::Segment"],
    )

    assert len(cleaned) == 3
    assert cleaned.loc[0, "Segment"] == "Retail"
    assert len(audit) == 1


def test_automated_mode_only_selects_high_confidence_safe_actions():
    df = pd.DataFrame(
        {
            "ID": [1, 1],
            "Segment": ["Retail ", "Retail "],
        }
    )
    recommendations = recommend_cleaning_actions(df)
    selected = automated_cleaning_action_ids(recommendations)

    assert "remove_exact_duplicates" in selected
    assert "trim_whitespace::Segment" in selected
