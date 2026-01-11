"""
Visualization Generator
Creates Chart.js compatible configurations from query results
"""

from typing import Any

from .models.state import VisualizationConfig, VisualizationType

# Default color palette
DEFAULT_COLORS = [
    "rgba(79, 70, 229, 0.8)",  # Indigo
    "rgba(16, 185, 129, 0.8)",  # Emerald
    "rgba(245, 158, 11, 0.8)",  # Amber
    "rgba(239, 68, 68, 0.8)",  # Red
    "rgba(139, 92, 246, 0.8)",  # Violet
    "rgba(20, 184, 166, 0.8)",  # Teal
    "rgba(249, 115, 22, 0.8)",  # Orange
    "rgba(236, 72, 153, 0.8)",  # Pink
    "rgba(59, 130, 246, 0.8)",  # Blue
    "rgba(34, 197, 94, 0.8)",  # Green
]

BORDER_COLORS = [
    "rgba(79, 70, 229, 1)",
    "rgba(16, 185, 129, 1)",
    "rgba(245, 158, 11, 1)",
    "rgba(239, 68, 68, 1)",
    "rgba(139, 92, 246, 1)",
    "rgba(20, 184, 166, 1)",
    "rgba(249, 115, 22, 1)",
    "rgba(236, 72, 153, 1)",
    "rgba(59, 130, 246, 1)",
    "rgba(34, 197, 94, 1)",
]


