from dataclasses import dataclass


@dataclass(frozen=True)
class QualityThresholds:
    min_ctr: float = 0.01
    min_cvr: float = 0.02
    min_conversions: float = 1.0


def quality_label(ctr: float, cvr: float, cpa: float, conversions: float, cpa_median: float) -> str:
    score = 0

    if ctr >= 0.01:
        score += 1
    if cvr >= 0.02:
        score += 1
    if conversions > 0 and cpa <= cpa_median:
        score += 1
    if conversions >= 1.0:
        score += 1

    if score >= 3:
        return "good"
    if score == 2:
        return "average"
    return "bad"
