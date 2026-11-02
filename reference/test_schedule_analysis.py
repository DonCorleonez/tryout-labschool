from datetime import datetime, timedelta

import pytest

import analysis as an
import schedule as sc

D = lambda s: datetime.fromisoformat(s).replace(tzinfo=sc.WIB)


def test_total_tryouts_is_14_in_12_windows():
    assert len(sc.WINDOWS) == 12
    assert sc.TOTAL_TRYOUTS == 14
    assert [w.n_tryouts for w in sc.WINDOWS] == [1] * 9 + [2, 2, 1]


def test_window_weekdays_and_hours():
    for w in sc.WINDOWS:
        assert w.friday.weekday() == 4                      # Jumat
        assert (w.tryout_open.hour, w.tryout_open.minute) == (17, 0)
        assert w.tryout_close.weekday() == 6 and w.tryout_close.hour == 16   # Minggu 16.00
        assert w.drill_open.weekday() == 0 and w.drill_open.hour == 6        # Senin 06.00
        assert w.drill_close.weekday() == 4 and w.drill_close.hour == 15     # Jumat 15.00


def test_drill_and_tryout_windows_never_overlap():
    spans = []
    for w in sc.WINDOWS:
        spans += [("t", w.tryout_open, w.tryout_close), ("d", w.drill_open, w.drill_close)]
    spans.sort(key=lambda s: s[1])
    for a, b in zip(spans, spans[1:]):
        assert a[2] <= b[1], (a, b)


def test_gap_between_drill_close_and_next_tryout_open_is_two_hours():
    for w, nxt in zip(sc.WINDOWS, sc.WINDOWS[1:]):
        assert nxt.tryout_open - w.drill_close == timedelta(hours=2)


def test_h_minus_7_is_sunday_24_jan_and_last_window_ends_there():
    h7 = sc.TEST_START - timedelta(days=7)
    assert (h7.month, h7.day, h7.weekday()) == (1, 24, 6)
    assert sc.WINDOWS[-1].tryout_close.date() == h7.date()


def test_intensive_windows_are_h23_to_h14():
    w10, w11 = sc.WINDOWS[9], sc.WINDOWS[10]
    assert (sc.TEST_START.date() - w10.friday.date()).days == 23
    assert (sc.TEST_START.date() - w11.friday.date()).days == 16
    assert w10.n_tryouts == w11.n_tryouts == 2


@pytest.mark.parametrize("when,kind", [
    ("2026-11-04T10:00", "pre"),
    ("2026-11-06T16:59", "pre"),
    ("2026-11-06T17:00", "tryout"),
    ("2026-11-08T15:59", "tryout"),
    ("2026-11-08T16:00", "proses"),
    ("2026-11-09T05:59", "proses"),
    ("2026-11-09T06:00", "drill"),
    ("2026-11-13T14:59", "drill"),
    ("2026-11-13T15:00", "gap"),
    ("2026-11-13T16:59", "gap"),
    ("2026-11-13T17:00", "tryout"),
    ("2027-01-23T10:00", "blackout"),
    ("2027-01-25T10:00", "taper"),
    ("2027-01-29T15:00", "jelang_tes"),
    ("2027-01-31T09:00", "hari_tes"),
    ("2027-01-31T13:00", "post"),
])
def test_clock_state(when, kind):
    assert sc.clock_state(D(when)).kind == kind


def test_exactly_one_state_every_15_minutes_and_never_both_open():
    t = sc.FIRST_FRIDAY - timedelta(days=3)
    end = sc.TEST_END + timedelta(days=1)
    seen = set()
    while t < end:
        st = sc.clock_state(t)
        assert st.kind in sc.KINDS
        seen.add(st.kind)
        t += timedelta(minutes=15)
    assert seen == set(sc.KINDS)


def test_join_rules_and_late_join_counts():
    # bergabung sebelum mulai -> diagnostik di jendela 1, lalu kalender kohort
    assert sc.join_window(D("2026-11-02T10:00")) == 1
    assert sc.total_for_family(1) == 14
    # bergabung Sabtu saat jendela 2 terbuka -> diagnostik di jendela 2
    assert sc.join_window(D("2026-11-14T10:00")) == 2
    # bergabung setelah gate 9 Des (hari Sabtu 12 Des, jendela 6): 1 diagnostik + 8 tryout = 9
    k = sc.join_window(D("2026-12-12T10:00"))
    assert k == 6
    assert sc.total_for_family(k) == 1 + 8
    # paket gratis hanya diagnostik
    assert sc.total_for_family(1, "free") == 1


def test_no_rollover_for_missed_windows():
    assert sc.tryout_ids(6, 3) == []              # sebelum bergabung: tidak digulung
    assert sc.tryout_ids(6, 6) == ["DIAG"]
    assert sc.tryout_ids(6, 10) == ["TO10-1", "TO10-2"]


