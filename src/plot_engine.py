"""PlotEngine: builds the Plotly figure for the annual load curve chart."""

from __future__ import annotations

import hashlib
import json

import plotly.graph_objects as go

from src.aggregator import AggregationResult
from src.models.project import StaticLimits

_CATEGORY_COLS = ["CSV_SUM", "SLP_SUM", "PS_SUM", "PVA_SUM", "BESS_SUM", "TOTAL"]

_COLORS = {
    "CSV_SUM": "#1f77b4",
    "SLP_SUM": "#ff7f0e",
    "PS_SUM": "#2ca02c",
    "PVA_SUM": "#d62728",
    "BESS_SUM": "#9467bd",
    "TOTAL": "#000000",
}


class PlotEngine:
    """Builds the Plotly figure for the annual P(t) load chart."""

    @staticmethod
    def build_figure(
        result: AggregationResult,
        limits: StaticLimits,
        visible: dict[str, bool],
    ) -> go.Figure:
        """Build a Plotly figure from an AggregationResult.

        Individual series are hidden by default; category sums and TOTAL are
        visible. Visibility is overridden by the ``visible`` dict.

        Args:
            result: The aggregation result containing the DataFrame.
            limits: Static power limits to draw as dashed horizontal lines.
            visible: Dict mapping column names to bool visibility state.

        Returns:
            A go.Figure ready for st.plotly_chart.
        """
        fig = go.Figure()
        df = result.df

        individual_cols = [c for c in df.columns if c not in _CATEGORY_COLS]
        agg_cols = [c for c in _CATEGORY_COLS if c in df.columns]

        x = df.index

        for col in individual_cols:
            vis = True if visible.get(col, False) else False
            fig.add_trace(
                go.Scattergl(
                    x=x,
                    y=df[col].to_numpy(),
                    name=col,
                    mode="lines",
                    visible=vis,
                    line=dict(width=1),
                )
            )

        for col in agg_cols:
            default_vis = True
            vis = visible.get(col, default_vis)
            if isinstance(vis, bool):
                vis = True if vis else "legendonly"
            width = 2 if col != "TOTAL" else 3
            color = _COLORS.get(col)
            line_kwargs = dict(width=width)
            if color:
                line_kwargs["color"] = color
            fig.add_trace(
                go.Scattergl(
                    x=x,
                    y=df[col].to_numpy(),
                    name=col,
                    mode="lines",
                    visible=vis,
                    line=line_kwargs,
                )
            )

        shapes = []
        annotations = []

        limit_defs = [
            ("Sicherung", limits.sicherung_kw, "red"),
            ("Hausanschluss", limits.hausanschluss_kw, "orange"),
            ("Trafo", limits.trafo_kw, "purple"),
        ]
        for label, value, color in limit_defs:
            if value is not None:
                shapes.append(
                    go.layout.Shape(
                        type="line",
                        x0=0,
                        x1=1,
                        xref="paper",
                        y0=value,
                        y1=value,
                        line=dict(dash="dash", color=color, width=1.5),
                    )
                )
                annotations.append(
                    go.layout.Annotation(
                        x=0.01,
                        y=value,
                        xref="paper",
                        yref="y",
                        text=f"{label}: {value:.0f} kW",
                        showarrow=False,
                        font=dict(color=color, size=11),
                        xanchor="left",
                    )
                )

        nonzero_mask = (df != 0).any(axis=1)
        if nonzero_mask.any():
            x_min = df.index[nonzero_mask.values.argmax()].isoformat()
            x_max = df.index[len(nonzero_mask) - 1 - nonzero_mask.values[::-1].argmax()].isoformat()
        else:
            x_min = df.index[0].isoformat()
            x_max = df.index[-1].isoformat()

        vis_hash = hashlib.md5(
            json.dumps(sorted(visible.items()), sort_keys=True).encode()
        ).hexdigest()[:8]

        fig.update_layout(
            uirevision=f"{x_min}_{x_max}_{vis_hash}",
            xaxis_title="Zeit (UTC)",
            xaxis_range=[x_min, x_max],
            yaxis_title="Leistung (kW)",
            legend=dict(orientation="v", x=1.01),
            shapes=shapes,
            annotations=annotations,
            margin=dict(l=60, r=160, t=40, b=60),
            hovermode="x unified",
        )

        return fig
