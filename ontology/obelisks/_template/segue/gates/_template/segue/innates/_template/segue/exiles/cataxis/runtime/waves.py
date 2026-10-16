#!/usr/bin/env python3
from __future__ import annotations

import cmath
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from physics import Vector3
from spacetime import EPSILON, OWNER

SCHEMA = "savant://cataxis/waves/1.0.0"
C = 299_792_458.0


class WaveError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Wave:
    wave_id: str
    amplitude: float
    frequency_hz: float
    phase_radians: float = 0.0
    propagation_speed_mps: float = C
    direction: Vector3 = field(
        default_factory=lambda: Vector3(
            1.0,
            0.0,
            0.0,
        )
    )
    damping_per_meter: float = 0.0
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class WaveSample:
    displacement: float
    phase_radians: float
    position_meters: float
    time_seconds: float


@dataclass(frozen=True, slots=True)
class InterferenceResult:
    amplitude: float
    intensity_relative: float
    constructive: bool
    destructive: bool
    contributors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DopplerResult:
    emitted_frequency_hz: float
    observed_frequency_hz: float
    ratio: float


@dataclass(frozen=True, slots=True)
class WaveProjection:
    waves: tuple[Wave, ...]
    samples: tuple[WaveSample, ...]
    diagnostics: Mapping[str, Any] = field(
        default_factory=dict
    )
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = (
            datetime.now(UTC).isoformat()
        )
        payload["digest"] = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return payload


