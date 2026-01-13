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
        Generate heatmap configuration using Chart.js Matrix controller.
        Transforms data into matrix format with x, y, and value coordinates.
        """
        if not data or not x_field or not y_fields:
            return VisualizationGenerator._empty_chart({"title": title})
        
        y_field = y_fields[0]
        
        # Find the value field (should be numeric, not x or y field)
        value_field = None
        if data:
            for key in data[0].keys():
                if key not in [x_field, y_field] and isinstance(data[0].get(key), (int, float)):
                    value_field = key
                    break
        
        if not value_field:
            # Fallback: use count or first numeric field
            value_field = y_fields[1] if len(y_fields) > 1 else "value"
        
        # Helper function to format labels
        def format_label(value: str, field_name: str) -> str:
            """Format labels for better readability"""
            # Day of week mapping
            day_map = {
                "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
                "4": "Thursday", "5": "Friday", "6": "Saturday",
                "0.0": "Sunday", "1.0": "Monday", "2.0": "Tuesday", "3.0": "Wednesday",
                "4.0": "Thursday", "5.0": "Friday", "6.0": "Saturday"
            }
            
            # Check if this is a day field
            if 'day' in field_name.lower() and value in day_map:
                return day_map[value]
            
            # Check if this is an hour field
            if 'hour' in field_name.lower():
                try:
                    hour = float(value)
                    if hour.is_integer():
                        hour_int = int(hour)
                        if 0 <= hour_int <= 23:
                            # Format as 12-hour time
                            if hour_int == 0:
                                return "12 AM"
                            elif hour_int < 12:
                                return f"{hour_int} AM"
                            elif hour_int == 12:
                                return "12 PM"
                            else:
                                return f"{hour_int - 12} PM"
                except ValueError:
                    pass
            
            return value
        
        # Extract unique x and y values for labels
        x_raw_values = sorted(list(set(str(row.get(x_field, "")) for row in data)))
        y_raw_values = sorted(list(set(str(row.get(y_field, "")) for row in data)))
        
        # Format labels for display
        x_labels = [format_label(val, x_field) for val in x_raw_values]
        y_labels = [format_label(val, y_field) for val in y_raw_values]
        
        # Transform data to matrix format: {x: x_label, y: y_label, v: value}
        matrix_data = []
        for row in data:
            x_val = str(row.get(x_field, ""))
            y_val = str(row.get(y_field, ""))
            value = VisualizationGenerator._safe_number(row.get(value_field, 0))
            
            if x_val in x_raw_values and y_val in y_raw_values:
                matrix_data.append({
                    "x": format_label(x_val, x_field),
                    "y": format_label(y_val, y_field),
                    "v": value
                })
        
        # Find min and max values for color scaling
        values = [point["v"] for point in matrix_data]
        min_val = min(values) if values else 0
        max_val = max(values) if values else 1
        
        # Enhanced color function - Viridis-inspired (colorblind-friendly)
        bg_color_fn = (
            f"function(context) {{ "
            f"const value = context.dataset.data[context.dataIndex]?.v; "
            f"if (value === undefined || value === null) return 'rgba(200, 200, 200, 0.1)'; "
            f"const min = {min_val}; "
            f"const max = {max_val}; "
            f"const normalized = max > min ? (value - min) / (max - min) : 0.5; "
            # Viridis-inspired color scheme (purple -> green -> yellow)
            f"let r, g, b; "
            f"if (normalized < 0.25) {{ "
            f"  const t = normalized / 0.25; "
            f"  r = Math.round(68 + (59 - 68) * t); "
            f"  g = Math.round(1 + (82 - 1) * t); "
            f"  b = Math.round(84 + (139 - 84) * t); "
            f"}} else if (normalized < 0.5) {{ "
            f"  const t = (normalized - 0.25) / 0.25; "
            f"  r = Math.round(59 + (33 - 59) * t); "
            f"  g = Math.round(82 + (145 - 82) * t); "
            f"  b = Math.round(139 + (140 - 139) * t); "
            f"}} else if (normalized < 0.75) {{ "
            f"  const t = (normalized - 0.5) / 0.25; "
            f"  r = Math.round(33 + (94 - 33) * t); "
            f"  g = Math.round(145 + (201 - 145) * t); "
            f"  b = Math.round(140 + (98 - 140) * t); "
            f"}} else {{ "
            f"  const t = (normalized - 0.75) / 0.25; "
            f"  r = Math.round(94 + (253 - 94) * t); "
            f"  g = Math.round(201 + (231 - 201) * t); "
            f"  b = Math.round(98 + (37 - 98) * t); "
            f"}} "
            f"return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + (0.7 + normalized * 0.3) + ')'; "
            f"}}"
        )
        
        # Cell width and height with better spacing
        width_fn = (
            f"function(context) {{ "
            f"const a = context.chart.chartArea; "
            f"if (!a) return 0; "
            f"return (a.right - a.left) / {len(x_labels)} - 2; "  # Reduced by 2 for better spacing
            f"}}"
        )
        
        height_fn = (
            f"function(context) {{ "
            f"const a = context.chart.chartArea; "
            f"if (!a) return 0; "
            f"return (a.bottom - a.top) / {len(y_labels)} - 2; "  # Reduced by 2 for better spacing
            f"}}"
        )
        
        # Enhanced tooltip with better formatting
        tooltip_label_fn = (
            f"function(context) {{ "
            f"const dataPoint = context.dataset.data[context.dataIndex]; "
            f"const lines = []; "
            f"lines.push('📍 {VisualizationGenerator._format_field_name(x_field)}: ' + dataPoint.x); "
            f"lines.push('📅 {VisualizationGenerator._format_field_name(y_field)}: ' + dataPoint.y); "
            f"lines.push('📊 {VisualizationGenerator._format_field_name(value_field)}: ' + dataPoint.v.toLocaleString()); "
            # Add percentage of max
            f"const pct = ({max_val} > 0 ? (dataPoint.v / {max_val} * 100).toFixed(1) : 0); "
            f"lines.push('📈 Intensity: ' + pct + '%'); "
            f"return lines; "
            f"}}"
        )
        
        return {
            "type": "matrix",
            "data": {
                "datasets": [{
                    "label": VisualizationGenerator._format_field_name(value_field),
                    "data": matrix_data,
                    "backgroundColor": bg_color_fn,
                    "borderColor": "rgba(255, 255, 255, 0.8)",  # Stronger white borders
                    "borderWidth": 2,  # Thicker borders
                    "borderRadius": 4,  # Rounded corners
                    "width": width_fn,
                    "height": height_fn
                }]
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": True,
                "animation": {
                    "duration": 750,  # Smooth fade-in
                    "easing": "easeOutQuart"
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": title,
                        "font": {"size": 18, "weight": "bold"},
                        "padding": {"top": 10, "bottom": 15},
                        "color": "#1f2937"
                    },
                    "legend": {
                        "display": True,
                        "position": "bottom",
                        "labels": {
                            "generateLabels": f"function(chart) {{ "
                                f"return [{{ "
                                f"  text: 'Range: {min_val} - {max_val} {VisualizationGenerator._format_field_name(value_field)}', "
                                f"  fillStyle: 'transparent', "
                                f"  strokeStyle: 'transparent', "
                                f"  fontColor: '#6b7280', "
                                f"  lineWidth: 0 "
                                f"}}]; "
                            f"}}"
                        }
                    },
                    "tooltip": {
                        "backgroundColor": "rgba(0, 0, 0, 0.9)",
                        "titleColor": "#fff",
                        "bodyColor": "#fff",
                        "borderColor": "rgba(255, 255, 255, 0.2)",
                        "borderWidth": 1,
                        "padding": 12,
                        "displayColors": False,
                        "callbacks": {
                            "title": "function() { return ''; }",
                            "label": tooltip_label_fn
                        }
                    }
                },
                "scales": {
                    "x": {
                        "type": "category",
                        "labels": x_labels,
                        "offset": True,
                        "title": {
                            "display": True,
                            "text": VisualizationGenerator._format_field_name(x_field),
                            "font": {"size": 13, "weight": "600"},
                            "color": "#374151"
                        },
                        "ticks": {
                            "font": {"size": 11, "weight": "500"},
                            "color": "#4b5563",
                            "autoSkip": False,
                            "maxRotation": 45,
                            "minRotation": 0
                        },
                        "grid": {"display": False}
                    },
                    "y": {
                        "type": "category",
                        "labels": y_labels,
                        "offset": True,
                        "title": {
                            "display": True,
                            "text": VisualizationGenerator._format_field_name(y_field),
                            "font": {"size": 13, "weight": "600"},
                            "color": "#374151"
                        },
                        "ticks": {
                            "font": {"size": 11, "weight": "500"},
                            "color": "#4b5563"
                        },
                        "grid": {"display": False}
                    }
                },
                "layout": {
                    "padding": {
                        "left": 10,
                        "right": 10,
                        "top": 10,
                        "bottom": 10
                    }
                }
            }
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
