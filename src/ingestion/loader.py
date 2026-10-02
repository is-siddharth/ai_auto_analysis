import os
import pandas as pd


def load_dataset(file_path):
    """
    Load a CSV or Excel file into a Pandas DataFrame.

    CSV files are tested against several common encodings.
    Excel files are loaded using pandas.read_excel().
    """

    file_extension = os.path.splitext(file_path)[1].lower()

    # ---------------------------------------------------------
    # Load file
    # ---------------------------------------------------------

    if file_extension == ".csv":

        encodings_to_try = [
            "utf-8",
            "utf-8-sig",
            "cp1252",
            "latin1"
        ]

        failed_encodings = []

        for encoding in encodings_to_try:

            try:

                df = pd.read_csv(
                    file_path,
                    encoding=encoding
                )

                break

            except UnicodeDecodeError:

                failed_encodings.append(encoding)

        else:

            raise UnicodeDecodeError(
                "unknown",
                b"",
                0,
                1,
                (
                    "Could not decode the CSV file. "
                    f"Encodings tried: {failed_encodings}"
                )
            )

    elif file_extension in [".xlsx", ".xls"]:

        df = pd.read_excel(file_path)

    else:

        raise ValueError(
            "Unsupported file format. "
            "Please provide a CSV or Excel file."
        )

    # ---------------------------------------------------------
    # Standardize known date columns
    # ---------------------------------------------------------

    date_columns = [
        "Order Date",
        "Ship Date"
    ]

    for column in date_columns:

        if column in df.columns:

            df[column] = pd.to_datetime(
                df[column],
                format="%d-%m-%Y",
                errors="coerce"
            )

    return df

def load_raw_dataset(file_path):
    """Load uploaded values without analytical date standardization."""
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == ".csv":
        for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode the CSV file with the supported encodings.")
    if file_extension in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)
    raise ValueError("Unsupported file format.")