def _finite(
    value: Any,
    name: str,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise WaveError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise WaveError(
            f"{name} must be finite"
        )

    return number


def _positive(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number <= 0:
        raise WaveError(
            f"{name} must be positive"
        )

    return number


def _nonnegative(
    value: Any,
    name: str,
) -> float:
    number = _finite(value, name)

    if number < 0:
        raise WaveError(
            f"{name} must be nonnegative"
        )

    return number


def validate(
    wave: Wave,
) -> None:
    _finite(
        wave.amplitude,
        "amplitude",
    )

    _positive(
        wave.frequency_hz,
        "frequency_hz",
    )

    _positive(
        wave.propagation_speed_mps,
        "propagation_speed_mps",
    )

    _nonnegative(
        wave.damping_per_meter,
        "damping_per_meter",
    )

    if wave.direction.magnitude <= EPSILON:
        raise WaveError(
            "wave direction cannot be zero"
        )


def period_seconds(
    wave: Wave,
) -> float:
    validate(wave)

    return 1.0 / wave.frequency_hz


def wavelength_meters(
    wave: Wave,
) -> float:
    validate(wave)

    return (
        wave.propagation_speed_mps
        / wave.frequency_hz
    )


def angular_frequency(
    wave: Wave,
) -> float:
    validate(wave)

    return (
        2.0
        * math.pi
        * wave.frequency_hz
    )


def wave_number(
    wave: Wave,
) -> float:
    return (
        2.0
        * math.pi
        / wavelength_meters(wave)
    )


def phase_velocity(
    wave: Wave,
) -> float:
    validate(wave)

    return wave.propagation_speed_mps


def phase_at(
    wave: Wave,
    *,
    position_meters: float,
    time_seconds: float,
) -> float:
    validate(wave)

    position = _finite(
        position_meters,
        "position_meters",
    )

    time = _finite(
        time_seconds,
        "time_seconds",
    )

    return (
        wave_number(wave) * position
        - angular_frequency(wave) * time
        + wave.phase_radians
    )


def amplitude_at(
    wave: Wave,
    *,
    distance_meters: float,
) -> float:
    validate(wave)

    distance = _nonnegative(
        distance_meters,
        "distance_meters",
    )

    return (
        wave.amplitude
        * math.exp(
            -wave.damping_per_meter
            * distance
        )
    )


def sample(
    wave: Wave,
    *,
    position_meters: float,
    time_seconds: float,
) -> WaveSample:
    phase = phase_at(
        wave,
        position_meters=position_meters,
        time_seconds=time_seconds,
    )

    amplitude = amplitude_at(
        wave,
        distance_meters=abs(
            position_meters
        ),
    )

    return WaveSample(
        displacement=(
            amplitude
            * math.sin(phase)
        ),
        phase_radians=phase,
        position_meters=position_meters,
        time_seconds=time_seconds,
    )


def phasor(
    wave: Wave,
    *,
    position_meters: float = 0.0,
    time_seconds: float = 0.0,
) -> complex:
    phase = phase_at(
        wave,
        position_meters=position_meters,
        time_seconds=time_seconds,
    )

    amplitude = amplitude_at(
        wave,
        distance_meters=abs(
            position_meters
        ),
    )

    return cmath.rect(
        amplitude,
        phase,
    )


def superposition(
    waves: Sequence[Wave],
    *,
    position_meters: float,
    time_seconds: float,
) -> InterferenceResult:
    if not waves:
        return InterferenceResult(
            amplitude=0.0,
            intensity_relative=0.0,
            constructive=False,
            destructive=False,
            contributors=(),
        )

    resultant = sum(
        (
            phasor(
                wave,
                position_meters=(
                    position_meters
                ),
                time_seconds=(
                    time_seconds
                ),
            )
            for wave in waves
        ),
        0j,
    )

    amplitude = abs(resultant)

    individual = sum(
        abs(
            amplitude_at(
                wave,
                distance_meters=abs(
                    position_meters
                ),
            )
        )
        for wave in waves
    )

    constructive = (
        individual > EPSILON
        and amplitude
        >= individual - EPSILON
    )

    destructive = (
        individual > EPSILON
        and amplitude <= EPSILON
    )

    return InterferenceResult(
        amplitude=amplitude,
        intensity_relative=(
            amplitude * amplitude
        ),
        constructive=constructive,
        destructive=destructive,
        contributors=tuple(
            wave.wave_id
            for wave in waves
        ),
    )


def standing_wave(
    *,
    amplitude: float,
    wave_number_per_meter: float,
    angular_frequency_rad_s: float,
    position_meters: float,
    time_seconds: float,
) -> float:
    return (
        2.0
        * _finite(
            amplitude,
            "amplitude",
        )
        * math.sin(
            _finite(
                wave_number_per_meter,
                "wave_number_per_meter",
            )
            * _finite(
                position_meters,
                "position_meters",
            )
        )
        * math.cos(
            _finite(
                angular_frequency_rad_s,
                "angular_frequency_rad_s",
            )
            * _finite(
                time_seconds,
                "time_seconds",
            )
        )
    )


def doppler_classical(
    *,
    emitted_frequency_hz: float,
    propagation_speed_mps: float,
    observer_velocity_toward_source_mps: float = 0.0,
    source_velocity_toward_observer_mps: float = 0.0,
) -> DopplerResult:
    frequency = _positive(
        emitted_frequency_hz,
        "emitted_frequency_hz",
    )

    speed = _positive(
        propagation_speed_mps,
        "propagation_speed_mps",
    )

    observer = _finite(
        observer_velocity_toward_source_mps,
        "observer_velocity_toward_source_mps",
    )

    source = _finite(
        source_velocity_toward_observer_mps,
        "source_velocity_toward_observer_mps",
    )

    denominator = speed - source

    if denominator <= EPSILON:
        raise WaveError(
            "source speed reaches or exceeds "
            "classical propagation denominator"
        )

    observed = (
        frequency
        * (speed + observer)
        / denominator
    )

    if observed < 0:
        raise WaveError(
            "classical doppler result is negative"
        )

    return DopplerResult(
        emitted_frequency_hz=frequency,
        observed_frequency_hz=observed,
        ratio=observed / frequency,
    )


def doppler_relativistic(
    *,
    emitted_frequency_hz: float,
    radial_velocity_mps: float,
) -> DopplerResult:
    frequency = _positive(
        emitted_frequency_hz,
        "emitted_frequency_hz",
    )

    velocity = _finite(
        radial_velocity_mps,
        "radial_velocity_mps",
    )

    beta = velocity / C

    if abs(beta) >= 1.0:
        raise WaveError(
            "radial velocity must remain below c"
        )

    ratio = math.sqrt(
        (1.0 - beta)
        / (1.0 + beta)
    )

    observed = frequency * ratio

    return DopplerResult(
        emitted_frequency_hz=frequency,
        observed_frequency_hz=observed,
        ratio=ratio,
    )


def beat_frequency(
    first_frequency_hz: float,
    second_frequency_hz: float,
) -> float:
    return abs(
        _positive(
            first_frequency_hz,
            "first_frequency_hz",
        )
        - _positive(
            second_frequency_hz,
            "second_frequency_hz",
        )
    )


def resonance_ratio(
    *,
    driving_frequency_hz: float,
    natural_frequency_hz: float,
) -> float:
    return (
        _positive(
            driving_frequency_hz,
            "driving_frequency_hz",
        )
        / _positive(
            natural_frequency_hz,
            "natural_frequency_hz",
        )
    )


def inverse_square_intensity(
    *,
    source_power_watts: float,
    radius_meters: float,
) -> float:
    power = _nonnegative(
        source_power_watts,
        "source_power_watts",
    )

    radius = _positive(
        radius_meters,
        "radius_meters",
    )

    return (
        power
        / (
            4.0
            * math.pi
            * radius
            * radius
        )
    )


def acoustic_intensity_level_db(
    *,
    intensity_w_m2: float,
    reference_w_m2: float = 1e-12,
) -> float:
    intensity = _positive(
        intensity_w_m2,
        "intensity_w_m2",
    )

    reference = _positive(
        reference_w_m2,
        "reference_w_m2",
    )

    return (
        10.0
        * math.log10(
            intensity / reference
        )
    )


def reflection_coefficient(
    *,
    impedance_one: float,
    impedance_two: float,
) -> float:
    first = _positive(
        impedance_one,
        "impedance_one",
    )

    second = _positive(
        impedance_two,
        "impedance_two",
    )

    return (
        (second - first)
        / (second + first)
    )


def transmission_power_fraction(
    *,
    impedance_one: float,
    impedance_two: float,
) -> float:
    first = _positive(
        impedance_one,
        "impedance_one",
    )

    second = _positive(
        impedance_two,
        "impedance_two",
    )

    return (
        4.0
        * first
        * second
        / (
            (first + second)
            * (first + second)
        )
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "wave_state",
            "frequency",
            "period",
            "wavelength",
            "phase",
            "phase_velocity",
            "angular_frequency",
            "wave_number",
            "spatiotemporal_sampling",
            "propagation",
            "exponential_attenuation",
            "phasor_representation",
            "linear_superposition",
            "constructive_interference",
            "destructive_interference",
            "standing_waves",
            "beat_frequency",
            "resonance_ratio",
            "classical_doppler_shift",
            "relativistic_doppler_shift",
            "inverse_square_intensity",
            "acoustic_intensity_level",
            "impedance_reflection",
            "impedance_transmission",
            "causal_propagation_speed",
            "mechanical_wave_support",
            "acoustic_wave_support",
            "electromagnetic_wave_support",
            "carbon_wave_environment_support",
            "mobius_signal_consequence_support",
            "deterministic_wave_projection",
        ],
    }
