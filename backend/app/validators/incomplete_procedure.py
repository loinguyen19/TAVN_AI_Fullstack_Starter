import re

from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity

STEP_RE = re.compile(r"\b(?:step|stage)\s+(\d+)\b", re.IGNORECASE)


class IncompleteProcedureValidator(BaseValidator):
    """Flags a multi-step tightening procedure whose later steps are absent.

    Critical fasteners are often torqued in stages -- an initial figure, then a
    further angle or torque. If step 1 is published and step 2 is not, the
    entry reads as complete while specifying only part of the job.
    """

    rationale = (
        "A staged tightening procedure that stops at step 1 leaves the fastener at a "
        "fraction of its final preload, while appearing to be a complete "
        "specification."
    )

    @property
    def name(self) -> str:
        return "incomplete_procedure"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        steps_present: set[int] = set()
        staged: list[tuple] = []
        for addr in document.addresses:
            match = STEP_RE.search(addr.notes or "")
            if match:
                number = int(match.group(1))
                steps_present.add(number)
                staged.append((addr, number))

        if not staged:
            return []

        highest = max(steps_present)
        issues = []
        for addr, number in staged:
            if number + 1 in steps_present:
                continue  # the next step exists, nothing to report

            if number + 1 < highest:
                # A gap in the middle: steps 1 and 3 exist but 2 does not.
                reason = (
                    f"step {number + 1} is missing while step {highest} is present"
                )
            elif number == 1:
                # A lone opening step. How many steps a procedure *should* have
                # is unknowable, so only the "step 1 and nothing else" shape is
                # reported -- the last step of a longer run is left alone.
                reason = f"no step {number + 1} is present in this document"
            else:
                continue

            issues.append(
                ValidationResult(
                    code=addr.code,
                    severity=Severity.WARNING,
                    message=(
                        f"Address {addr.code!r} specifies step {number} of a staged "
                        f"tightening procedure, but {reason}. The procedure may be "
                        f"incomplete."
                    ),
                    validator=self.name,
                    expected=f"an entry for step {number + 1}",
                    actual=f"steps present: {sorted(steps_present)}",
                )
            )
        return issues
