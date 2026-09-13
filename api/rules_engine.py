"""
rules_engine.py

WHY THIS FILE EXISTS:
Our ML models (Isolation Forest, Random Forest) were trained on a limited
range of synthetic values. When a reading falls far outside that range
(e.g. vibration = 18 mm/s, when training data topped out around 9 mm/s),
tree-based models don't extrapolate -- they can't reliably tell you that
18 is "worse" than 9. This is a known, well-documented limitation of
tree-based models, not a bug in our code.

Real industrial systems solve this by never relying on ML alone. They
pair statistical models with straightforward engineering threshold
checks -- the kind of limits an actual maintenance engineer would use.
This file is that layer. It's simple on purpose: every recommendation
here is directly traceable to a specific sensor value crossing a known
limit, which makes it explainable and defensible (unlike a raw ML
probability, which is hard to justify to a non-technical evaluator).

HOW IT'S USED:
main.py calls evaluate_thresholds(reading) BEFORE trusting the ML output.
If any hard limit is breached, this layer can override the ML risk level
to HIGH regardless of what the models say -- this is the safety net.

IMPORTANT CAVEAT (be upfront about this in your report):
These threshold values are reasonable engineering estimates based on
typical centrifugal/reciprocating compressor operating ranges, NOT
GAIL-specific limits. In a real deployment, these would be replaced
with GAIL's actual equipment specifications and safety limits.
"""

from dataclasses import dataclass, field


# ---- Threshold table ----
# Each sensor has a "warning" and "critical" limit. Values below warning
# are considered normal. This table is the single source of truth for
# every rule-based check in this file -- change limits here, nothing
# else needs to change.
THRESHOLDS = {
    "vibration_mm_s":        {"warning": 4.0,  "critical": 7.0},
    "bearing_temp_c":        {"warning": 70.0, "critical": 85.0},
    "oil_temp_c":            {"warning": 65.0, "critical": 80.0},
    "discharge_pressure_bar": {"low_critical": 45.0, "low_warning": 50.0,
                                "high_warning": 60.0, "high_critical": 65.0},
    "suction_pressure_bar":   {"low_critical": 12.0, "low_warning": 15.0,
                                "high_warning": 20.0, "high_critical": 23.0},
}

# Maps each sensor to specific maintenance actions when it's the cause
# of a warning/critical flag. Keeping this separate from the thresholds
# above means the "what to check" text can be edited independently of
# "what counts as abnormal."
RECOMMENDATIONS = {
    "vibration_mm_s": [
        "Inspect bearings for wear",
        "Check shaft alignment and coupling",
        "Verify mounting bolts are secure",
    ],
    "bearing_temp_c": [
        "Inspect bearing lubrication",
        "Check cooling system function",
        "Reduce load if temperature keeps rising",
    ],
    "oil_temp_c": [
        "Check lubrication oil level and quality",
        "Inspect oil cooler for blockage",
        "Verify oil pump is functioning correctly",
    ],
    "discharge_pressure_bar": [
        "Inspect discharge valve for blockage or leakage",
        "Check for downstream restrictions",
        "Verify compressor is not overloaded",
    ],
    "suction_pressure_bar": [
        "Inspect suction line for blockage or leaks",
        "Check inlet filter for clogging",
        "Verify upstream supply pressure is stable",
    ],
}


@dataclass
class ThresholdResult:
    """What evaluate_thresholds() returns -- kept as a simple structured
    object so main.py can use it directly without parsing strings."""
    detected_issues: list = field(default_factory=list)   # human-readable flags
    recommendations: list = field(default_factory=list)   # de-duplicated action list
    max_severity: str = "normal"                          # "normal" | "warning" | "critical"
    sensor_health_penalty: float = 0.0                     # 0-100, subtracted from health score


def _check_simple_sensor(name: str, value: float, limits: dict, issues: list, actions: set, penalty: list):
    """Handles sensors with a single warning/critical ceiling
    (vibration, bearing_temp, oil_temp)."""
    if value >= limits["critical"]:
        issues.append(f"CRITICAL: {name.replace('_', ' ')} is {value} (limit: {limits['critical']})")
        actions.update(RECOMMENDATIONS[name])
        penalty.append(("critical", 25))
    elif value >= limits["warning"]:
        issues.append(f"WARNING: {name.replace('_', ' ')} is {value} (limit: {limits['warning']})")
        actions.update(RECOMMENDATIONS[name])
        penalty.append(("warning", 10))


def _check_pressure_sensor(name: str, value: float, limits: dict, issues: list, actions: set, penalty: list):
    """Handles pressure sensors, which are abnormal if TOO HIGH or TOO LOW."""
    if value <= limits["low_critical"] or value >= limits["high_critical"]:
        issues.append(f"CRITICAL: {name.replace('_', ' ')} is {value} (outside safe range)")
        actions.update(RECOMMENDATIONS[name])
        penalty.append(("critical", 25))
    elif value <= limits["low_warning"] or value >= limits["high_warning"]:
        issues.append(f"WARNING: {name.replace('_', ' ')} is {value} (approaching limit)")
        actions.update(RECOMMENDATIONS[name])
        penalty.append(("warning", 10))


def evaluate_thresholds(reading: dict) -> ThresholdResult:
    """
    Main entry point. Takes a dict of sensor readings (same shape as our
    SensorReading model) and returns detected issues + recommendations
    based purely on fixed engineering limits -- no ML involved.
    """
    issues = []
    actions = set()   # set avoids duplicate recommendations across sensors
    penalty_events = []

    _check_simple_sensor("vibration_mm_s", reading["vibration_mm_s"],
                          THRESHOLDS["vibration_mm_s"], issues, actions, penalty_events)
    _check_simple_sensor("bearing_temp_c", reading["bearing_temp_c"],
                          THRESHOLDS["bearing_temp_c"], issues, actions, penalty_events)
    _check_simple_sensor("oil_temp_c", reading["oil_temp_c"],
                          THRESHOLDS["oil_temp_c"], issues, actions, penalty_events)
    _check_pressure_sensor("discharge_pressure_bar", reading["discharge_pressure_bar"],
                            THRESHOLDS["discharge_pressure_bar"], issues, actions, penalty_events)
    _check_pressure_sensor("suction_pressure_bar", reading["suction_pressure_bar"],
                            THRESHOLDS["suction_pressure_bar"], issues, actions, penalty_events)

    # Overall severity = the worst single event seen across all sensors
    if any(level == "critical" for level, _ in penalty_events):
        max_severity = "critical"
    elif any(level == "warning" for level, _ in penalty_events):
        max_severity = "warning"
    else:
        max_severity = "normal"

    # Total penalty is capped at 70 -- we never want the rule layer alone
    # to drag health score all the way to 0; it works ALONGSIDE the ML
    # score, not instead of it. See main.py for how these combine.
    total_penalty = min(sum(p for _, p in penalty_events), 70)

    return ThresholdResult(
        detected_issues=issues,
        recommendations=sorted(actions),
        max_severity=max_severity,
        sensor_health_penalty=total_penalty
    )   