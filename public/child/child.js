/* Ruang anak: masuk → beranda → tryout → periksa → hasil. Semua keputusan akses ada di server;
 * layar ini hanya menampilkan apa yang dikembalikan API. Tidak ada kunci jawaban di browser sebelum submit. */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const app = $('#app'), clockEl = $('#clock'), toastEl = $('#toast');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
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
  const toast = (m) => { toastEl.textContent = m; toastEl.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => toastEl.classList.remove('on'), 2600); };
  const fmtTime = (iso) => new Date(iso).toLocaleString('id-ID', { weekday: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' });

  const MSG = {
    kode_tidak_dikenali: 'Kode belum dikenali. Periksa lagi atau tanya orang tua.',
    terlalu_sering: 'Terlalu banyak percobaan. Tunggu 10 menit, lalu coba lagi.',
    akses_dinonaktifkan: 'Akses sedang dinonaktifkan. Minta orang tua menghubungi kami.',
    jendela_tertutup: 'Tryout sedang tidak dibuka sekarang.',
    sudah_dikerjakan: 'Tryout ini sudah dikerjakan.',
    kumpulkan_tryout_pertama_dulu: 'Kumpulkan tryout pertama dulu, lalu tryout kedua terbuka.',
    paket_gratis_hanya_diagnostik: 'Paket gratis berisi satu diagnostik.',
    waktu_habis: 'Waktu pengerjaan sudah habis.',
  };
  const msg = (e) => MSG[e] || 'Ada gangguan. Coba lagi sebentar.';

  const CLOCK = {
    pre: 'Tryout pertama dibuka Jumat 6 November pukul 17.00.',
    tryout: 'Jendela tryout sedang dibuka.',
    blackout: 'Hari ini ada simulasi resmi sekolah, jadi tryout di sini ditutup.',
    drill: 'Minggu ini waktunya drill singkat.',
    taper: 'Minggu terakhir: ulang Buku Salah dan latihan ringan saja.',
    gap: 'Jeda sebentar. Tryout dibuka Jumat 17.00.',
    proses: 'Hasil sedang diolah. Drill dibuka Senin pagi.',
    jelang_tes: 'Tes sudah dekat. Istirahat cukup, ya.',
    hari_tes: 'Hari ini hari tes. Semoga lancar!',
    post: 'Musim tryout sudah selesai.',
  };

  // ---------------- router ----------------
  function go(hash) { if (location.hash !== hash) location.hash = hash; else route(); }
  window.addEventListener('hashchange', route);
  function route() {
    stopTimer();
    const h = location.hash.replace(/^#\/?/, '').split('/');
    if (!sessionStorage.getItem(tokenKey)) return viewLogin();
    if (h[0] === 'tryout' && h[1]) return viewTryout(h[1]);
    if (h[0] === 'hasil' && h[1]) return viewResult(h[1]);
    return viewHome();
  }
  function render(html) { app.innerHTML = html; app.focus({ preventScroll: true }); window.scrollTo(0, 0); }

  // ---------------- masuk ----------------
  function viewLogin() {
    clockEl.textContent = '';
    render(`<h1>Masuk</h1>
      <p class="muted">Ketik kode keluarga dari orang tua.</p>
      <form id="f" class="card" autocomplete="off">
        <label for="code">Kode keluarga</label><br>
        <input id="code" type="text" inputmode="text" placeholder="ABCD-1234" maxlength="9" required aria-describedby="e">
        <div id="e" class="err" hidden></div>
        <p><button class="primary" type="submit">Masuk</button></p>
      </form>`);
    const code = $('#code'), err = $('#e');
    code.addEventListener('input', () => { let v = code.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8); if (v.length > 4) v = v.slice(0, 4) + '-' + v.slice(4); code.value = v; });
    $('#f').addEventListener('submit', async (ev) => {
      ev.preventDefault(); const b = ev.submitter || $('button', ev.target); b.disabled = true; err.hidden = true;
      try {
        const r = await api.post('/api/child/login', { code: code.value });
        if (r.status === 200) { sessionStorage.setItem(tokenKey, r.json.token); go('#/beranda'); return; }
        err.textContent = msg(r.json && r.json.error); err.hidden = false;
      } catch (e) { err.textContent = 'Tidak tersambung ke internet. Coba lagi.'; err.hidden = false; }
      b.disabled = false;
    });
    code.focus();
  }

  // ---------------- beranda ----------------
  async function viewHome() {
    render('<p class="muted">Memuat…</p>');
    let r;
    try { r = await api.get('/api/child/home'); } catch (e) { return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), $('#rt').onclick = viewHome; }
    if (r.status === 401) { sessionStorage.removeItem(tokenKey); return viewLogin(); }
    if (r.status !== 200) return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div>`);
    const h = r.json; clockEl.textContent = '';
    const tryouts = h.tryouts.map((t, i) => {
      const name = t.id === 'DIAG' ? 'Diagnostik' : `Tryout ${t.id.split('-')[1] || ''}`.trim();
      const second = i > 0 ? '<p class="muted">Dianjurkan, tidak wajib. Terbuka setelah tryout sebelumnya dikumpulkan.</p>' : '';
      const act = {
        siap: `<button class="primary" data-start="${esc(t.id)}">Mulai</button>`,
        berjalan: `<button class="primary" data-start="${esc(t.id)}">Lanjutkan</button>`,
        selesai: '<span class="pill done">✓ Sudah dikumpulkan</span>',
        terkunci: '<span class="pill lock">Belum terbuka</span>',
        terlewat: '<span class="pill lock">Waktu sudah habis</span>',
      }[t.state] || '';
      return `<div class="card"><div class="row spread"><strong>${esc(name)}</strong>${act}</div>${t.state === 'terkunci' ? second : ''}</div>`;
    }).join('');
    const drills = (h.drills || []).map((d) => `<div class="card row spread"><span>${esc(d.topic)} · sesi ${d.session}</span>
        <span class="pill ${d.state === 'selesai' ? 'done' : d.state === 'terkunci' ? 'lock' : ''}">${d.state === 'selesai' ? '✓ Selesai' : d.state === 'siap' ? 'Siap' : 'Setelah sesi sebelumnya'}</span></div>`).join('');
    render(`<h1>Halo!</h1>
      <p class="note">${esc(CLOCK[h.clock] || '')}${h.closes_at ? ` Ditutup ${esc(fmtTime(h.closes_at))}.` : ''}</p>
      ${h.tryouts.length ? '<h2>Tryout</h2>' + tryouts : ''}
      ${h.clock === 'tryout' && !h.tryouts.length ? '<p class="muted">Tidak ada tryout untukmu di jendela ini.</p>' : ''}
      ${h.drills && h.drills.length ? '<h2>Drill minggu ini</h2><p class="muted">Dianjurkan, 10–15 menit per sesi.</p>' + drills : ''}
      ${h.pending ? '<p class="muted">Drill sedang disiapkan dari hasil tryout.</p>' : ''}
      <p style="margin-top:2em"><button id="out">Keluar</button></p>`);
    app.querySelectorAll('[data-start]').forEach((b) => b.addEventListener('click', () => go('#/tryout/' + b.dataset.start)));
    $('#out').onclick = () => { sessionStorage.removeItem(tokenKey); go('#/masuk'); };
  }

  // ---------------- tryout ----------------
  let timer = null; const stopTimer = () => { if (timer) clearInterval(timer); timer = null; clockEl.classList.remove('low'); };

  async function viewTryout(tid) {
    render('<p class="muted">Menyiapkan soal…</p>');
    let r;
    try { r = await api.post('/api/child/tryouts/' + encodeURIComponent(tid) + '/start'); } catch (e) { return render(`<div class="err">Tidak tersambung. <button id="rt">Coba lagi</button></div>`), $('#rt').onclick = () => viewTryout(tid); }
    if (r.status !== 200) return render(`<div class="err">${esc(msg(r.json && r.json.error))}</div><p><a class="btn" href="#/beranda">Kembali</a></p>`);
    const data = r.json, Q = data.questions;
    sessionStorage.setItem('q:' + data.attempt, JSON.stringify(Q));
    const run = new window.Runner({ api, attempt: data.attempt, questions: Q, deadlineAt: data.deadline_at, storage: window.localStorage, now });
    run.attachVisibility(document);
    if (data.resumed) toast('Melanjutkan dari jawaban terakhir.');
    let cur = run.state.cur || 1, sending = false;
    const flushSoon = () => run.flush().catch(() => {});
    const fl = setInterval(flushSoon, 20000);
    document.addEventListener('visibilitychange', () => { if (document.hidden) flushSoon(); });

    function tick() {
      const s = run.remainingSec(), m = Math.floor(s / 60);
      clockEl.textContent = `${String(Math.floor(m / 60))}:${String(m % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
      clockEl.setAttribute('aria-label', `Sisa waktu ${m} menit`);
      clockEl.classList.toggle('low', s <= 300);
      if (s <= 0 && !sending) { stopTimer(); clearInterval(fl); doSubmit(true); }
    }
    stopTimer(); timer = setInterval(tick, 1000); tick();

    function show(n) {
      cur = Math.min(Math.max(1, n), Q.length); run.visit(cur);
      const q = Q[cur - 1], a = run.state.answers[cur], f = !!run.state.flags[cur];
      render(`<div class="qhead"><span>Soal <strong>${cur}</strong> dari ${Q.length}</span><span>${esc(q.subject)}</span></div>
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
    function pick(i) { run.answer(cur, i); app.querySelectorAll('.opt').forEach((b) => b.setAttribute('aria-checked', String(+b.dataset.i === i))); $('#grid').textContent = `☰ ${run.progress().answered}/${Q.length}`; }

    function gridHtml() {
      return `<div class="legend"><span><i class="a"></i>Sudah dijawab</span><span><i></i>Belum dijawab</span><span><i class="f"></i>Ragu-ragu</span></div>
        <div class="grid">${Q.map((_, i) => { const n = i + 1, ans = run.state.answers[n] != null, f = run.state.flags[n];
          return `<button class="cell ${ans ? 'ans' : ''} ${n === cur ? 'cur' : ''}" data-n="${n}" aria-label="Soal ${n}${ans ? ', sudah dijawab' : ', belum dijawab'}${f ? ', ragu-ragu' : ''}">${n}${f ? '<span class="fm" aria-hidden="true"></span>' : ''}</button>`; }).join('')}</div>`;
    }
    function openGrid() {
      const ov = document.createElement('div'); ov.className = 'overlay';
      ov.innerHTML = `<div class="sheet" role="dialog" aria-modal="true" aria-label="Daftar soal">${gridHtml()}<p class="row spread"><button id="close">Tutup</button><button id="g-check" class="primary">Periksa &amp; kumpulkan</button></p></div>`;
      document.body.appendChild(ov);
      const close = () => ov.remove();
      ov.addEventListener('click', (e) => { if (e.target === ov) close(); });
      ov.querySelectorAll('.cell').forEach((b) => b.addEventListener('click', () => { close(); show(+b.dataset.n); }));
      $('#close', ov).onclick = close; $('#g-check', ov).onclick = () => { close(); viewCheck(); };
      $('.cell', ov).focus();
    }

    function viewCheck() {
      const p = run.progress(); const blank = Q.map((_, i) => i + 1).filter((n) => run.state.answers[n] == null);
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
      $('#back').onclick = () => show(cur); $('#send').onclick = () => doSubmit(false);
    }

    async function doSubmit(auto) {
      if (sending) return; sending = true;
      if (auto) render('<h1>Waktu habis</h1><p>Jawabanmu sedang dikumpulkan otomatis…</p><div id="st" role="status" aria-live="polite"></div><p><button id="send" class="primary" disabled>Mengirim…</button></p>');
      const btn = $('#send'), st = $('#st');
      if (btn) { btn.disabled = true; btn.textContent = 'Mengirim…'; }
      const res = await run.submit();
      sending = false;
      if (res.ok) {
        stopTimer(); clearInterval(fl);
        sessionStorage.setItem('r:' + data.attempt, JSON.stringify(res.result)); run.clear();
        if (btn) btn.textContent = 'Terkirim ✓';
        return go('#/hasil/' + data.attempt);
      }
      if (res.closed) { stopTimer(); clearInterval(fl); return render(`<h1>Tidak bisa dikumpulkan</h1><div class="err">${esc(msg(res.error))}</div><p><a class="btn" href="#/beranda">Ke beranda</a></p>`); }
      if (st) st.innerHTML = '<div class="err">Gagal terkirim. Jawabanmu aman tersimpan di perangkat ini. Periksa internet, lalu tekan Coba lagi.</div>';
      if (btn) { btn.disabled = false; btn.textContent = 'Coba lagi'; btn.onclick = () => doSubmit(auto); }
    }

    document.onkeydown = (e) => {
      if (!location.hash.startsWith('#/tryout') || e.ctrlKey || e.metaKey || e.altKey || document.querySelector('.overlay') || !$('.opts')) return;
      const k = e.key.toUpperCase(); const i = 'ABCD'.indexOf(k) >= 0 ? 'ABCD'.indexOf(k) : '1234'.indexOf(k);
      if (i >= 0 && k.length === 1) { pick(i); e.preventDefault(); }
      else if (k === 'N' || e.key === 'ArrowRight') { if (cur < Q.length) show(cur + 1); }
      else if (k === 'P' || e.key === 'ArrowLeft') { if (cur > 1) show(cur - 1); }
    };
    show(cur);
  }

  // ---------------- hasil ----------------
  function viewResult(att) {
    clockEl.textContent = '';
    const res = JSON.parse(sessionStorage.getItem('r:' + att) || 'null'), Q = JSON.parse(sessionStorage.getItem('q:' + att) || 'null');
    if (!res) return render('<h1>Hasil tersimpan</h1><p class="muted">Jawabanmu sudah dikumpulkan. Ringkasan lengkap ada di laporan orang tua.</p><p><a class="btn" href="#/beranda">Ke beranda</a></p>');
    const s = res.score;
    const subj = Object.entries(s.subject).map(([k, v]) => `<span>${esc(k)}</span><span>${v.c}/${v.t}</span><div class="meter"><span style="width:${Math.round(100 * v.c / v.t)}%"></span></div>`).join('');
    const wrong = res.review.filter((x) => !x.is_correct);
    const items = res.review.map((x) => {
      const q = Q && Q[x.no - 1];
      const chosen = x.chosen_idx == null ? 'tidak dijawab' : `${L[x.chosen_idx]}${q ? '. ' + esc(q.opts[x.chosen_idx]) : ''}`;
      return `<div class="card rv ${x.is_correct ? 'ok' : 'no'}"><div class="row spread"><strong>Soal ${x.no}</strong><span class="tag ${x.is_correct ? 'ok' : 'no'}">${x.is_correct ? '✓ Benar' : '✗ Belum tepat'}</span></div>
        ${q ? `<p>${esc(q.q)}</p>` : ''}
        ${x.is_correct ? '' : `<p>Jawabanmu: ${chosen}<br>Jawaban benar: <strong>${L[x.correct_idx]}${q ? '. ' + esc(q.opts[x.correct_idx]) : ''}</strong></p>
        ${x.explanation ? `<p><strong>Pembahasan.</strong> ${esc(x.explanation)}</p>` : ''}${x.shortcut ? `<p><strong>Cara cepat.</strong> ${esc(x.shortcut)}</p>` : ''}`}</div>`;
    }).join('');
    render(`<h1>Tryout terkumpul ✓</h1>
      <div class="card row spread"><div><div class="score">${s.correct}<span class="muted" style="font-size:1.4rem">/${s.total}</span></div><div class="muted">jawaban benar</div></div></div>
      <div class="card subj">${subj}</div>
      <p class="note">Soal yang belum tepat masuk ke Buku Salah. Laporan untuk orang tua terbit Senin pagi.</p>
      <h2>Pembahasan (${wrong.length} soal belum tepat)</h2>
      <p class="row"><button id="only" aria-pressed="true">Tampilkan semua soal</button></p>
      <div id="list">${items}</div>
      <p><a class="btn primary" href="#/beranda">Ke beranda</a></p>`);
    let onlyWrong = true; const list = $('#list');
    const apply = () => { list.querySelectorAll('.rv.ok').forEach((e) => { e.hidden = onlyWrong; }); $('#only').textContent = onlyWrong ? 'Tampilkan semua soal' : 'Hanya yang belum tepat'; };
    $('#only').onclick = () => { onlyWrong = !onlyWrong; apply(); }; apply();
  }

  route();
})();
