"""AQI calculation service following EPA breakpoint standards.

Per regulatory standards, official Air Quality Index (AQI) values require
specific temporal averaging periods (e.g., 24-hour NowCast for particulate matter).
This service does not fabricate official AQI metrics when required measurements
or requisite averaging windows are missing.
"""

from typing import Optional, TypedDict, List
from math import floor


class AQIResult(TypedDict):
    """Result of an AQI evaluation."""
    status: str  # "calculated", "unavailable"
    aqi: Optional[int]
    category: Optional[str]
    pollutant: Optional[str]
    averaging_period: Optional[str]
    reason: Optional[str]


# EPA PM2.5 Breakpoints (concentration C_low, C_high in µg/m³, index I_low, I_high, category)
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50, "Good"),
    (12.1, 35.4, 51, 100, "Moderate"),
    (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups"),
    (55.5, 150.4, 151, 200, "Unhealthy"),
    (150.5, 250.4, 201, 300, "Very Unhealthy"),
    (250.5, 500.4, 301, 500, "Hazardous"),
]

# EPA PM10 Breakpoints (concentration C_low, C_high in µg/m³, index I_low, I_high, category)
PM10_BREAKPOINTS = [
    (0.0, 54.0, 0, 50, "Good"),
    (55.0, 154.0, 51, 100, "Moderate"),
    (155.0, 254.0, 101, 150, "Unhealthy for Sensitive Groups"),
    (255.0, 354.0, 151, 200, "Unhealthy"),
    (355.0, 424.0, 201, 300, "Very Unhealthy"),
    (425.0, 604.0, 301, 500, "Hazardous"),
]


def _linear_interpolate(
    conc: float,
    breakpoints: List[tuple[float, float, int, int, str]],
) -> Optional[tuple[int, str]]:
    """Apply standard EPA linear interpolation equation for an individual pollutant."""
    for c_low, c_high, i_low, i_high, category in breakpoints:
        if c_low <= conc <= c_high:
            # EPA formula: I = [(I_high - I_low) / (C_high - C_low)] * (C - C_low) + I_low
            aqi_val = round(((i_high - i_low) / (c_high - c_low)) * (conc - c_low) + i_low)
            return aqi_val, category

    # If concentration exceeds highest hazardous threshold
    if conc > breakpoints[-1][1]:
        return 500, "Hazardous"

    return None


def calculate_instantaneous_aqi(
    pm2_5: Optional[float],
    pm10: Optional[float],
) -> AQIResult:
    """Calculate an indicative instantaneous AQI estimate from raw particulate readings.

    Note:
        Official EPA AQI requires 24-hour averaging or NowCast temporal weighting.
        If measurements are missing or negative, status 'unavailable' is returned.
    """
    if pm2_5 is None and pm10 is None:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant=None,
            averaging_period="instantaneous",
            reason="Missing required PM2.5 and PM10 measurements.",
        )

    results: list[tuple[int, str, str]] = []

    if pm2_5 is not None:
        if pm2_5 < 0 or pm2_5 > 1000:
            return AQIResult(
                status="unavailable",
                aqi=None,
                category=None,
                pollutant="PM2.5",
                averaging_period="instantaneous",
                reason=f"PM2.5 concentration {pm2_5} µg/m³ is out of valid range (0-1000).",
            )
        # Truncate PM2.5 to 1 decimal place per EPA guidelines
        truncated_pm25 = floor(pm2_5 * 10) / 10
        interp = _linear_interpolate(truncated_pm25, PM25_BREAKPOINTS)
        if interp:
            results.append((interp[0], interp[1], "PM2.5"))

    if pm10 is not None:
        if pm10 < 0 or pm10 > 2000:
            return AQIResult(
                status="unavailable",
                aqi=None,
                category=None,
                pollutant="PM10",
                averaging_period="instantaneous",
                reason=f"PM10 concentration {pm10} µg/m³ is out of valid range (0-2000).",
            )
        # Truncate PM10 to integer per EPA guidelines
        truncated_pm10 = float(floor(pm10))
        interp = _linear_interpolate(truncated_pm10, PM10_BREAKPOINTS)
        if interp:
            results.append((interp[0], interp[1], "PM10"))

    if not results:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant=None,
            averaging_period="instantaneous",
            reason="Unable to determine AQI from provided values.",
        )

    # Highest sub-index determines overall AQI
    results.sort(key=lambda x: x[0], reverse=True)
    highest_aqi, highest_cat, dominant_pollutant = results[0]

    return AQIResult(
        status="calculated",
        aqi=highest_aqi,
        category=highest_cat,
        pollutant=dominant_pollutant,
        averaging_period="instantaneous_estimate",
        reason="Indicative instantaneous estimate. Official regulatory AQI requires 24-hr NowCast averaging.",
    )