class VisualizationGenerator:
    """Generates Chart.js compatible visualization configurations"""

    @staticmethod
    def generate_config(
        data: list[dict[str, Any]], chart_type: VisualizationType, config: VisualizationConfig
    ) -> dict[str, Any]:
        """
        Generate a complete Chart.js configuration.

        Args:
            data: Query result data
            chart_type: Type of visualization
            config: Visualization configuration with axes and options

        Returns:
            Chart.js compatible configuration object
        """
        if not data:
            return VisualizationGenerator._empty_chart(config)

        x_field = config.get("x_axis", "")
        y_field = config.get("y_axis", "")
        title = config.get("title", "Query Results")
        format_type = config.get("format_type", "number")

        # Extract y_axes for multi-series, or use single y_axis
        y_fields = config.get("y_axes", [y_field] if y_field else [])

        if chart_type == VisualizationType.BAR_CHART:
            return VisualizationGenerator._bar_chart(data, x_field, y_fields, title, format_type)
        elif chart_type == VisualizationType.LINE_CHART:
            return VisualizationGenerator._line_chart(data, x_field, y_fields, title, format_type)
        elif chart_type == VisualizationType.PIE_CHART:
            return VisualizationGenerator._pie_chart(
                data, x_field, y_fields[0] if y_fields else "", title
            )
        elif chart_type == VisualizationType.STACKED_BAR:
            return VisualizationGenerator._stacked_bar(data, x_field, y_fields, title, format_type)
        elif chart_type == VisualizationType.MULTI_SERIES:
            return VisualizationGenerator._multi_series(data, x_field, y_fields, title, format_type)
        elif chart_type == VisualizationType.HEATMAP:
            return VisualizationGenerator._heatmap(data, x_field, y_fields, title)
        elif chart_type == VisualizationType.AREA_CHART:
            return VisualizationGenerator._area_chart(data, x_field, y_fields, title, format_type)
        else:
            # TABLE or unknown - return data as-is
            return VisualizationGenerator._table_config(data, title)

    @staticmethod
    def _empty_chart(config: VisualizationConfig) -> dict[str, Any]:
        """Generate config for empty data"""
        return {
            "type": "bar",
            "data": {"labels": [], "datasets": []},
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {"display": True, "text": config.get("title", "No Data Available")}
                },
            },
        }

    @staticmethod
    def _bar_chart(
        data: list[dict], x_field: str, y_fields: list[str], title: str, format_type: str
    ) -> dict[str, Any]:
        """Generate bar chart configuration"""
        if not data or not x_field:
            # Fallback to simple labels if no data or no x_field
            labels = [f"Item {i+1}" for i in range(len(data))] if data else []
        else:
            # Check if we have duplicate x_field values - if so, combine with other categorical fields
            try:
                x_values = [row.get(x_field, "") for row in data]
                has_duplicates = len(x_values) != len(set(x_values))
                
                if has_duplicates and data and len(data) > 0:
                    # Find additional categorical fields to combine (exclude numeric and the x_field itself)
                    all_keys = set(data[0].keys()) if data[0] else set()
                    numeric_fields = {y for y in y_fields}
                    categorical_fields = [
                        k for k in all_keys 
                        if k != x_field and k not in numeric_fields and k not in ["id", "created_at", "updated_at"]
                    ]
                    
                    # Create combined labels
                    labels = []
                    for row in data:
                        x_val = VisualizationGenerator._format_label(row.get(x_field, ""))
                        # Try to find a distinguishing field
                        distinguishing_parts = []
                        for cat_field in categorical_fields[:2]:  # Use up to 2 additional fields
                            cat_val = row.get(cat_field)
                            if cat_val and str(cat_val).strip():
                                distinguishing_parts.append(VisualizationGenerator._format_label(cat_val))
                        
                        if distinguishing_parts:
                            label = f"{x_val} ({', '.join(distinguishing_parts)})"
                        else:
                            label = x_val
                        labels.append(label)
                else:
                    labels = [VisualizationGenerator._format_label(row.get(x_field, "")) for row in data]
            except Exception as e:
                # Fallback to simple labels on any error
                labels = [VisualizationGenerator._format_label(row.get(x_field, f"Item {i+1}")) for i, row in enumerate(data)]

        datasets = []
        # Handle case where y_fields is empty
        if not y_fields and data:
            # If no y_fields specified, try to find numeric columns
            numeric_cols = [
                k for k in data[0].keys() 
                if k != x_field and isinstance(data[0].get(k), (int, float))
            ]
            if numeric_cols:
                y_fields = numeric_cols[:1]
            else:
                # Fallback: use first non-x_field column
                other_cols = [k for k in data[0].keys() if k != x_field]
                y_fields = other_cols[:1] if other_cols else []
        
        # If still no y_fields, create dummy dataset
        if not y_fields:
            datasets.append({
                "label": "Value",
                "data": [1] * len(labels) if labels else [],
                "backgroundColor": DEFAULT_COLORS[0],
                "borderColor": BORDER_COLORS[0],
                "borderWidth": 1,
            })
        else:
            # Create datasets for each y_field
            for i, y_field in enumerate(y_fields):
                # For single dataset (single y_field), assign different colors to each bar
                # For multiple datasets, assign one color per dataset
                if len(y_fields) == 1:
                    # Single series: each bar gets a different color
                    backgroundColor = [DEFAULT_COLORS[j % len(DEFAULT_COLORS)] for j in range(len(labels))]
                    borderColor = [BORDER_COLORS[j % len(BORDER_COLORS)] for j in range(len(labels))]
                else:
                    # Multiple series: one color per dataset
                    backgroundColor = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
                    borderColor = BORDER_COLORS[i % len(BORDER_COLORS)]
                
                datasets.append(
                    {
                        "label": VisualizationGenerator._format_field_name(y_field),
                        "data": [
                            VisualizationGenerator._safe_number(row.get(y_field, 0)) for row in data
                        ],
                        "backgroundColor": backgroundColor,
                        "borderColor": borderColor,
                        "borderWidth": 1,
                    }
                )

        chart_config = {
            "type": "bar",
            "data": {"labels": labels, "datasets": datasets},
            "options": {
                "responsive": True,
                "maintainAspectRatio": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": title,
                        "font": {"size": 16, "weight": "bold"},
                    },
                    "legend": {"display": len(datasets) > 1},
                    "tooltip": {
                        "callbacks": {
                            "label": VisualizationGenerator._get_tooltip_callback(format_type)
                        }
                    },
                },
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "ticks": VisualizationGenerator._get_tick_config(format_type),
                    },
                    "x": {
                        "ticks": {
                            "display": True,
                            "maxRotation": 45,
                            "minRotation": 0,
                            "autoSkip": False,
                            "font": {"size": 12},
                            "color": "#374151",
                        }
                    },
                },
            },
        }

        # Add axis titles if field names are provided
        if y_fields and y_fields[0]:
            chart_config["options"]["scales"]["y"]["title"] = {
                "display": True,
                "text": VisualizationGenerator._format_field_name(y_fields[0]),
            }
        if x_field:
            chart_config["options"]["scales"]["x"]["title"] = {
                "display": True,
                "text": VisualizationGenerator._format_field_name(x_field),
            }

        return chart_config

    @staticmethod
    def _line_chart(
        data: list[dict], x_field: str, y_fields: list[str], title: str, format_type: str
    ) -> dict[str, Any]:
        """Generate line chart configuration"""
        labels = [VisualizationGenerator._format_label(row.get(x_field, "")) for row in data]

        datasets = []
        for i, y_field in enumerate(y_fields):
            datasets.append(
                {
                    "label": VisualizationGenerator._format_field_name(y_field),
                    "data": [
                        VisualizationGenerator._safe_number(row.get(y_field, 0)) for row in data
                    ],
                    "borderColor": BORDER_COLORS[i % len(BORDER_COLORS)],
                    "backgroundColor": DEFAULT_COLORS[i % len(DEFAULT_COLORS)],
                    "fill": False,
                    "tension": 0.1,
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                }
            )

        chart_config = {
            "type": "line",
            "data": {"labels": labels, "datasets": datasets},
            "options": {
                "responsive": True,
                "maintainAspectRatio": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": title,
                        "font": {"size": 16, "weight": "bold"},
                    },
                    "legend": {"display": len(datasets) > 1},
                },
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "ticks": VisualizationGenerator._get_tick_config(format_type),
                    },
                    "x": {
                        "ticks": {
                            "display": True,
                            "maxRotation": 45,
                            "minRotation": 0,
                            "autoSkip": False,
                            "font": {"size": 12},
                            "color": "#374151",
                        }
                    },
                },
                "interaction": {"mode": "index", "intersect": False},
            },
        }

        # Add axis titles if field names are provided
        if y_fields and y_fields[0]:
            chart_config["options"]["scales"]["y"]["title"] = {
                "display": True,
                "text": VisualizationGenerator._format_field_name(y_fields[0]),
            }
        if x_field:
            chart_config["options"]["scales"]["x"]["title"] = {
                "display": True,
                "text": VisualizationGenerator._format_field_name(x_field),
            }

        return chart_config

    @staticmethod
    def _pie_chart(data: list[dict], x_field: str, y_field: str, title: str) -> dict[str, Any]:
        """Generate pie chart configuration"""
        labels = [VisualizationGenerator._format_label(row.get(x_field, "")) for row in data]
        values = [VisualizationGenerator._safe_number(row.get(y_field, 0)) for row in data]

        return {
            "type": "pie",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "data": values,
                        "backgroundColor": DEFAULT_COLORS[: len(values)],
                        "borderColor": BORDER_COLORS[: len(values)],
                        "borderWidth": 2,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": title,
                        "font": {"size": 16, "weight": "bold"},
                    },
                    "legend": {"position": "right"},
                    "tooltip": {"callbacks": {}},
                },
            },
        }

    @staticmethod
    def _stacked_bar(
        data: list[dict], x_field: str, y_fields: list[str], title: str, format_type: str
    ) -> dict[str, Any]:
        """Generate stacked bar chart configuration"""
        config = VisualizationGenerator._bar_chart(data, x_field, y_fields, title, format_type)
        config["options"]["scales"]["x"]["stacked"] = True
        config["options"]["scales"]["y"]["stacked"] = True
        return config

    @staticmethod
    def _multi_series(
        data: list[dict], x_field: str, y_fields: list[str], title: str, format_type: str
    ) -> dict[str, Any]:
        """Generate multi-series line chart"""
        return VisualizationGenerator._line_chart(data, x_field, y_fields, title, format_type)

    @staticmethod
    def _area_chart(
        data: list[dict], x_field: str, y_fields: list[str], title: str, format_type: str
    ) -> dict[str, Any]:
        """Generate area chart configuration"""
        config = VisualizationGenerator._line_chart(data, x_field, y_fields, title, format_type)
        for dataset in config["data"]["datasets"]:
            dataset["fill"] = True
        return config

    @staticmethod
    def _heatmap(data: list[dict], x_field: str, y_fields: list[str], title: str) -> dict[str, Any]:
        """
        Generate heatmap configuration.
        Note: Chart.js doesn't have native heatmap support,
        so we return structured data for custom rendering.
        """
        return {
            "type": "heatmap",
            "data": {"raw": data, "x_field": x_field, "y_field": y_fields[0] if y_fields else ""},
            "options": {"title": title},
        }

    @staticmethod
    def _table_config(data: list[dict], title: str) -> dict[str, Any]:
        """Generate table configuration"""
        columns = list(data[0].keys()) if data else []

        return {
            "type": "table",
            "data": {"columns": columns, "rows": data},
            "options": {
                "title": title,
                "pagination": len(data) > 20,
                "pageSize": 20,
                "sortable": True,
            },
        }

    @staticmethod
    def _format_label(value: Any) -> str:
        """Format a value for use as a chart label"""
        if value is None:
            return "N/A"
        if isinstance(value, int | float):
            return str(value)
        return str(value)[:30]  # Truncate long labels

    @staticmethod
    def _format_field_name(field: str) -> str:
        """Format a field name for display"""
        return field.replace("_", " ").title()

    @staticmethod
    def _safe_number(value: Any) -> float:
        """Safely convert a value to a number"""
        if value is None:
            return 0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _get_tooltip_callback(format_type: str) -> str:
        """Get tooltip callback for format type"""
        if format_type == "currency":
            return "function(context) { return '$' + context.parsed.y.toLocaleString(); }"
        elif format_type == "percentage":
            return "function(context) { return context.parsed.y.toFixed(1) + '%'; }"
        return "function(context) { return context.parsed.y.toLocaleString(); }"

    @staticmethod
    def _get_tick_config(format_type: str) -> dict[str, Any]:
        """Get tick configuration for format type"""
        if format_type == "currency":
            return {"callback": "function(value) { return '$' + value.toLocaleString(); }"}
        elif format_type == "percentage":
            return {"callback": "function(value) { return value + '%'; }"}
        return {}


def generate_chart_config(
    data: list[dict[str, Any]], viz_type: VisualizationType, config: VisualizationConfig
) -> dict[str, Any]:
    """
    Convenience function to generate chart configuration.

    Args:
        data: Query result data
        viz_type: Type of visualization
        config: Visualization configuration

    Returns:
        Chart.js compatible configuration
    """
    return VisualizationGenerator.generate_config(data, viz_type, config)
