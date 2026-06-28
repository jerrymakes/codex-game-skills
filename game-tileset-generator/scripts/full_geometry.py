from __future__ import annotations

from dataclasses import dataclass


ATLAS_ASPECT_TOLERANCE = 0.2
CELL_ASPECT_TOLERANCE = 0.2


@dataclass
class GridFit:
    crop_box: tuple[int, int, int, int]
    fitted_width: int
    fitted_height: int
    cell_width: int
    cell_height: int


@dataclass
class GeometryCheck:
    expected_atlas_aspect: float
    actual_atlas_aspect: float
    atlas_aspect_error: float
    expected_cell_aspect: float
    actual_cell_aspect: float
    cell_aspect_error: float


def fit_to_grid(width: int, height: int, columns: int, rows: int) -> GridFit:
    fitted_width = width - (width % columns)
    fitted_height = height - (height % rows)
    if fitted_width <= 0 or fitted_height <= 0:
        raise SystemExit("candidate image is too small for requested grid")

    left = max(0, (width - fitted_width) // 2)
    top = max(0, (height - fitted_height) // 2)
    return GridFit(
        crop_box=(left, top, left + fitted_width, top + fitted_height),
        fitted_width=fitted_width,
        fitted_height=fitted_height,
        cell_width=fitted_width // columns,
        cell_height=fitted_height // rows,
    )


def check_geometry(fit: GridFit, columns: int, rows: int) -> GeometryCheck:
    expected_atlas_aspect = columns / rows
    actual_atlas_aspect = fit.fitted_width / fit.fitted_height
    atlas_aspect_error = abs(actual_atlas_aspect - expected_atlas_aspect) / expected_atlas_aspect

    expected_cell_aspect = 1.0
    actual_cell_aspect = fit.cell_width / fit.cell_height
    cell_aspect_error = abs(actual_cell_aspect - expected_cell_aspect)

    return GeometryCheck(
        expected_atlas_aspect=expected_atlas_aspect,
        actual_atlas_aspect=actual_atlas_aspect,
        atlas_aspect_error=atlas_aspect_error,
        expected_cell_aspect=expected_cell_aspect,
        actual_cell_aspect=actual_cell_aspect,
        cell_aspect_error=cell_aspect_error,
    )


def require_acceptable_geometry(check: GeometryCheck) -> None:
    if check.atlas_aspect_error > ATLAS_ASPECT_TOLERANCE:
        raise SystemExit(
            "candidate atlas aspect does not match spec closely enough: "
            f"expected {check.expected_atlas_aspect:.3f}, got {check.actual_atlas_aspect:.3f}"
        )
    if check.cell_aspect_error > CELL_ASPECT_TOLERANCE:
        raise SystemExit(
            "derived cell aspect is too far from square for full extraction: "
            f"expected {check.expected_cell_aspect:.3f}, got {check.actual_cell_aspect:.3f}"
        )
