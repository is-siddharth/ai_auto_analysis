from src.ingestion.loader import load_dataset


def test_load_superstore():

    file_path = "data/raw/Superstore.csv"

    df = load_dataset(file_path)

    assert df is not None
    assert len(df) > 0
    assert len(df.columns) > 0