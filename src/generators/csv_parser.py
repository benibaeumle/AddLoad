"""CSV/XLSX parser: auto-detect and align uploaded measurement data."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from src.models.load_series import CSVParameters, MergeMode
from src.normalizer import Normalizer

_MAX_WARNING_BYTES = 50 * 1024 * 1024


def parse_upload(
    file_bytes: bytes,
    filename: str,
    target_year: int,
    bdew_profiles: dict | None = None,
) -> tuple[np.ndarray, CSVParameters, int]:
    """Parse a CSV or XLSX upload and align to the canonical time grid.

    Auto-detects encoding (UTF-8 → ISO-8859-1), separator (comma → semicolon),
    power column (first numeric column with values in [-10000, 10000] kW), and
    timestamp column. Falls back to assuming 15-min intervals from Jan 1 if no
    timestamp column is found.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Original filename (used to detect XLSX via extension).
        target_year: The target year for the canonical grid.
        bdew_profiles: Unused; kept for API consistency.

    Returns:
        Tuple of (aligned_values array of shape (35040,), CSVParameters, detected_year).

    Raises:
        ValueError: with German message if alignment fails (< 35040 rows after
                    resampling) or file cannot be parsed.
    """
    is_xlsx = filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls")

    if is_xlsx:
        df = _read_xlsx(file_bytes)
    else:
        df = _read_csv(file_bytes)

    ts_col, power_col = _detect_columns(df)

    if ts_col is not None:
        ts_series = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
        df.index = ts_series
        detected_year = ts_series.dropna().dt.year.mode()
        if len(detected_year) > 0:
            target_year = int(detected_year.iloc[0])
    else:
        n_rows = len(df)
        start = pd.Timestamp(f"{target_year}-01-01 00:00:00", tz="UTC")
        df.index = pd.date_range(start=start, periods=n_rows, freq="15min")

    power_series = pd.to_numeric(df[power_col], errors="coerce")
    power_series.index = df.index

    non_null_before = power_series.notna().sum()
    replaced_zeros = int((power_series.isna()).sum())

    try:
        aligned = Normalizer.align(power_series, target_year)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    replaced_zeros = int(np.sum(aligned == 0.0)) - int(np.sum(power_series.reindex(Normalizer.canonical_index(target_year)).fillna(0.0) == 0.0))
    replaced_zeros = max(0, replaced_zeros)

    params = CSVParameters(
        source_filenames=[filename],
        merge_mode=MergeMode.INDIVIDUAL,
        column_name=power_col,
        replaced_zeros=replaced_zeros,
    )
    return aligned, params, target_year


def _read_csv(file_bytes: bytes) -> pd.DataFrame:
    """Try to read CSV with various encodings and separators."""
    for encoding in ("utf-8", "utf-8-sig", "iso-8859-1"):
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    sep=sep,
                    encoding=encoding,
                    engine="python",
                )
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue

    for encoding in ("utf-8", "utf-8-sig", "iso-8859-1"):
        try:
            return pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                engine="python",
            )
        except Exception:
            continue

    raise ValueError(
        "Die CSV-Datei konnte nicht eingelesen werden. "
        "Bitte prüfen Sie Kodierung und Trennzeichen."
    )


def _read_xlsx(file_bytes: bytes) -> pd.DataFrame:
    """Read an XLSX file using openpyxl."""
    try:
        return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"Die XLSX-Datei konnte nicht eingelesen werden: {exc}") from exc


def _detect_columns(df: pd.DataFrame) -> tuple[str | None, str]:
    """Detect timestamp and power columns.

    Returns:
        (ts_col_name_or_None, power_col_name)
    """
    ts_col: str | None = None
    power_col: str | None = None

    for col in df.columns:
        if ts_col is None:
            try:
                numeric_check = pd.to_numeric(df[col], errors="coerce")
                if numeric_check.notna().sum() > len(df) * 0.9:
                    pass
                else:
                    parsed = pd.to_datetime(df[col], errors="coerce")
                    if parsed.notna().sum() > len(df) * 0.5:
                        ts_col = col
                        continue
            except Exception:
                pass

        if power_col is None:
            try:
                numeric = pd.to_numeric(df[col], errors="coerce")
                valid = numeric.dropna()
                if len(valid) > 0 and valid.between(-10000, 10000).mean() > 0.9:
                    power_col = col
            except Exception:
                pass

    if power_col is None:
        for col in df.columns:
            if col == ts_col:
                continue
            try:
                numeric = pd.to_numeric(df[col], errors="coerce")
                if numeric.notna().sum() > 0:
                    power_col = col
                    break
            except Exception:
                continue

    if power_col is None:
        raise ValueError(
            "Es wurde keine Leistungsspalte gefunden. "
            "Bitte stellen Sie sicher, dass die Datei numerische Leistungswerte in kW enthält."
        )

    return ts_col, str(power_col)
