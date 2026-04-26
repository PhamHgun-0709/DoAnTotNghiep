from dataclasses import dataclass


@dataclass(frozen=True)
class QualityThresholds:
    min_ctr: float = 0.01
    min_cvr: float = 0.02
    min_approved_conversion: float = 1.0


def quality_label(ctr: float, cvr: float, cpa: float, approved_conversion: float, cpa_median: float) -> str:
    score = 0

    if ctr >= 0.01:
        score += 1
    if cvr >= 0.02:
        score += 1
    if approved_conversion > 0 and cpa <= cpa_median:
        score += 1
    if approved_conversion >= 1.0:
        score += 1

    if score >= 3:
        return "good"
    if score == 2:
        return "average"
    return "bad"
