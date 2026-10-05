import pandas as pd

from src.profiling.quality import profile_data_quality
from src.profiling.quality_guide import build_quality_guides


def test_quality_guide_only_returns_detected_issues():
    clean = pd.DataFrame({"Category": ["Retail", "Corporate"], "Sales": [100, 200]})
    guides = build_quality_guides(profile_data_quality(clean))
    assert guides == []


def test_quality_guide_explains_whitespace_and_method():
    df = pd.DataFrame({"Category": ["Retail", "Retail ", "Corporate"]})
    guides = build_quality_guides(profile_data_quality(df))
    whitespace = [g for g in guides if g["issue"] == "Text whitespace"]
    assert whitespace
    assert "false categories" in whitespace[0]["why"]
    assert "TRIM(text)" in whitespace[0]["method"]


def test_quality_guide_explains_missing_values_without_automating_imputation():
    df = pd.DataFrame({"Category": ["Retail", None, "Corporate"]})
    guides = build_quality_guides(profile_data_quality(df))
    missing = [g for g in guides if g["issue"] == "Missing values"]
    assert missing
    assert "Missing %" in missing[0]["method"]
    assert "does not guess" in missing[0]["fix"]


def test_quality_guide_explicitly_identifies_extra_trailing_space():
    df = pd.DataFrame({"Category": ["Retail", "Retail ", "Corporate"]})
    guides = build_quality_guides(profile_data_quality(df))
    whitespace = [g for g in guides if g["issue"] == "Text whitespace"][0]
    assert "extra space after" in whitespace["what"]
    assert "Retail `" in whitespace["what"]
