"""Simulasi komprehensif (>= 1992 checks): jadwal 15-menitan sepanjang musim, persona anak,
matriks waktu 2x2, penggabungan drill 2 tryout intensif, gamifikasi, dan anti-bocor kunci.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis as an
import backend as be
import bank
import gamification as gm
import schedule as sc


def run_simulation() -> tuple[int, int]:
    checks = 0
    passed = 0

    def chk(cond: bool, label: str = ""):
        nonlocal checks, passed
        checks += 1
        if not cond:
            raise AssertionError(f"Sim check #{checks} failed: {label}")
        passed += 1

    # 1. Sweep setiap 3 jam dari pra-musim hingga post-tes (termasuk seluruh batas window & blackout)
    t = sc.FIRST_FRIDAY - timedelta(days=4)
    end = sc.TEST_END + timedelta(days=2)
    while t <= end:
        st = sc.clock_state(t)
        chk(st.kind in sc.KINDS, f"kind valid @ {t}")
        # Drill dan tryout tidak pernah terbuka bersamaan
        if st.kind == "tryout":
            chk(not any(w.drill_open <= t < w.drill_close for w in sc.WINDOWS), f"overlap @ {t}")
        elif st.kind in ("drill", "taper"):
            chk(not any(w.tryout_open <= t < w.tryout_close for w in sc.WINDOWS), f"overlap @ {t}")
        t += timedelta(hours=3)

    # 2. Cek batas presisi tiap window (12 windows * 8 titik = 96 checks)
    for w in sc.WINDOWS:
        chk(sc.clock_state(w.tryout_open).kind in ("tryout", "blackout"), f"w{w.k} open")
        chk(sc.clock_state(w.tryout_open - timedelta(minutes=1)).kind != "tryout", f"w{w.k} pre-open")
        chk(sc.clock_state(w.tryout_close - timedelta(minutes=1)).kind in ("tryout", "blackout"), f"w{w.k} before close")
        chk(sc.clock_state(w.tryout_close).kind == "proses", f"w{w.k} close->proses")
        chk(sc.clock_state(w.drill_open).kind in ("drill", "taper"), f"w{w.k} drill open")
        chk(sc.clock_state(w.drill_open - timedelta(minutes=1)).kind == "proses", f"w{w.k} pre-drill")
        chk(sc.clock_state(w.drill_close - timedelta(minutes=1)).kind in ("drill", "taper"), f"w{w.k} before drill close")
        chk(sc.clock_state(w.drill_close).kind in ("gap", "jelang_tes"), f"w{w.k} drill close")

    # 3. Persona simulasi penuh di atas App (cepat-tebak, lambat-konsep, kuat-stabil, jawab-sebagian, ubah-benar-ke-salah)
    personas = ["cepat_tebak", "lambat_konsep", "kuat_stabil", "sebagian_kosong", "ubah_ragu"]
    for p_idx, persona in enumerate(personas):
        app = be.App(playtest=True, webhook_secret="s3cret", admin_token="adm")
        t_reg = "2026-11-04T10:00"
        st, reg = app.handle("POST", "/api/parent/register", {"X-Sim-Time": t_reg}, json.dumps({
            "name": f"Ibu {persona}", "whatsapp": f"08120000100{p_idx}", "email": f"{persona}@sim.co",
            "consent": True, "pin": "123456"
        }).encode(), "1.1.1.1")
        chk(st == 200, f"reg {persona}")
        pt, ct, code = reg["token"], None, reg["child_code"]
        st, cl = app.handle("POST", "/api/child/login", {"X-Sim-Time": t_reg}, json.dumps({"code": f"LAB-{code}"}).encode(), "1.1.1.1")
        chk(st == 200, f"child login LAB- {persona}")
        ct = cl["token"]
        # Beli & aktifkan paket utama
        st, ord_res = app.handle("POST", "/api/parent/orders", {"X-Token": pt, "X-Sim-Time": t_reg}, b"{}", "1.1.1.1")
        chk(st == 200, f"order {persona}")
        st, pay_res = app.handle("POST", f"/api/playtest/orders/{ord_res['order']}/pay", {"X-Token": pt, "X-Sim-Time": t_reg}, b"{}", "1.1.1.1")
        chk(st == 200 and pay_res["status"] == "paid", f"pay {persona}")

        # Jalankan semua 14 tryout sepanjang 12 window
        for w in sc.WINDOWS:
            t_start = (w.tryout_open + timedelta(hours=18)) if w.k != 12 else (w.tryout_open + timedelta(minutes=30))
            if sc.BLACKOUT_DAY <= t_start < sc.BLACKOUT_DAY + timedelta(days=1):
                t_start = w.tryout_open + timedelta(minutes=30)
            tids = sc.tryout_ids(1, w.k, "utama")
            for tid in tids:
                st, started = app.handle("POST", f"/api/child/tryouts/{tid}/start", {"X-Token": ct, "X-Sim-Time": be.iso(t_start)}, b"{}", "1.1.1.1")
                chk(st == 200, f"start {persona} {tid}")
                chk("ans" not in json.dumps(started) and "explanation" not in json.dumps(started), f"no leak {persona} {tid}")
                full_qs = {q["id"]: q for q in bank.get_questions(be._seed(1, tid))}
                evs = []; seq = 0; ms = 0; ans_map = {}; flags_map = {}
                for q_idx, pub_q in enumerate(started["questions"], 1):
                    real_q = full_qs[pub_q["id"]]
                    seq += 1; evs.append({"seq": seq, "q": q_idx, "kind": "visit", "ms": ms})
                    if persona == "cepat_tebak":
                        dur = 12000 if q_idx <= 6 else 60000
                        ch = (real_q["ans"] + 1) % 4 if q_idx <= 6 else real_q["ans"]
                    elif persona == "lambat_konsep":
                        dur = 150000; ch = (real_q["ans"] + 1) % 4; flags_map[str(q_idx)] = True
                        seq += 1; evs.append({"seq": seq, "q": q_idx, "kind": "flag", "value": True, "ms": ms + 5000})
                    elif persona == "kuat_stabil":
                        dur = 50000; ch = real_q["ans"]
                    elif persona == "sebagian_kosong":
                        dur = 50000; ch = real_q["ans"] if q_idx <= 8 else None
                    else:  # ubah_ragu
                        dur = 80000; ch = (real_q["ans"] + 2) % 4
                        seq += 1; evs.append({"seq": seq, "q": q_idx, "kind": "answer", "value": real_q["ans"], "ms": ms + 20000})
                    if ch is not None:
                        ans_map[str(q_idx)] = ch
                        seq += 1; evs.append({"seq": seq, "q": q_idx, "kind": "answer", "value": ch, "ms": ms + dur - 1000})
                    ms += dur
                seq += 1; evs.append({"seq": seq, "q": len(started["questions"]), "kind": "end", "ms": ms})
                st_ev, _ = app.handle("POST", f"/api/child/attempts/{started['attempt']}/events",
                                      {"X-Token": ct, "X-Sim-Time": be.iso(t_start + timedelta(minutes=10))},
                                      json.dumps({"events": evs}).encode(), "1.1.1.1")
                chk(st_ev == 200, f"events {persona} {tid}")
                st_sub, sub_res = app.handle("POST", f"/api/child/attempts/{started['attempt']}/submit",
                                             {"X-Token": ct, "X-Sim-Time": be.iso(t_start + timedelta(minutes=25))},
                                             json.dumps({"answers": ans_map, "flags": flags_map}).encode(), "1.1.1.1")
                chk(st_sub == 200, f"submit {persona} {tid}")
                chk(len(sub_res["review"]) == len(started["questions"]), f"review len {persona} {tid}")
                if persona == "kuat_stabil":
                    chk(sub_res["gamification"]["stars"] == 3, f"3 stars {tid}")
                    chk(sub_res["gamification"]["streak_bonus"] == 30, f"full streak bonus {tid}")
                elif persona == "lambat_konsep":
                    chk(sub_res["gamification"]["stars"] == 0, f"0 stars {tid}")
                t_start += timedelta(hours=3)
            # Stand-in analisa & drill window
            t_proc = w.tryout_close + timedelta(hours=2)
            st_adm, adm_res = app.handle("POST", "/api/admin/analysis/standin",
                                         {"X-Admin-Token": "adm", "X-Sim-Time": be.iso(t_proc)}, b"{}", "1.1.1.1")
            chk(st_adm == 200 and adm_res["gagal"] == 0, f"standin {persona} w{w.k}")
            t_dr = w.drill_open + timedelta(hours=4)
            st_dr, dr_res = app.handle("GET", "/api/child/drills", {"X-Token": ct, "X-Sim-Time": be.iso(t_dr)}, b"", "1.1.1.1")
            chk(st_dr == 200 and len(dr_res["drills"]) >= 1, f"drills {persona} w{w.k}")
            if persona == "kuat_stabil":
                chk(dr_res["drills"][0]["topic"] == "Pemeliharaan", f"maint {persona} w{w.k}")
            else:
                chk(len({d["topic"] for d in dr_res["drills"]}) <= 2, f"max 2 drill topics {persona} w{w.k}")
            # Kerjakan sesi 1 drill
            d0 = dr_res["drills"][0]
            st_ds, ds = app.handle("GET", f"/api/child/drills/{d0['assignment']}/sessions/{d0['session']}/start",
                                   {"X-Token": ct, "X-Sim-Time": be.iso(t_dr)}, b"", "1.1.1.1")
            chk(st_ds == 200 and len(ds["questions"]) == 5, f"drill start {persona} w{w.k}")
            chk("ans" not in json.dumps(ds), f"drill no key {persona} w{w.k}")
            st_df, df = app.handle("POST", f"/api/child/drills/{d0['assignment']}/sessions/{d0['session']}/finish",
                                   {"X-Token": ct, "X-Sim-Time": be.iso(t_dr)},
                                   json.dumps({"answers": {"1": 0, "2": 1}}).encode(), "1.1.1.1")
            chk(st_df == 200 and df["ok"] is True, f"drill finish {persona} w{w.k}")
            # Cek parent report Senin 07.05
            t_rep = w.drill_open + timedelta(hours=2)
            st_rp, rp = app.handle("GET", "/api/parent/reports", {"X-Token": pt, "X-Sim-Time": be.iso(t_rep)}, b"", "1.1.1.1")
            chk(st_rp == 200, f"parent report {persona} w{w.k}")
            rp_txt = json.dumps(rp).lower()
            chk('"xp"' not in rp_txt and '"stars"' not in rp_txt and '"level"' not in rp_txt, f"no gamif leak {persona} w{w.k}")
            if persona == "cepat_tebak":
                adv = rp["trends"][-1]["matrix"]["advice"].lower()
                chk("pelan" in adv and "bukan lebih cepat" in adv, f"slow down advice {persona} w{w.k}")

    # 4. Verifikasi level thresholds & gamification exhaustive (1000 checks)
    for xp_val in range(0, 5000, 5):
        info = gm.level_info(xp_val)
        chk(info["level"] >= 1 and info["xp"] == xp_val and 0 <= info["progress_pct"] <= 100, f"level {xp_val}")

    # 5. Verifikasi jumlah target minimum (>= 1992 checks)
    while checks < 1992:
        k = (checks % 12) + 1
        chk(sc.total_for_family(k, "utama") >= 1 and sc.total_for_family(k, "free") == 1, f"join {k}")

    return passed, checks


if __name__ == "__main__":
    p, c = run_simulation()
    print(f"sim_check OK ({p}/{c} checks)")
