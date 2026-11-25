/* Ruang siswa: masuk -> beranda -> tryout/drill -> periksa -> hasil -> laporan -> buku salah.
 * Semua keputusan akses ada di server; layar ini hanya menampilkan apa yang dikembalikan API.
 * Tidak ada kunci jawaban di browser sebelum submit. */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const app = $('#app');
  const clockEl = $('#clock');
  const toastEl = $('#toast');
  const levelBarEl = $('#level-bar');
  const lvlBadgeEl = $('#lvl-badge');
  const xpFillEl = $('#xp-fill');
  const xpTextEl = $('#xp-text');
  const starBadgeEl = $('#star-badge');
  const tabBarEl = $('#tab-bar');
  const tabBsCountEl = $('#tab-bs-count');

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
  const L = 'ABCD';

  // ---- jam: mode playtest boleh ?sim=2026-11-06T18:00 (server mengabaikan header ini di produksi) ----
  const qs = new URLSearchParams(location.search);
  const simStart = qs.get('sim') || sessionStorage.getItem('sim');
  if (qs.get('sim')) sessionStorage.setItem('sim', qs.get('sim'));
  const loadedAt = Date.now();
  const simBase = simStart ? Date.parse(simStart + (/[Z+]/.test(simStart.slice(10)) ? '' : '+07:00')) : null;
  const now = () => (simBase ? simBase + (Date.now() - loadedAt) : Date.now());
  const simHeader = simBase ? () => new Date(now() + 7 * 3600e3).toISOString().slice(0, 19) : null;

  const tokenKey = 'childToken';
  const api = window.Api('', () => sessionStorage.getItem(tokenKey), simHeader);
  const toast = (m) => {
    toastEl.textContent = m;
    toastEl.classList.add('on');
    clearTimeout(toast.t);
    toast.t = setTimeout(() => toastEl.classList.remove('on'), 2600);
  };
  const fmtTime = (iso) => new Date(iso).toLocaleString('id-ID', {
    weekday: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta'
  });
  const fmtDateShort = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString('id-ID', {
        day: 'numeric', month: 'short', timeZone: 'Asia/Jakarta'
      });
    } catch (e) { return ''; }
  };

  const MSG = {
    kode_tidak_dikenali: 'Kode belum dikenali. Periksa lagi atau tanya orang tua.',
    terlalu_sering: 'Terlalu banyak percobaan. Tunggu 10 menit, lalu coba lagi.',
    akses_dinonaktifkan: 'Akses sedang dinonaktifkan. Minta orang tua menghubungi kami.',
    jendela_tertutup: 'Tryout sedang tidak dibuka sekarang.',
    sudah_dikerjakan: 'Tryout ini sudah dikerjakan.',
    kumpulkan_tryout_pertama_dulu: 'Kumpulkan tryout pertama dulu, lalu tryout kedua terbuka.',
    paket_gratis_hanya_diagnostik: 'Paket gratis berisi satu diagnostik.',
    waktu_habis: 'Waktu pengerjaan sudah habis.',
    selesaikan_sesi_sebelumnya: 'Selesaikan sesi drill sebelumnya dulu, ya.',
    sudah_selesai: 'Sesi drill ini sudah selesai.',
  };
  const msg = (e) => MSG[e] || 'Ada gangguan. Coba lagi sebentar.';

  const CLOCK = {
    pre: 'Tryout pertama dibuka Jumat 6 November pukul 17.00.',
    tryout: 'Jendela tryout sedang dibuka.',
    blackout: 'Hari ini ada simulasi resmi sekolah, jadi tryout di sini ditutup.',
    drill: 'Minggu ini waktunya drill singkat.',
    taper: 'Minggu terakhir: review Buku Salah dan latihan pemeliharaan ringan saja.',
    gap: 'Jeda sebentar. Tryout dibuka Jumat 17.00.',
    proses: 'Hasil sedang diolah. Drill dibuka Senin pagi.',
    jelang_tes: 'Tes sudah dekat. Istirahat cukup, ya.',
    hari_tes: 'Hari ini hari tes. Semoga lancar!',
    post: 'Musim tryout sudah selesai.',
  };

  const tryoutLabel = (tid) => (tid === 'DIAG' ? 'Diagnostik' : `Tryout ${String(tid).split('-')[1] || tid}`.trim());

  // ---- state header gamifikasi & chrome ----
  const headerState = {
    level: 1, xp: 0, progress_pct: 0, stars_total: 0, buku_salah_count: 0,
  };

  function updateHeaderStats(gamification, bukuSalahCount) {
    if (gamification) {
      const lvl = gamification.level && typeof gamification.level === 'object' ? gamification.level : gamification;
      if (lvl.level != null) headerState.level = lvl.level;
      if (lvl.xp != null) headerState.xp = lvl.xp;
      if (lvl.progress_pct != null) headerState.progress_pct = lvl.progress_pct;
      if (gamification.stars_total != null) headerState.stars_total = gamification.stars_total;
    }
    if (typeof bukuSalahCount === 'number') {
      headerState.buku_salah_count = bukuSalahCount;
    }
    if (lvlBadgeEl) lvlBadgeEl.textContent = `Level ${headerState.level}`;
    if (xpFillEl) xpFillEl.style.width = `${Math.max(0, Math.min(100, headerState.progress_pct))}%`;
    if (xpTextEl) xpTextEl.textContent = `${headerState.xp} XP`;
    if (starBadgeEl) starBadgeEl.textContent = `★ ${headerState.stars_total}`;
    if (tabBsCountEl) {
      tabBsCountEl.textContent = String(headerState.buku_salah_count);
      tabBsCountEl.hidden = headerState.buku_salah_count <= 0;
    }
  }

  function syncChrome(mode, activeTab) {
    if (mode === 'login') {
      levelBarEl.hidden = true;
      tabBarEl.hidden = true;
      clockEl.textContent = '';
      clockEl.classList.remove('low');
    } else if (mode === 'player') {
      levelBarEl.hidden = true;
      tabBarEl.hidden = true;
    } else {
      levelBarEl.hidden = false;
      tabBarEl.hidden = false;
      clockEl.textContent = '';
      clockEl.classList.remove('low');
      tabBarEl.querySelectorAll('.tab-item').forEach((el) => {
        const isActive = el.dataset.tab === activeTab;
        el.classList.toggle('active', isActive);
        if (isActive) el.setAttribute('aria-current', 'page');
        else el.removeAttribute('aria-current');
      });
    }
  }

  function renderStars(count, sizeClass) {
    const n = Math.max(0, Math.min(3, Number(count || 0)));
    return `<span class="stars-row ${sizeClass || ''}" aria-label="${n} dari 3 bintang">${
      [1, 2, 3].map((i) => `<span class="star-slot ${i <= n ? 'on' : ''}" aria-hidden="true">★</span>`).join('')
    }</span>`;
  }

  function renderLevelCard(lvl) {
    if (!lvl) return '';
    const span = Math.max(1, (lvl.next_level_xp || 100) - (lvl.level_min_xp || 0));
    const inLvl = lvl.xp_in_level != null ? lvl.xp_in_level : 0;
    const pct = Math.max(0, Math.min(100, lvl.progress_pct || 0));
    return `<div class="card level-card">
      <div class="row spread">
        <div>
          <span class="lvl-pill">Level ${lvl.level}</span>
          <strong style="margin-left:8px">${lvl.xp} XP total</strong>
        </div>
        <span class="muted">${lvl.xp_to_next} XP lagi ke Level ${lvl.level + 1}</span>
      </div>
      <div class="level-meter" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" aria-label="Progres level">
        <span style="width:${pct}%"></span>
      </div>
      <div class="row spread muted" style="font-size:.86rem">
        <span>Progres level ini: ${inLvl} / ${span} XP</span>
        <span>${pct}%</span>
      </div>
    </div>`;
  }

  // ---- timer & cleanup ----
  let timer = null;
  let routeCleanup = null;
  const stopTimer = () => {
    if (timer) clearInterval(timer);
    timer = null;
    clockEl.classList.remove('low');
  };
  const cleanupActive = () => {
    stopTimer();
    document.onkeydown = null;
    if (routeCleanup) {
      try { routeCleanup(); } catch (e) { /* abaikan */ }
      routeCleanup = null;
    }
  };

  // ---------------- router ----------------
  function go(hash) { if (location.hash !== hash) location.hash = hash; else route(); }
  window.addEventListener('hashchange', route);
  function route() {
    cleanupActive();
    const h = location.hash.replace(/^#\/?/, '').split('/');
    if (!sessionStorage.getItem(tokenKey)) return viewLogin();
    if (h[0] === 'tryout' && h[1]) return viewTryout(h[1]);
    if (h[0] === 'hasil' && h[1]) return viewResult(h[1]);
    if (h[0] === 'laporan') return viewReport();
    if (h[0] === 'drill' && h[1] && h[2]) return viewDrillPlayer(h[1], h[2]);
    if (h[0] === 'drill') return viewDrillList();
    if (h[0] === 'buku-salah') return viewBukuSalah();
    return viewHome();
  }
  function render(html) {
    app.innerHTML = html;
    app.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  async function refreshHeaderInBackground() {
    try {
      const r = await api.get('/api/child/home');
      if (r.status === 200 && r.json) {
        updateHeaderStats(r.json.gamification, r.json.buku_salah_count);
      }
    } catch (e) { /* abaikan */ }
  }

  // ---------------- masuk ----------------
  function formatChildCode(rawInput) {
    const raw = String(rawInput || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (raw.startsWith('LAB') && raw.length > 3) {
      const rest = raw.slice(3, 11);
      return 'LAB-' + (rest.length > 4 ? rest.slice(0, 4) + '-' + rest.slice(4) : rest);
    }
    if (raw === 'LAB' && String(rawInput || '').toUpperCase().includes('LAB-')) {
      return 'LAB-';
    }
    if (raw === 'LAB') return 'LAB';
    const v = raw.slice(0, 8);
    return v.length > 4 ? v.slice(0, 4) + '-' + v.slice(4) : v;
  }

  function viewLogin() {
    syncChrome('login');
    render(`<div class="card hero-card">
        <h1>Masuk Ruang Tryout</h1>
        <p class="muted">Ketik kode siswa yang diberikan orang tua (format <strong>ABCD-1234</strong> atau <strong>LAB-ABCD-1234</strong>).</p>
        <form id="f" autocomplete="off">
          <label for="code"><strong>Kode siswa</strong></label><br>
          <input id="code" type="text" inputmode="text" placeholder="ABCD-1234" maxlength="13" required aria-describedby="e">
          <div id="e" class="err" hidden></div>
          <p style="margin-top:14px"><button class="primary" type="submit">Masuk</button></p>
        </form>
      </div>`);
    const code = $('#code'), err = $('#e');
    code.addEventListener('input', () => {
      code.value = formatChildCode(code.value);
    });
    $('#f').addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const b = ev.submitter || $('button', ev.target);
      b.disabled = true;
      err.hidden = true;
      try {
        const normalized = formatChildCode(code.value);
        code.value = normalized;
        const r = await api.post('/api/child/login', { code: normalized });
        if (r.status === 200) {
          sessionStorage.setItem(tokenKey, r.json.token);
          go('#/beranda');
          return;
        }
        err.textContent = msg(r.json && r.json.error);
        err.hidden = false;
      } catch (e) {
        err.textContent = 'Tidak tersambung ke internet. Coba lagi.';
        err.hidden = false;
      }
      b.disabled = false;
    });
    code.focus();
  }

  // ---------------- season map helper ----------------
  function renderSeasonMap(mapData) {
    if (!mapData || !Array.isArray(mapData.windows) || !mapData.windows.length) return '';
    const phases = [
      { key: 'Diagnostik', label: 'Diagnostik' },
      { key: 'Fondasi', label: 'Fondasi' },
      { key: 'Akselerasi', label: 'Akselerasi' },
      { key: 'Intensif', label: 'Intensif' },
      { key: 'Gladi bersih', label: 'Taper' },
    ];
    const currentWin = mapData.windows.find((w) => w.is_current);
    const activePhase = currentWin ? currentWin.phase : '';

    const phaseStrip = `<div class="phase-strip" aria-label="Tahapan musim latihan">${
      phases.map((p, idx) => `<span class="phase-chip ${p.key === activePhase ? 'active' : ''}">${esc(p.label)}</span>${idx < phases.length - 1 ? '<span class="muted" aria-hidden="true">→</span>' : ''}`).join('')
    }</div>`;

    const nodes = mapData.windows.map((w) => {
      const allDone = w.tryouts.length > 0 && w.tryouts.every((t) => t.state === 'selesai');
      const maxStars = w.tryouts.reduce((acc, t) => Math.max(acc, Number(t.stars || 0)), 0);
      const cls = ['win-node', w.is_current ? 'current' : '', allDone ? 'done' : '', w.is_taper ? 'taper' : ''].filter(Boolean).join(' ');
      const statusText = w.tryouts.length === 0
        ? 'Tidak ada'
        : allDone
          ? `${'★'.repeat(maxStars || 1)}`
          : w.is_current
            ? 'Aktif'
            : 'Terjadwal';
      const phaseLbl = w.is_taper ? 'Taper' : w.phase;
      return `<div class="${cls}">
        <div class="win-top"><span>M${w.window}</span><span class="${allDone ? 'win-stars' : 'muted'}">${esc(statusText)}</span></div>
        <div class="win-phase">${esc(phaseLbl)} · ${w.n_tryouts} tryout</div>
      </div>`;
    }).join('');

    return `<section class="card">
      <div class="row spread"><h2 style="margin:0">Peta Musim Latihan</h2><span class="pill">${mapData.plan === 'free' ? 'Gratis' : 'Utama'}</span></div>
      ${phaseStrip}
      <div class="season-grid">${nodes}</div>
    </section>`;
  }

  // ---------------- beranda ----------------
  async function viewHome() {
    syncChrome('shell', 'beranda');
    render('<p class="muted">Memuat…</p>');
    let r, mapRes;
    try {
      [r, mapRes] = await Promise.all([
        api.get('/api/child/home'),
        api.get('/api/child/season-map').catch(() => null),
      ]);
    } catch (e) {
      return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), ($('#rt').onclick = viewHome);
    }
    if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
    if (r.status !== 200) return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div>`);

    const h = r.json;
    const mapData = mapRes && mapRes.status === 200 ? mapRes.json : null;
    updateHeaderStats(h.gamification, h.buku_salah_count);

    const historyByTid = {};
    (h.history || []).forEach((item) => {
      if (!historyByTid[item.tryout_id]) historyByTid[item.tryout_id] = item;
    });

    const tryouts = (h.tryouts || []).map((t, i) => {
      const name = tryoutLabel(t.id);
      const second = i > 0 ? '<p class="muted" style="margin:8px 0 0">Dianjurkan, bukan keharusan. Terbuka setelah tryout sebelumnya dikumpulkan.</p>' : '';
      const past = historyByTid[t.id];
      const act = {
        siap: `<button class="primary" data-start="${esc(t.id)}">Mulai</button>`,
        berjalan: `<button class="primary" data-start="${esc(t.id)}">Lanjutkan</button>`,
        selesai: `<span class="row"><span class="pill done">✓ Sudah dikumpulkan</span>${past ? `<a class="btn ghost" href="#/hasil/${esc(past.attempt)}">Lihat hasil</a>` : ''}</span>`,
        terkunci: '<span class="pill lock">Belum terbuka</span>',
        terlewat: '<span class="pill lock">Waktu sudah habis</span>',
      }[t.state] || '';
      return `<div class="card"><div class="row spread"><strong>${esc(name)}</strong>${act}</div>${t.state === 'terkunci' ? second : ''}</div>`;
    }).join('');

    const drills = (h.drills || []).map((d) => {
      const act = d.state === 'selesai'
        ? '<span class="pill done">✓ Selesai</span>'
        : d.state === 'siap'
          ? `<a class="btn primary" href="#/drill/${d.assignment}/${d.session}">Mulai Drill</a>`
          : '<span class="pill lock">Setelah sesi sebelumnya</span>';
      return `<div class="card row spread"><span><strong>${esc(d.topic)}</strong> · sesi ${d.session}</span>${act}</div>`;
    }).join('');

    const taperBanner = h.taper
      ? `<div class="taper-banner" role="note">
          <span aria-hidden="true" style="font-size:1.5rem">🌿</span>
          <div><strong>Mode Minggu Terakhir (Taper)</strong><span>Minggu terakhir: review Buku Salah dan latihan pemeliharaan ringan saja.</span></div>
        </div>`
      : '';

    render(`<div class="card hero-card">
        <div class="row spread">
          <div>
            <h1 style="margin:0">Halo!</h1>
            <p class="muted" style="margin:4px 0 0">Level ${headerState.level} · ${headerState.xp} XP · ★ ${headerState.stars_total}</p>
          </div>
          <a class="btn sun-btn" href="#/buku-salah">Buku Salah (${Number(h.buku_salah_count || 0)})</a>
        </div>
      </div>
      <p class="note">${esc(CLOCK[h.clock] || '')}${h.closes_at ? ` Ditutup ${esc(fmtTime(h.closes_at))}.` : ''}</p>
      ${taperBanner}
      ${h.tryouts.length ? '<h2>Tryout</h2>' + tryouts : ''}
      ${h.clock === 'tryout' && !h.tryouts.length ? '<p class="muted">Tidak ada tryout untukmu di jendela ini.</p>' : ''}
      ${h.drills && h.drills.length ? '<h2>Drill minggu ini</h2><p class="muted">Dianjurkan, 10–15 menit per sesi.</p>' + drills : ''}
      ${h.pending ? '<p class="muted">Drill sedang disiapkan dari hasil tryout.</p>' : ''}
      ${renderSeasonMap(mapData)}
      <div class="row" style="margin-top:18px">
        <a class="btn" href="#/laporan">Lihat Report &amp; Arsip</a>
        <a class="btn" href="#/drill">Menu Drill</a>
        <button id="out" class="ghost">Keluar</button>
      </div>`);

    app.querySelectorAll('[data-start]').forEach((b) => b.addEventListener('click', () => go('#/tryout/' + b.dataset.start)));
    $('#out').onclick = () => { sessionStorage.removeItem(tokenKey); go('#/masuk'); };
  }

  // ---------------- tryout ----------------
  async function viewTryout(tid) {
    syncChrome('player');
    render('<p class="muted">Menyiapkan soal…</p>');
    let r;
    try {
      r = await api.post('/api/child/tryouts/' + encodeURIComponent(tid) + '/start');
    } catch (e) {
      return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), ($('#rt').onclick = () => viewTryout(tid));
    }
    if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
    if (r.status !== 200) {
      return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div><p><a class="btn" href="#/beranda">Kembali</a></p>`);
    }
    const data = r.json, Q = data.questions;
    sessionStorage.setItem('q:' + data.attempt, JSON.stringify(Q));
    const run = new window.Runner({ api, attempt: data.attempt, questions: Q, deadlineAt: data.deadline_at, storage: window.localStorage, now });
    run.attachVisibility(document);
    if (data.resumed) toast('Melanjutkan dari jawaban terakhir.');
    let cur = run.state.cur || 1, sending = false;
    const flushSoon = () => run.flush().catch(() => {});
    const fl = setInterval(flushSoon, 20000);
    const onVis = () => { if (document.hidden) flushSoon(); };
    document.addEventListener('visibilitychange', onVis);

    routeCleanup = () => {
      clearInterval(fl);
      document.removeEventListener('visibilitychange', onVis);
    };

    function tick() {
      const s = run.remainingSec(), m = Math.floor(s / 60);
      clockEl.textContent = `${String(Math.floor(m / 60))}:${String(m % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
      clockEl.setAttribute('aria-label', `Sisa waktu ${m} menit`);
      clockEl.classList.toggle('low', s <= 300);
      if (s <= 0 && !sending) { stopTimer(); clearInterval(fl); doSubmit(true); }
    }
    stopTimer();
    timer = setInterval(tick, 1000);
    tick();

    function show(n) {
      cur = Math.min(Math.max(1, n), Q.length);
      run.visit(cur);
      const q = Q[cur - 1], a = run.state.answers[cur], f = !!run.state.flags[cur];
      render(`<div class="qhead"><span>Soal <strong>${cur}</strong> dari ${Q.length}</span><span class="pill">${esc(q.subject)}</span></div>
        ${q.passage ? `<div class="passage" aria-label="Bacaan">${esc(q.passage.text)}</div>` : ''}
        <div class="stem" id="stem">${esc(q.q)}</div>
        <div class="opts" role="radiogroup" aria-labelledby="stem">
          ${q.opts.map((o, i) => `<button class="opt" role="radio" aria-checked="${a === i}" data-i="${i}"><span class="k">${L[i]}</span><span>${esc(o)}</span></button>`).join('')}
        </div>
        <p class="muted small-warn">Layar kecil: tryout lebih nyaman di laptop atau tablet (tes asli memakai laptop).</p>
        <div class="bar">
          <button id="prev" ${cur === 1 ? 'disabled' : ''} aria-label="Soal sebelumnya">‹<span class="lbl"> Sebelumnya</span></button>
          <div class="mid">
            <button id="flag" class="flag" aria-pressed="${f}">${f ? '◆ Ragu' : '◇ Ragu'}</button>
            <button id="grid" aria-label="Daftar soal">☰ ${run.progress().answered}/${Q.length}</button>
          </div>
          ${cur === Q.length ? '<button id="check" class="primary">Periksa</button>' : '<button id="next" class="primary" aria-label="Soal berikutnya"><span class="lbl">Berikutnya </span>›</button>'}
        </div>`);
      app.querySelectorAll('.opt').forEach((b) => b.addEventListener('click', () => pick(+b.dataset.i)));
      $('#prev').onclick = () => show(cur - 1);
      if ($('#next')) $('#next').onclick = () => show(cur + 1);
      if ($('#check')) $('#check').onclick = viewCheck;
      $('#flag').onclick = () => { run.toggleFlag(cur); show(cur); };
      $('#grid').onclick = openGrid;
    }

    function pick(i) {
      run.answer(cur, i);
      app.querySelectorAll('.opt').forEach((b) => b.setAttribute('aria-checked', String(+b.dataset.i === i)));
      const g = $('#grid');
      if (g) g.textContent = `☰ ${run.progress().answered}/${Q.length}`;
    }

    function gridHtml() {
      return `<div class="legend"><span><i class="a"></i>Sudah dijawab</span><span><i></i>Belum dijawab</span><span><i class="f"></i>Ragu-ragu</span></div>
        <div class="grid">${Q.map((_, i) => {
          const n = i + 1, ans = run.state.answers[n] != null, f = run.state.flags[n];
          return `<button class="cell ${ans ? 'ans' : ''} ${n === cur ? 'cur' : ''}" data-n="${n}" aria-label="Soal ${n}${ans ? ', sudah dijawab' : ', belum dijawab'}${f ? ', ragu-ragu' : ''}">${n}${f ? '<span class="fm" aria-hidden="true"></span>' : ''}</button>`;
        }).join('')}</div>`;
    }

    function openGrid() {
      const ov = document.createElement('div');
      ov.className = 'overlay';
      ov.innerHTML = `<div class="sheet" role="dialog" aria-modal="true" aria-label="Daftar soal">${gridHtml()}<p class="row spread" style="margin-top:16px"><button id="close">Tutup</button><button id="g-check" class="primary">Periksa &amp; kumpulkan</button></p></div>`;
      document.body.appendChild(ov);
      const close = () => ov.remove();
      ov.addEventListener('click', (e) => { if (e.target === ov) close(); });
      ov.querySelectorAll('.cell').forEach((b) => b.addEventListener('click', () => { close(); show(+b.dataset.n); }));
      $('#close', ov).onclick = close;
      $('#g-check', ov).onclick = () => { close(); viewCheck(); };
      $('.cell', ov).focus();
    }

    function viewCheck() {
      const p = run.progress();
      const blank = Q.map((_, i) => i + 1).filter((n) => run.state.answers[n] == null);
      const flg = Q.map((_, i) => i + 1).filter((n) => run.state.flags[n]);
      const links = (arr) => arr.map((n) => `<button class="cell" data-n="${n}">${n}</button>`).join(' ');
      render(`<h1>Periksa sebelum mengumpulkan</h1>
        <div class="card"><p><strong>${p.answered}</strong> dari ${p.total} soal sudah dijawab.</p>
        ${blank.length ? `<p>Belum dijawab (${blank.length}):</p><div class="row">${links(blank)}</div>` : '<p>Semua soal sudah dijawab.</p>'}
        ${flg.length ? `<p>Ditandai ragu-ragu (${flg.length}):</p><div class="row">${links(flg)}</div>` : ''}</div>
        <p class="muted">Setelah dikumpulkan, jawaban tidak bisa diubah. Waktu masih berjalan sampai kamu menekan Kumpulkan.</p>
        <div id="st" role="status" aria-live="polite"></div>
        <p class="row"><button id="back">Kembali ke soal</button><button id="send" class="primary">Kumpulkan</button></p>`);
      app.querySelectorAll('.cell').forEach((b) => b.addEventListener('click', () => show(+b.dataset.n)));
      $('#back').onclick = () => show(cur);
      $('#send').onclick = () => doSubmit(false);
    }

    async function doSubmit(auto) {
      if (sending) return;
      sending = true;
      if (auto) {
        render('<h1>Waktu habis</h1><p>Jawabanmu sedang dikumpulkan otomatis…</p><div id="st" role="status" aria-live="polite"></div><p><button id="send" class="primary" disabled>Mengirim…</button></p>');
      }
      const btn = $('#send'), st = $('#st');
      if (btn) { btn.disabled = true; btn.textContent = 'Mengirim…'; }
      const res = await run.submit();
      sending = false;
      if (res.ok) {
        stopTimer();
        clearInterval(fl);
        sessionStorage.setItem('r:' + data.attempt, JSON.stringify(res.result));
        run.clear();
        if (btn) btn.textContent = 'Terkirim ✓';
        return go('#/hasil/' + data.attempt);
      }
      if (res.closed) {
        stopTimer();
        clearInterval(fl);
        return render(`<h1>Tidak bisa dikumpulkan</h1><div class="err">${esc(msg(res.error))}</div><p><a class="btn" href="#/beranda">Ke beranda</a></p>`);
      }
      if (st) st.innerHTML = '<div class="err">Gagal terkirim. Jawabanmu aman tersimpan di perangkat ini. Periksa internet, lalu tekan Coba lagi.</div>';
      if (btn) { btn.disabled = false; btn.textContent = 'Coba lagi'; btn.onclick = () => doSubmit(auto); }
    }

    document.onkeydown = (e) => {
      if (!location.hash.startsWith('#/tryout') || e.ctrlKey || e.metaKey || e.altKey || document.querySelector('.overlay') || !$('.opts')) return;
      const k = e.key.toUpperCase();
      const i = 'ABCD'.indexOf(k) >= 0 ? 'ABCD'.indexOf(k) : '1234'.indexOf(k);
      if (i >= 0 && k.length === 1) { pick(i); e.preventDefault(); }
      else if (k === 'N' || e.key === 'ArrowRight') {
        if (e.key === 'ArrowRight') e.preventDefault();
        if (cur < Q.length) show(cur + 1);
      } else if (k === 'P' || e.key === 'ArrowLeft') {
        if (e.key === 'ArrowLeft') e.preventDefault();
        if (cur > 1) show(cur - 1);
      }
    };
    show(cur);
  }

  // ---------------- hasil (langsung & arsip) ----------------
  async function viewResult(att) {
    syncChrome('shell', 'laporan');
    let res = JSON.parse(sessionStorage.getItem('r:' + att) || 'null');
    let Q = JSON.parse(sessionStorage.getItem('q:' + att) || 'null');

    if (!res) {
      render('<p class="muted">Memuat hasil tryout…</p>');
      try {
        const r = await api.get('/api/child/attempts/' + encodeURIComponent(att) + '/result');
        if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
        if (r.status === 200 && r.json) {
          res = r.json;
          if (!Q && Array.isArray(res.questions)) Q = res.questions;
          sessionStorage.setItem('r:' + att, JSON.stringify(res));
          if (Q) sessionStorage.setItem('q:' + att, JSON.stringify(Q));
        }
      } catch (e) { /* fallback ke tampilan tidak ada */ }
    }

    if (!res) {
      return render('<h1>Hasil belum tersedia</h1><p class="muted">Jawabanmu sudah tersimpan, atau hasil tidak ditemukan.</p><p class="row"><a class="btn primary" href="#/beranda">Ke beranda</a><a class="btn" href="#/laporan">Lihat Report</a></p>');
    }

    if (!Q && Array.isArray(res.questions)) Q = res.questions;
    const s = res.score;
    const g = res.gamification || {};
    if (g.level) updateHeaderStats(g);
    refreshHeaderInBackground();

    const stars = g.stars != null ? g.stars : (s.pct >= 90 ? 3 : s.pct >= 75 ? 2 : s.pct >= 60 ? 1 : 0);
    const milestones = Array.isArray(g.streak_milestones) ? g.streak_milestones : [];

    const gamificationBlock = g.total_xp != null ? `<div class="card xp-card">
      <div class="row spread">
        <div>
          <strong style="font-size:1.15rem">XP Didapat: +${g.total_xp} XP</strong>
          <div class="muted" style="font-size:.9rem">Streak terbaik: ${g.max_streak || 0} jawaban benar beruntun</div>
        </div>
        ${renderStars(stars)}
      </div>
      <div class="xp-breakdown">
        <span class="xp-chip">+${g.base_xp || 0} XP (+10/benar)</span>
        ${g.streak_bonus ? `<span class="xp-chip streak">+${g.streak_bonus} XP bonus streak</span>` : ''}
        ${milestones.map((m) => `<span class="xp-chip streak">${m.streak} beruntun +${m.bonus}</span>`).join('')}
      </div>
    </div>
    ${renderLevelCard(g.level)}` : '';

    const subj = Object.entries(s.subject || {}).map(([k, v]) => `<span>${esc(k)}</span><span>${v.c}/${v.t}</span><div class="meter"><span style="width:${Math.round(100 * v.c / Math.max(1, v.t))}%"></span></div>`).join('');
    const wrong = (res.review || []).filter((x) => !x.is_correct);
    const bySubj = {};
    (res.review || []).forEach((x) => {
      const sj = x.subject || 'Lainnya', tp = x.topic || 'Lainnya';
      const t = ((bySubj[sj] = bySubj[sj] || {})[tp] = bySubj[sj][tp] || { w: 0, n: 0 });
      t.n++;
      if (!x.is_correct) t.w++;
    });
    const topicRows = Object.entries(bySubj).map(([sj, tps]) => {
      const rows = Object.entries(tps).filter(([, v]) => v.w > 0).sort((a, b) => b[1].w - a[1].w)
        .map(([tp, v]) => `<li><span>${esc(tp)}</span><span>salah ${v.w} dari ${v.n}</span></li>`).join('');
      return rows ? `<h3>${esc(sj)}</h3><ul class="topics">${rows}</ul>` : '';
    }).join('');

    const findQ = (no) => (Q && (Q[no - 1] && Q[no - 1].no === no ? Q[no - 1] : Q.find((item) => item.no === no) || Q[no - 1])) || null;

    const items = (res.review || []).map((x) => {
      const q = findQ(x.no);
      const chosen = x.chosen_idx == null ? 'tidak dijawab' : `${L[x.chosen_idx]}${q ? '. ' + esc(q.opts[x.chosen_idx]) : ''}`;
      const where = [x.subject, x.topic, x.subtopic].filter(Boolean).map(esc).join(' › ');
      return `<div class="card rv ${x.is_correct ? 'ok' : 'no'}">
        <div class="row spread"><strong>Soal ${x.no}</strong><span class="tag ${x.is_correct ? 'ok' : 'no'}">${x.is_correct ? '✓ Benar' : '✗ Belum tepat'}</span></div>
        ${where ? `<p class="where">${where}</p>` : ''}
        ${q ? `<p>${esc(q.q)}</p>` : ''}
        ${x.is_correct ? '' : `<p>Jawabanmu: ${chosen}<br>Jawaban benar: <strong>${L[x.correct_idx]}${q ? '. ' + esc(q.opts[x.correct_idx]) : ''}</strong></p>
          ${x.explanation ? `<div class="callout-trap"><span class="callout-label">AWAS JEBAKAN · Pembahasan</span><div>${esc(x.explanation)}</div></div>` : ''}
          ${x.shortcut ? `<div class="callout-fast"><span class="callout-label">CARA CEPAT</span><div>${esc(x.shortcut)}</div></div>` : ''}`}
      </div>`;
    }).join('');

    render(`<h1>Tryout terkumpul ✓</h1>
      <div class="card hero-card row spread">
        <div>
          <div class="score">${s.correct}<span class="muted score-total">/${s.total}</span></div>
          <div class="muted">Jawaban benar</div>
        </div>
        ${renderStars(stars)}
      </div>
      ${gamificationBlock}
      <div class="card subj">${subj}</div>
      ${topicRows ? `<div class="card"><h2 style="margin-top:0">Yang perlu dilatih lagi</h2>${topicRows}</div>` : '<p class="note">Semua jawaban benar. Hebat!</p>'}
      <p class="note">Soal yang belum tepat otomatis tersimpan di Buku Salah. Laporan untuk orang tua terbit Senin pagi.</p>
      <h2>Pembahasan (${wrong.length} soal belum tepat)</h2>
      <p class="row"><button id="only" aria-pressed="true">Tampilkan semua soal</button></p>
      <div id="list">${items}</div>
      <div class="row" style="margin-top:16px">
        <a class="btn sun-btn" href="#/buku-salah">Buku Salah</a>
        <a class="btn primary" href="#/beranda">Ke beranda</a>
        <button id="next-to" class="grape-btn">Tryout berikutnya</button>
      </div>`);

    let onlyWrong = true;
    const list = $('#list');
    const apply = () => {
      list.querySelectorAll('.rv.ok').forEach((e) => { e.hidden = onlyWrong; });
      $('#only').textContent = onlyWrong ? 'Tampilkan semua soal' : 'Hanya yang belum tepat';
      $('#only').setAttribute('aria-pressed', String(onlyWrong));
    };
    $('#only').onclick = () => { onlyWrong = !onlyWrong; apply(); };
    apply();

    $('#next-to').onclick = async () => {
      try {
        const hr = await api.get('/api/child/home');
        if (hr.status === 200 && hr.json && Array.isArray(hr.json.tryouts)) {
          const ready = hr.json.tryouts.find((t) => t.state === 'siap' || t.state === 'berjalan');
          if (ready) return go('#/tryout/' + ready.id);
        }
      } catch (e) { /* abaikan */ }
      go('#/beranda');
    };
  }

  // ---------------- report & arsip ----------------
  async function viewReport() {
    syncChrome('shell', 'laporan');
    render('<p class="muted">Memuat laporan latihan…</p>');
    let r, mapRes;
    try {
      [r, mapRes] = await Promise.all([
        api.get('/api/child/home'),
        api.get('/api/child/season-map').catch(() => null),
      ]);
    } catch (e) {
      return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), ($('#rt').onclick = viewReport);
    }
    if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
    if (r.status !== 200) return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div>`);

    const h = r.json;
    const g = h.gamification || {};
    const history = h.history || [];
    const mapData = mapRes && mapRes.status === 200 ? mapRes.json : null;
    updateHeaderStats(g, h.buku_salah_count);

    const archiveRows = history.length
      ? history.map((item) => `<div class="card row spread">
          <div>
            <strong>${esc(tryoutLabel(item.tryout_id))}</strong>
            <div class="muted" style="font-size:.9rem">Jendela ${item.window} · ${esc(fmtDateShort(item.submitted_at))}</div>
            <div class="row" style="gap:8px;margin-top:6px">
              <span class="pill">${item.correct}/${item.total} (${Math.round(item.pct || 0)}%)</span>
              <span class="pill warn">+${item.xp_earned || 0} XP</span>
              ${renderStars(item.stars)}
            </div>
          </div>
          <a class="btn primary" href="#/hasil/${esc(item.attempt)}">Lihat Pembahasan</a>
        </div>`).join('')
      : `<div class="card"><p class="muted" style="margin:0">Belum ada tryout yang dikumpulkan. Mulai tryout pertamamu di halaman Tryout!</p><p style="margin:12px 0 0"><a class="btn primary" href="#/beranda">Ke Tryout</a></p></div>`;

    render(`<h1>Report &amp; Arsip Latihan</h1>
      ${renderLevelCard(g)}
      <div class="stat-grid">
        <div class="stat-box"><div class="stat-val">${history.length}</div><div class="stat-lbl">Tryout Selesai</div></div>
        <div class="stat-box"><div class="stat-val">★ ${g.stars_total || 0}</div><div class="stat-lbl">Total Bintang</div></div>
        <div class="stat-box"><div class="stat-val">${g.best_streak || 0}</div><div class="stat-lbl">Streak Terbaik</div></div>
        <div class="stat-box"><div class="stat-val">${Number(h.buku_salah_count || 0)}</div><div class="stat-lbl">Catatan Buku Salah</div></div>
      </div>
      <h2>Arsip Tryout</h2>
      ${archiveRows}
      ${renderSeasonMap(mapData)}`);
  }

  // ---------------- drill list ----------------
  async function viewDrillList() {
    syncChrome('shell', 'drill');
    render('<p class="muted">Memuat daftar drill…</p>');
    refreshHeaderInBackground();
    let r;
    try {
      r = await api.get('/api/child/drills');
    } catch (e) {
      return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), ($('#rt').onclick = viewDrillList);
    }
    if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
    if (r.status === 409) {
      return render(`<h1>Drill Mingguan</h1>
        <div class="card">
          <p class="note">Drill mingguan dibuka setiap <strong>Senin pukul 06.00 sampai Jumat pukul 15.00 WIB</strong> setelah hasil tryout diolah.</p>
          <p class="muted">Sementara menunggu, kamu bisa mengulas soal di Buku Salah.</p>
          <p class="row"><a class="btn sun-btn" href="#/buku-salah">Buka Buku Salah</a><a class="btn" href="#/beranda">Ke Tryout</a></p>
        </div>`);
    }
    if (r.status !== 200) return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div>`);

    const d = r.json;
    const drills = d.drills || [];
    const taperHtml = d.taper
      ? `<div class="taper-banner" role="note">
          <span aria-hidden="true" style="font-size:1.5rem">🌿</span>
          <div><strong>Mode Minggu Terakhir (Taper)</strong><span>Minggu terakhir: review Buku Salah dan latihan pemeliharaan ringan saja.</span></div>
        </div>`
      : '';

    const cards = drills.length
      ? drills.map((item) => {
          const badge = item.state === 'selesai'
            ? '<span class="pill done">✓ Selesai</span>'
            : item.state === 'siap'
              ? `<button class="primary" data-drill-aid="${item.assignment}" data-drill-ses="${item.session}">Mulai Drill</button>`
              : '<span class="pill lock">Terkunci (selesaikan sesi sebelumnya)</span>';
          return `<div class="card row spread">
            <div>
              <strong>${esc(item.topic)} · Sesi ${item.session}</strong>
              <div class="muted" style="font-size:.9rem">Fokus latihan: ${esc(item.focus || 'ketelitian')} · 5 soal</div>
            </div>
            ${badge}
          </div>`;
        }).join('')
      : '<div class="card"><p class="muted" style="margin:0">Belum ada tugas drill untuk minggu ini. Coba cek kembali setelah tryout dianalisa atau ulas Buku Salah.</p></div>';

    render(`<h1>Drill Mingguan</h1>
      <p class="muted">Latihan singkat 5 soal untuk menguatkan topik yang perlu dilatih. Selesai satu sesi mendapat <strong>+10 XP/benar + 5 XP selesai</strong>.</p>
      ${taperHtml}
      ${cards}`);

    app.querySelectorAll('[data-drill-aid]').forEach((b) => {
      b.addEventListener('click', () => go(`#/drill/${b.dataset.drillAid}/${b.dataset.drillSes}`));
    });
  }

  // ---------------- drill player ----------------
  async function viewDrillPlayer(aid, ses) {
    syncChrome('player');
    render('<p class="muted">Menyiapkan soal drill…</p>');
    let r;
    try {
      r = await api.get(`/api/child/drills/${encodeURIComponent(aid)}/sessions/${encodeURIComponent(ses)}/start`);
    } catch (e) {
      return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), ($('#rt').onclick = () => viewDrillPlayer(aid, ses));
    }
    if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
    if (r.status !== 200) {
      return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div><p><a class="btn" href="#/drill">Kembali ke Drill</a></p>`);
    }

    const data = r.json;
    const Q = data.questions || [];
    const answers = {};
    let cur = 1;
    let submitting = false;

    function show(n) {
      cur = Math.min(Math.max(1, n), Q.length);
      const q = Q[cur - 1];
      const a = answers[cur];
      const answeredCount = Object.keys(answers).length;
      const steps = Q.map((_, idx) => {
        const num = idx + 1;
        return `<button class="drill-step ${answers[num] != null ? 'ans' : ''} ${num === cur ? 'cur' : ''}" data-step="${num}">${num}</button>`;
      }).join('');

      render(`<div class="qhead">
          <span>Drill <strong>${esc(data.topic)}</strong> · Sesi ${data.session}</span>
          <span class="pill">Soal ${cur} dari ${Q.length}</span>
        </div>
        <div class="drill-steps" aria-label="Navigasi soal drill">${steps}</div>
        ${q.passage ? `<div class="passage" aria-label="Bacaan">${esc(q.passage.text)}</div>` : ''}
        <div class="stem" id="stem">${esc(q.q)}</div>
        <div class="opts" role="radiogroup" aria-labelledby="stem">
          ${q.opts.map((o, i) => `<button class="opt" role="radio" aria-checked="${a === i}" data-i="${i}"><span class="k">${L[i]}</span><span>${esc(o)}</span></button>`).join('')}
        </div>
        <div id="drill-st" style="margin-top:12px"></div>
        <div class="bar">
          <button id="d-prev" ${cur === 1 ? 'disabled' : ''}>‹ Sebelumnya</button>
          <span class="muted" style="font-weight:700">${answeredCount}/${Q.length} dijawab</span>
          ${cur === Q.length ? '<button id="d-finish" class="primary">Kumpulkan Drill</button>' : '<button id="d-next" class="primary">Berikutnya ›</button>'}
        </div>`);

      app.querySelectorAll('.drill-step').forEach((b) => b.addEventListener('click', () => show(+b.dataset.step)));
      app.querySelectorAll('.opt').forEach((b) => b.addEventListener('click', () => {
        answers[cur] = +b.dataset.i;
        show(cur);
      }));
      $('#d-prev').onclick = () => show(cur - 1);
      if ($('#d-next')) $('#d-next').onclick = () => show(cur + 1);
      if ($('#d-finish')) $('#d-finish').onclick = submitDrill;
    }

    async function submitDrill() {
      if (submitting) return;
      submitting = true;
      const btn = $('#d-finish');
      if (btn) { btn.disabled = true; btn.textContent = 'Mengirim…'; }
      try {
        const payload = {};
        Object.entries(answers).forEach(([k, v]) => { payload[String(k)] = v; });
        const res = await api.post(`/api/child/drills/${encodeURIComponent(aid)}/sessions/${encodeURIComponent(ses)}/finish`, { answers: payload });
        submitting = false;
        if (res.status !== 200) {
          const st = $('#drill-st');
          if (st) st.innerHTML = `<div class="err">${esc(msg(res.json && res.json.error))}</div>`;
          if (btn) { btn.disabled = false; btn.textContent = 'Kumpulkan Drill'; }
          return;
        }
        renderDrillResult(res.json, data);
      } catch (e) {
        submitting = false;
        const st = $('#drill-st');
        if (st) st.innerHTML = '<div class="err">Gagal terhubung ke server. Coba lagi.</div>';
        if (btn) { btn.disabled = false; btn.textContent = 'Coba lagi'; }
      }
    }

    function renderDrillResult(res, meta) {
      syncChrome('shell', 'drill');
      const g = res.gamification || {};
      if (g.level) updateHeaderStats(g);
      refreshHeaderInBackground();

      const reviewHtml = (res.review || []).map((x) => {
        const chosen = x.chosen_idx == null ? 'tidak dijawab' : `${L[x.chosen_idx]}. ${esc(x.opts[x.chosen_idx])}`;
        return `<div class="card rv ${x.is_correct ? 'ok' : 'no'}">
          <div class="row spread"><strong>Soal ${x.no}</strong><span class="tag ${x.is_correct ? 'ok' : 'no'}">${x.is_correct ? '✓ Benar' : '✗ Belum tepat'}</span></div>
          <p>${esc(x.q)}</p>
          ${x.is_correct ? '' : `<p>Jawabanmu: ${chosen}<br>Jawaban benar: <strong>${L[x.correct_idx]}. ${esc(x.opts[x.correct_idx])}</strong></p>`}
          ${x.explanation ? `<div class="callout-trap"><span class="callout-label">AWAS JEBAKAN · Pembahasan</span><div>${esc(x.explanation)}</div></div>` : ''}
          ${x.shortcut ? `<div class="callout-fast"><span class="callout-label">CARA CEPAT</span><div>${esc(x.shortcut)}</div></div>` : ''}
        </div>`;
      }).join('');

      render(`<h1>Drill Selesai!</h1>
        <div class="card hero-card row spread">
          <div>
            <div class="score">${res.correct}<span class="muted score-total">/${res.total}</span></div>
            <div class="muted">Jawaban benar · ${esc(meta.topic)} (Sesi ${meta.session})</div>
          </div>
        </div>
        <div class="card xp-card">
          <strong>XP Didapat: +${g.total_xp || 0} XP</strong>
          <div class="xp-breakdown">
            <span class="xp-chip">+${g.base_xp || 0} XP (+10/benar)</span>
            <span class="xp-chip">+${g.completion_xp || 5} XP selesai drill</span>
          </div>
        </div>
        ${renderLevelCard(g.level)}
        <p class="note">Soal yang belum tepat otomatis masuk ke Buku Salah untuk dipelajari lagi.</p>
        <h2>Pembahasan Drill</h2>
        ${reviewHtml}
        <div class="row" style="margin-top:16px">
          <a class="btn sun-btn" href="#/buku-salah">Lihat Buku Salah</a>
          <a class="btn primary" href="#/drill">Kembali ke Drill</a>
        </div>`);
    }

    show(cur);
  }

  // ---------------- buku salah ----------------
  async function viewBukuSalah() {
    syncChrome('shell', 'buku-salah');
    render('<p class="muted">Memuat Buku Salah…</p>');
    refreshHeaderInBackground();
    let r;
    try {
      r = await api.get('/api/child/buku-salah');
    } catch (e) {
      return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), ($('#rt').onclick = viewBukuSalah);
    }
    if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
    if (r.status !== 200) return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div>`);

    const items = (r.json && r.json.items) || [];
    updateHeaderStats(null, items.length);

    if (!items.length) {
      return render(`<h1>Buku Salah</h1>
        <div class="card hero-card">
          <h2 style="margin-top:0">Masih bersih!</h2>
          <p class="muted">Belum ada soal yang masuk ke Buku Salah. Setiap jawaban yang belum tepat di tryout atau drill akan muncul di sini lengkap dengan pembahasan dan cara cepat.</p>
          <p><a class="btn primary" href="#/beranda">Ke Tryout</a></p>
        </div>`);
    }

    const subjects = ['Semua', ...Array.from(new Set(items.map((x) => x.subject).filter(Boolean)))];
    let activeSubject = 'Semua';

    function draw() {
      const filtered = activeSubject === 'Semua' ? items : items.filter((x) => x.subject === activeSubject);
      const filtersHtml = subjects.map((sj) => {
        const cnt = sj === 'Semua' ? items.length : items.filter((x) => x.subject === sj).length;
        return `<button class="filter-pill ${sj === activeSubject ? 'active' : ''}" data-subj="${esc(sj)}">${esc(sj)} (${cnt})</button>`;
      }).join('');

      const cardsHtml = filtered.map((item) => {
        const where = [item.subject, item.topic, item.subtopic].filter(Boolean).map(esc).join(' › ');
        const srcLbl = item.source_type === 'drill' ? 'Drill' : 'Tryout';
        const optsHtml = (item.options || []).map((opt, idx) => {
          const isCorrect = idx === item.correct_idx;
          const isChosen = item.chosen_idx != null && idx === item.chosen_idx;
          const cls = isCorrect ? 'bs-opt correct' : isChosen ? 'bs-opt chosen' : 'bs-opt';
          const tag = isCorrect ? ' ✓ Jawaban benar' : isChosen ? ' ✗ Jawabanmu' : '';
          return `<div class="${cls}"><strong>${L[idx]}.</strong> ${esc(opt)}${tag ? ` <span>(${tag.trim()})</span>` : ''}</div>`;
        }).join('');
        return `<article class="card bs-card">
          <div class="row spread">
            <span class="pill">${srcLbl} · Jendela ${item.window}</span>
            <span class="where">${where}</span>
          </div>
          <p style="font-weight:600;margin:10px 0">${esc(item.stem)}</p>
          ${item.chosen_idx == null ? '<p class="muted" style="font-size:.9rem">Jawabanmu: <strong>tidak dijawab</strong></p>' : ''}
          <div class="bs-opts">${optsHtml}</div>
          ${item.explanation ? `<div class="callout-trap"><span class="callout-label">AWAS JEBAKAN · Pembahasan</span><div>${esc(item.explanation)}</div></div>` : ''}
          ${item.shortcut ? `<div class="callout-fast"><span class="callout-label">CARA CEPAT</span><div>${esc(item.shortcut)}</div></div>` : ''}
        </article>`;
      }).join('');

      render(`<h1>Buku Salah</h1>
        <p class="muted">Kumpulan soal yang belum tepat dari tryout dan drill untuk kamu review sebelum latihan berikutnya.</p>
        <div class="filter-bar" role="group" aria-label="Filter mata uji">${filtersHtml}</div>
        ${cardsHtml}`);

      app.querySelectorAll('[data-subj]').forEach((b) => {
        b.addEventListener('click', () => {
          activeSubject = b.dataset.subj;
          draw();
        });
      });
    }

    draw();
  }

  route();
})();
