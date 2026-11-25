"""Mesin gamifikasi sisi anak (hanya untuk anak, DILARANG bocor ke parent report).

Aturan terkunci (Section 5 build prompt):
- XP: +10 per jawaban benar (tryout + drill)
- Bonus streak per tryout (masing-masing sekali per tryout):
  3 benar beruntun +5, 5 beruntun +10, 8 beruntun +15
- Bintang per tryout: >=90% = 3, 75-89% = 2, 60-74% = 1, <60% = 0
- Level (XP kumulatif):
  L1 0, L2 100, L3 250, L4 450, L5 700, L6 1000, L7 1400, L8 1900, L9 2500, L10 3200, lalu +800 per level
- Drill selesai: +5 XP per set drill yang diselesaikan
"""
from __future__ import annotations

XP_PER_CORRECT = 10
XP_DRILL_COMPLETE = 5
STREAK_BONUSES = ((3, 5), (5, 10), (8, 15))
LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200]


def stars_for_pct(pct: float) -> int:
    """Konversi persentase skor tryout menjadi 0..3 bintang."""
    if pct >= 90:
        return 3
    if pct >= 75:
        return 2
    if pct >= 60:
        return 1
    return 0


def max_correct_streak(is_correct_list: list[bool]) -> int:
    """Hitung rentetan jawaban benar terpanjang dalam satu tryout."""
    best = cur = 0
    for ok in is_correct_list:
        if ok:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def score_tryout_xp(is_correct_list: list[bool], pct: float) -> dict:
    """Hitung XP, bonus streak, dan bintang untuk satu tryout."""
    correct_count = sum(1 for ok in is_correct_list if ok)
    base_xp = correct_count * XP_PER_CORRECT
    best_streak = max_correct_streak(is_correct_list)
    milestones = []
    streak_bonus = 0
    for threshold, bonus in STREAK_BONUSES:
        if best_streak >= threshold:
            milestones.append({"streak": threshold, "bonus": bonus})
            streak_bonus += bonus
    return {
        "base_xp": base_xp,
        "streak_bonus": streak_bonus,
        "streak_milestones": milestones,
        "max_streak": best_streak,
        "total_xp": base_xp + streak_bonus,
        "stars": stars_for_pct(pct),
    }


def score_drill_xp(correct_count: int) -> dict:
    """Hitung XP untuk satu set drill yang diselesaikan."""
    c = max(0, int(correct_count or 0))
    base_xp = c * XP_PER_CORRECT
    return {
        "base_xp": base_xp,
        "completion_xp": XP_DRILL_COMPLETE,
        "total_xp": base_xp + XP_DRILL_COMPLETE,
    }


def threshold_for_level(level: int) -> int:
    """XP kumulatif minimum untuk mencapai `level` (1-based)."""
    if level <= 1:
        return 0
    if level <= len(LEVEL_THRESHOLDS):
        return LEVEL_THRESHOLDS[level - 1]
    return LEVEL_THRESHOLDS[-1] + 800 * (level - len(LEVEL_THRESHOLDS))


def level_info(total_xp: int) -> dict:
    """Hitung level aktif dan progres bar menuju level berikutnya."""
    xp = max(0, int(total_xp or 0))
    lvl = 1
    while xp >= threshold_for_level(lvl + 1):
        lvl += 1
    cur_min = threshold_for_level(lvl)
    next_min = threshold_for_level(lvl + 1)
    span = max(1, next_min - cur_min)
    in_lvl = xp - cur_min
    return {
        "level": lvl,
        "xp": xp,
        "level_min_xp": cur_min,
        "next_level_xp": next_min,
        "xp_in_level": in_lvl,
        "xp_to_next": next_min - xp,
        "progress_pct": min(100, round(100 * in_lvl / span)),
    }
