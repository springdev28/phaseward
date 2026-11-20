"""Phaseward units: nm/meV at the scattering API, SI for kinetic coefficients.

The separate polynomial demo remains dimensionless with no physical mapping.
"""

NM_TO_M: float = 1e-9
MEV_TO_J: float = 1.602176634e-22  # Exact SI definition of one meV in joules.

DIMENSIONLESS: str = "dimensionless"


def demo_units() -> dict[str, str]:
    """Return fresh unit labels; ``1`` is the dimensionless unit."""
    return {"x": "1", "f_x": "1", "integral": "1"}


def physical_constants() -> dict[str, float]:
    """Record the actual SciPy SI constants used for a scattering run."""
    from scipy.constants import elementary_charge, hbar, m_e

    return {"hbar_J_s": hbar, "electron_mass_kg": m_e,
            "elementary_charge_C": elementary_charge, "nm_to_m": NM_TO_M, "meV_to_J": MEV_TO_J}
