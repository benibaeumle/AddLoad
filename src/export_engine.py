"""ExportEngine: produces wide-format CSV bytes and project JSON bytes."""

from __future__ import annotations

import io

from src.aggregator import AggregationResult
from src.models.project import Project
from src.services.project_service import ProjectService


class ExportEngine:
    """Produces export artifacts for download via st.download_button."""

    @staticmethod
    def to_csv_bytes(result: AggregationResult) -> bytes:
        """Produce UTF-8 with BOM semicolon-delimited CSV bytes.

        Format:
        - Delimiter: ;
        - Timestamp column: ISO 8601 UTC (e.g. 2024-01-01T00:00:00Z)
        - 35040 data rows + 1 header row
        - No empty cells; missing values are 0.0
        - Encoding: UTF-8 with BOM for Excel compatibility

        Args:
            result: AggregationResult with a DataFrame indexed by canonical
                    DatetimeIndex.

        Returns:
            UTF-8 BOM CSV bytes.
        """
        df = result.df.copy()
        df = df.fillna(0.0)

        ts_strings = df.index.strftime("%Y-%m-%dT%H:%M:%SZ")

        buf = io.StringIO()
        buf.write("\ufeff")

        headers = ["timestamp"] + list(df.columns)
        buf.write(";".join(str(h) for h in headers) + "\n")

        for i, ts in enumerate(ts_strings):
            row_vals = [ts] + [f"{df.iloc[i, j]:.6f}" for j in range(df.shape[1])]
            buf.write(";".join(row_vals) + "\n")

        return buf.getvalue().encode("utf-8")

    @staticmethod
    def to_json_bytes(project: Project) -> bytes:
        """Serialize the project to UTF-8 JSON bytes.

        Args:
            project: The project to serialize.

        Returns:
            UTF-8 JSON bytes.

        Raises:
            ValueError: (German message) if project validation fails.
        """
        errors = ProjectService.validate_for_export(project)
        if errors:
            raise ValueError("\n".join(errors))

        json_str = ProjectService.to_json(project)
        return json_str.encode("utf-8")
