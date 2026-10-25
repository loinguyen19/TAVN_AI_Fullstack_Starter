import re

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

# Thread size stated in the free-text notes, e.g. "M12", "M14x1.5".
# Only the nominal diameter is captured: the fine-pitch suffix changes the
# stress area slightly but never the order of magnitude.
THREAD_RE = re.compile(r"\bM(\d{1,2})(?:\s*[xX]\s*[\d.,]+)?\b")

# Plausible tightening-torque band per nominal thread diameter, in Nm.
#
# Derived from the standard bolted-joint relation rather than guessed:
#     T = K * 0.7 * A_s * R_p0.2 * d
# with K = 0.2 (nut factor, dry steel), A_s the tensile stress area, R_p0.2 the
# yield strength (640 MPa for property class 8.8, 940 MPa for 10.9) and d the
# nominal diameter. Reference values that produces:
#
#     M6 10.8/15.9   M8 26.2/38.5   M10 52.0/76.3   M12 90.6/133.1
#     M14 144.3/211.9   M16 225.1/330.6   M22 597.3/877.2      (8.8 / 10.9)
#
# The data almost never states a property class, so the band must span the
# plausible class and friction range: ceiling ~1.5x the 10.9 reference, floor
# ~0.25x the 8.8 reference. The headroom is deliberate -- real OEM specs exceed
# the simple calculation (angle tightening, yield-point tightening, higher
# friction), so this only catches gross violations. Hence WARNING, not ERROR.
BANDS = {
    5: (3, 18),
    6: (4, 24),
    8: (10, 58),
    10: (20, 115),
    12: (35, 200),
    14: (55, 320),
    16: (85, 500),
    18: (120, 700),
    20: (140, 900),
    22: (150, 1000),
    24: (180, 1200),
}

# No hand torque wrench reaches this. Catches order-of-magnitude errors such as
# a dropped decimal separator, independently of any thread size being stated.
ABSOLUTE_CEILING_NM = 1000.0


class TorquePlausibilityValidator(BaseValidator):
    """Flags torque values that are physically implausible for the fastener.

    Two independent checks:
      1. An absolute ceiling, applied to every entry. Needs no thread size.
      2. A per-thread-size band, applied only when the notes state an M-size.
    """

    rationale = (
        "A torque far outside the capability of the stated thread size will either "
        "shear the fastener or leave the joint loose; both fail in service, and on "
        "chassis or engine fasteners that is a safety issue."
    )

    @property
    def name(self) -> str:
        return "torque_plausibility"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for addr in document.addresses:
            if addr.torque is None or addr.torque <= 0:
                continue  # owned by torque_value / missing_torque

            if addr.torque > ABSOLUTE_CEILING_NM:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.ERROR,
                        message=(
                            f"Address {addr.code!r} specifies {addr.torque_raw} Nm, "
                            f"beyond the range of any workshop torque wrench "
                            f"(>{ABSOLUTE_CEILING_NM:.0f} Nm). This is an "
                            f"order-of-magnitude error."
                        ),
                        validator=self.name,
                        expected=f"<= {ABSOLUTE_CEILING_NM:.0f} Nm",
                        actual=f"{addr.torque_raw} Nm",
                    )
                )
                continue

            match = THREAD_RE.search(addr.notes or "")
            if not match:
                continue

            size = int(match.group(1))
            band = BANDS.get(size)
            if band is None:
                continue

            low, high = band
            if addr.torque < low:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.WARNING,
                        message=(
                            f"Address {addr.code!r} specifies {addr.torque_raw} Nm for "
                            f"an M{size} fastener, below the plausible range "
                            f"{low}-{high} Nm. An under-torqued joint can work loose."
                        ),
                        validator=self.name,
                        expected=f"{low}-{high} Nm for M{size}",
                        actual=f"{addr.torque_raw} Nm",
                    )
                )
            elif addr.torque > high:
                issues.append(
                    ValidationResult(
                        code=addr.code,
                        severity=Severity.WARNING,
                        message=(
                            f"Address {addr.code!r} specifies {addr.torque_raw} Nm for "
                            f"an M{size} fastener, above the plausible range "
                            f"{low}-{high} Nm. This risks shearing the bolt."
                        ),
                        validator=self.name,
                        expected=f"{low}-{high} Nm for M{size}",
                        actual=f"{addr.torque_raw} Nm",
                    )
                )
        return issues
