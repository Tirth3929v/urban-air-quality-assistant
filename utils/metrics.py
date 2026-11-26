"""Deterministic impact calculations for the interactive habit simulator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatedImpact:
    """Calculated exposure and emission savings for selected habits."""

    active_exposure_pct: int
    active_weekly_co2_kg: float
    annual_trees_equivalent: float
    completion_ratio: float


def calculate_simulated_impact(
    max_exposure_pct: int,
    max_weekly_co2_kg: float,
    exposure_habits_selected: int,
    exposure_habits_total: int,
    emission_swaps_selected: int,
    emission_swaps_total: int,
) -> SimulatedImpact:
    """Scale exposure and CO2 savings proportionally based on user-selected habits."""
    exp_ratio = (
        min(max(exposure_habits_selected / exposure_habits_total, 0.0), 1.0)
        if exposure_habits_total > 0
        else 0.0
    )
    co2_ratio = (
        min(max(emission_swaps_selected / emission_swaps_total, 0.0), 1.0)
        if emission_swaps_total > 0
        else 0.0
    )

    active_exposure = round(max_exposure_pct * exp_ratio)
    active_co2 = round(max_weekly_co2_kg * co2_ratio, 1)
    # One mature urban tree absorbs ~21.77 kg CO2 per year
    annual_trees = round((active_co2 * 52.0) / 21.77, 1)

    total_items = exposure_habits_total + emission_swaps_total
    selected_items = exposure_habits_selected + emission_swaps_selected
    overall_ratio = round(selected_items / total_items, 2) if total_items > 0 else 0.0

    return SimulatedImpact(
        active_exposure_pct=active_exposure,
        active_weekly_co2_kg=active_co2,
        annual_trees_equivalent=annual_trees,
        completion_ratio=overall_ratio,
    )