def test_second_tryout_requires_first_submitted():
    ids = ["TO10-1", "TO10-2"]
    assert sc.can_open_tryout(ids, set(), "TO10-1")
    assert not sc.can_open_tryout(ids, set(), "TO10-2")
    assert sc.can_open_tryout(ids, {"TO10-1"}, "TO10-2")
    assert not sc.can_open_tryout(ids, set(), "TO99")


# ---------------- analysis ----------------

def A(qid, topic, ok, sec, flagged=False, subject="Matematika", chosen=None):
    return an.Answer(qid, subject, topic, 1, (1 if ok else 2) if chosen is None else chosen, sec, flagged)


def test_score_is_binary_and_deterministic():
    ans = [A("1", "Pecahan", True, 60), A("2", "Pecahan", False, 60), A("3", "KPK", True, 60),
           an.Answer("4", "Matematika", "KPK", 1, None, 0)]
    s = an.score(ans)
    assert (s["correct"], s["total"], s["pct"]) == (2, 4, 50.0)
    assert s["topic"]["Pecahan"] == {"c": 1, "t": 2}
    assert s["topic"]["KPK"] == {"c": 1, "t": 2}


def test_classify_patterns():
    base = [A(str(i), "T", True, 100) for i in range(7)]               # median 100
    fast_wrong = A("fw", "T", False, 20)                                # < 0.5 median, tidak ragu
    slow_wrong = A("sw", "T", False, 200)                               # > 1.5 median
    flagged_wrong = A("fl", "T", False, 90, flagged=True)
    slow_right = A("sr", "T", True, 200)
    empty = an.Answer("e", "Matematika", "T", 1, None, 10)
    tags = {c["qid"]: c["tag"] for c in an.classify(base + [fast_wrong, slow_wrong, flagged_wrong, slow_right, empty])}
    assert tags["fw"] == "cepat_salah"
    assert tags["sw"] == "konsep"
    assert tags["fl"] == "konsep"
    assert tags["sr"] == "benar_lambat"
    assert tags["e"] == "kosong"
    assert tags["0"] == "benar"


@pytest.mark.parametrize("pct,avg,cell", [
    (85, 90, "efisien"),
    (85, 160, "paham_belum_lancar"),
    (50, 90, "terburu_buru"),
    (50, 160, "konsep_belum_paham"),
])
def test_time_matrix(pct, avg, cell):
    assert an.time_matrix(pct, avg)["cell"] == cell


def test_bad_and_fast_never_advises_faster():
    adv = an.time_matrix(40, 60)["advice"].lower()
    assert "pelan" in adv and "lebih cepat" in adv and "bukan lebih cepat" in adv


def test_stamina_drop():
    good = [A(str(i), "T", True, 60) for i in range(6)]
    bad = [A(str(i), "T", False, 60) for i in range(6, 12)]
    assert an.stamina_drop(good + bad)
    assert not an.stamina_drop(good + good)
    assert not an.stamina_drop(good[:3])        # terlalu sedikit data


def test_stamina_ignores_blank_and_blank_tail_is_separate():
    good = [A(str(i), "T", True, 60) for i in range(6)]
    blank = [an.Answer(str(i), "S", "T", 0, None, 60) for i in range(6, 12)]
    assert not an.stamina_drop(good + blank)          # kosong di akhir bukan kelelahan
    assert an.blank_tail(good + blank) and not an.blank_tail(good + good)


def test_weak_topics_sorted_and_severity():
    w = an.weak_topics({"A": {"c": 3, "t": 7}, "B": {"c": 4, "t": 7}, "C": {"c": 6, "t": 7}})
    assert [x["topic"] for x in w] == ["A", "B"]
    assert w[0]["severity"] == "berat" and w[1]["severity"] == "sedang"


def test_merge_drill_specs_caps_at_two_and_keeps_worst():
    s1 = [{"topic": "X", "pct": 40}, {"topic": "Y", "pct": 60}]
    s2 = [{"topic": "X", "pct": 30}, {"topic": "Z", "pct": 50}]
    merged = an.merge_drill_specs([s1, s2])
    assert [m["topic"] for m in merged] == ["X", "Z"]
    assert merged[0]["pct"] == 30
    assert len(an.merge_drill_specs([s1, s2], limit=1)) == 1


@pytest.mark.parametrize("pcts,weak,label", [
    ([55, 58], False, "Belum Siap"),
    ([70, 74], True, "Mengejar"),
    ([82, 86], False, "Siap Diuji"),
    ([82, 86], True, "Mengejar"),
    ([], False, "Belum Siap"),
])
def test_readiness_status(pcts, weak, label):
    assert an.readiness_status(pcts, weak) == label


def test_clean_seconds_removes_idle_and_caps():
    assert an.clean_seconds(100, 30) == 70
    assert an.clean_seconds(5000, 0) == 600
    assert an.clean_seconds(10, 50) == 0