def calculate_official_nowcast_aqi(
    hourly_pm25_readings: List[float],
) -> AQIResult:
    """Calculate official EPA NowCast AQI for PM2.5 across a 12-hour window.

    Requires at least 2 of the 3 most recent hours to be valid.
    If the series has fewer than 12 hours or lacks recent hours, returns status 'unavailable'.
    """
    if len(hourly_pm25_readings) < 12:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant="PM2.5",
            averaging_period="12-hour NowCast",
            reason=f"Insufficient averaging period: requires 12 hours of data, but only {len(hourly_pm25_readings)} available.",
        )

    # Check for negative or corrupt values
    valid_readings = [v for v in hourly_pm25_readings if v is not None and v >= 0]
    if len(valid_readings) < 12:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant="PM2.5",
            averaging_period="12-hour NowCast",
            reason="Missing or corrupt values in the 12-hour averaging window.",
        )

    c_min = min(valid_readings)
    c_max = max(valid_readings)

    # Compute weight factor w* = 1 - (c_max - c_min) / c_max if c_max > 0, else 1
    weight_factor = 1.0 - ((c_max - c_min) / c_max) if c_max > 0 else 1.0
    weight_factor = max(0.5, min(1.0, weight_factor))

    weighted_sum = 0.0
    weight_sum = 0.0
    # Readings ordered from most recent (index 0) to oldest (index 11)
    for i, reading in enumerate(valid_readings[:12]):
        w = weight_factor ** i
        weighted_sum += reading * w
        weight_sum += w

    nowcast_concentration = weighted_sum / weight_sum
    truncated_c = floor(nowcast_concentration * 10) / 10
    interp = _linear_interpolate(truncated_c, PM25_BREAKPOINTS)

    if not interp:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant="PM2.5",
            averaging_period="12-hour NowCast",
            reason="NowCast concentration calculation resulted in out-of-bounds AQI.",
        )

    return AQIResult(
        status="calculated",
        aqi=interp[0],
        category=interp[1],
        pollutant="PM2.5",
        averaging_period="12-hour NowCast",
        reason=None,
    )


# -----------------------------------------------------------------------------
# CPCB (Central Pollution Control Board - India) AQI Calculation & Compliance
# -----------------------------------------------------------------------------

CPCB_PM25_BREAKPOINTS = [
    (0.0, 30.0, 0, 50, "Good"),
    (31.0, 60.0, 51, 100, "Satisfactory"),
    (61.0, 90.0, 101, 200, "Moderate"),
    (91.0, 120.0, 201, 300, "Poor"),
    (121.0, 250.0, 301, 400, "Very Poor"),
    (251.0, 500.0, 401, 500, "Severe"),
]

CPCB_PM10_BREAKPOINTS = [
    (0.0, 50.0, 0, 50, "Good"),
    (51.0, 100.0, 51, 100, "Satisfactory"),
    (101.0, 250.0, 101, 200, "Moderate"),
    (251.0, 350.0, 201, 300, "Poor"),
    (351.0, 430.0, 301, 400, "Very Poor"),
    (431.0, 600.0, 401, 500, "Severe"),
]


def calculate_official_cpcb_aqi(
    pollutant_24h_averages: dict[str, float],
    is_24h_average: bool = True,
) -> AQIResult:
    """Calculate official Indian CPCB National Air Quality Index (NAQI).

    Regulatory Compliance Requirements (CPCB):
    1. A minimum of 3 pollutants must be monitored.
    2. At least one of the pollutants MUST be PM2.5 or PM10.
    3. Each pollutant must meet the 24-hour averaging requirement (min 16 hours of valid data).
    4. Instantaneous or single readings must NEVER be presented as official CPCB AQI.
    """
    if not is_24h_average:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant=None,
            averaging_period="sub-24h",
            reason=(
                "CPCB Compliance: Instantaneous or sub-24h readings cannot be presented "
                "as official CPCB AQI. A 24-hour averaging period (min 16 hours valid data) is required."
            ),
        )

    # Filter out None/negative values
    valid_pollutants = {
        k.upper(): v for k, v in pollutant_24h_averages.items()
        if v is not None and v >= 0
    }

    # Rule 1: Minimum 3 pollutants required
    if len(valid_pollutants) < 3:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant=None,
            averaging_period="24-hour",
            reason=(
                f"CPCB Compliance: Official CPCB AQI requires data for at least 3 pollutants, "
                f"but only {len(valid_pollutants)} provided ({list(valid_pollutants.keys())})."
            ),
        )

    # Rule 2: At least one must be PM2.5 or PM10
    has_particulate = "PM2.5" in valid_pollutants or "PM25" in valid_pollutants or "PM10" in valid_pollutants
    if not has_particulate:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant=None,
            averaging_period="24-hour",
            reason="CPCB Compliance: At least one of the 3 pollutants must be PM2.5 or PM10.",
        )

    sub_indices: list[tuple[int, str, str]] = []

    pm25_val = valid_pollutants.get("PM2.5", valid_pollutants.get("PM25"))
    if pm25_val is not None:
        interp = _linear_interpolate(pm25_val, CPCB_PM25_BREAKPOINTS)
        if interp:
            sub_indices.append((interp[0], interp[1], "PM2.5"))

    pm10_val = valid_pollutants.get("PM10")
    if pm10_val is not None:
        interp = _linear_interpolate(pm10_val, CPCB_PM10_BREAKPOINTS)
        if interp:
            sub_indices.append((interp[0], interp[1], "PM10"))

    if not sub_indices:
        return AQIResult(
            status="unavailable",
            aqi=None,
            category=None,
            pollutant=None,
            averaging_period="24-hour",
            reason="Unable to compute valid sub-indices for provided pollutants.",
        )

    # Highest sub-index determines overall CPCB AQI
    sub_indices.sort(key=lambda x: x[0], reverse=True)
    max_aqi, max_cat, dom_pollutant = sub_indices[0]

    return AQIResult(
        status="calculated",
        aqi=max_aqi,
        category=max_cat,
        pollutant=dom_pollutant,
        averaging_period="24-hour",
        reason=None,
    )

