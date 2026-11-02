/* Area orang tua: daftar (kode anak tampil sekali) → masuk email+PIN → dashboard (paket, tryout anak, laporan).
 * Semua angka (harga, status) datang dari server. */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const app = $('#app'), nav = $('#nav');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const rp = (n) => 'Rp' + Number(n).toLocaleString('id-ID');
  const qs = new URLSearchParams(location.search);
  if (qs.get('sim')) sessionStorage.setItem('sim', qs.get('sim'));
  const sim = sessionStorage.getItem('sim');
  const loaded = Date.now(), simBase = sim ? Date.parse(sim + (/[Z+]/.test(sim.slice(10)) ? '' : '+07:00')) : null;
  const simHeader = simBase ? () => new Date(simBase + (Date.now() - loaded) + 7 * 3600e3).toISOString().slice(0, 19) : null;
  const TK = 'parentToken';
  const api = window.Api('', () => sessionStorage.getItem(TK), simHeader);

  const ERR = {
    email_atau_pin_salah: 'Email atau PIN tidak cocok.',
    terkunci: 'Terlalu banyak percobaan. Coba lagi dalam 15 menit.',
    akses_dinonaktifkan: 'Akun ini sedang dinonaktifkan. Hubungi kami.',
    sudah_terdaftar: 'Email atau nomor WhatsApp ini sudah terdaftar. Silakan masuk dengan PIN Anda.',
    paket_sudah_aktif: 'Paket utama sudah aktif.',
    harga_belum_ditetapkan: 'Paket ini belum dibuka.',
    gateway_gagal: 'Halaman pembayaran belum bisa dibuka. Coba lagi beberapa menit lagi.',
  };
  const FIELD = { name: 'Isi nama orang tua.', whatsapp: 'Nomor WhatsApp diawali 08 atau +62.', email: 'Periksa alamat email.', consent: 'Centang persetujuan untuk melanjutkan.', pin: 'PIN berisi 6 angka.' };
  const PHASE = ['Diagnostik', 'Fondasi', 'Fondasi', 'Fondasi', 'Fondasi', 'Fondasi', 'Akselerasi', 'Akselerasi', 'Akselerasi', 'Intensif', 'Intensif', 'Gladi bersih'];

  function render(html) { app.innerHTML = html; app.focus({ preventScroll: true }); window.scrollTo(0, 0); }
  function setNav() {
    nav.innerHTML = sessionStorage.getItem(TK) ? '<a href="#/beranda">Dashboard</a><a href="#" id="logout">Keluar</a>' : '<a href="#/masuk">Masuk</a><a href="#/daftar">Daftar</a>';
    const lo = $('#logout'); if (lo) lo.onclick = (e) => { e.preventDefault(); sessionStorage.removeItem(TK); location.hash = '#/masuk'; };
  }
  window.addEventListener('hashchange', route);
  function route() {
    setNav();
    const h = location.hash.replace(/^#\/?/, '');
    if (h === 'daftar') return viewRegister();
    if (h === 'masuk' || !sessionStorage.getItem(TK)) return viewLogin();
    return viewHome();
  }

  // ---------- daftar ----------
  function viewRegister() {
    render(`<h1>Daftar dan coba diagnostik gratis</h1>
      <p class="muted">Satu akun untuk satu siswa. Setelah daftar, Anda mendapat kode siswa untuk anak masuk ke ruang tryout.</p>
      <form id="f" class="panel" novalidate>
        <div class="field"><label for="name">Nama orang tua atau wali</label><input id="name" type="text" autocomplete="name" required></div>
        <div class="field"><label for="whatsapp">Nomor WhatsApp</label><input id="whatsapp" type="tel" inputmode="tel" autocomplete="tel" placeholder="08xxxxxxxxxx" required></div>
        <div class="field"><label for="email">Email</label><input id="email" type="email" autocomplete="email" required><span class="hint">Laporan Senin dikirim ke sini. Dipakai juga untuk masuk.</span></div>
        <div class="field"><label for="pin">PIN masuk (6 angka)</label><input id="pin" type="password" inputmode="numeric" autocomplete="new-password" maxlength="6" required><span class="hint">Simpan PIN ini. Anda memakainya bersama email untuk masuk.</span></div>
        <div class="field check"><input id="consent" type="checkbox"><label for="consent" style="font-weight:400">Saya setuju data ini dipakai untuk akun dan laporan anak. Data belajar disimpan terpisah dari data kontak.</label></div>
        <div id="e" class="err" hidden></div>
        <button class="btn solid" type="submit">Daftar</button>
      </form>
      <p>Sudah punya akun? <a href="#/masuk">Masuk</a></p>`);
    $('#f').addEventListener('submit', async (ev) => {
      ev.preventDefault(); const btn = $('button', ev.target), err = $('#e'); btn.disabled = true; err.hidden = true;
      app.querySelectorAll('[aria-invalid]').forEach((x) => x.removeAttribute('aria-invalid'));
      const body = { name: $('#name').value.trim(), whatsapp: $('#whatsapp').value.trim(), email: $('#email').value.trim(), pin: $('#pin').value.trim(), consent: $('#consent').checked };
      try {
        const r = await api.post('/api/parent/register', body);
        if (r.status === 200) { sessionStorage.setItem(TK, r.json.token); return viewCode(r.json.child_code); }
        if (r.status === 422) {
          const bad = JSON.parse(r.json.message || '{}');
          Object.keys(bad).forEach((k) => { const el = $('#' + k); if (el) el.setAttribute('aria-invalid', 'true'); });
          err.innerHTML = Object.keys(bad).map((k) => esc(FIELD[k] || k)).join('<br>');
        } else if (r.json && r.json.error === 'sudah_terdaftar') err.innerHTML = 'Email atau nomor WhatsApp ini sudah terdaftar. <a href="#/masuk">Masuk dengan PIN</a>.';
        else err.textContent = 'Pendaftaran belum berhasil. Coba lagi.';
      } catch (e) { err.textContent = 'Tidak tersambung ke internet. Coba lagi.'; }
      err.hidden = false; btn.disabled = false;
      const first = app.querySelector('[aria-invalid=true]'); if (first) first.focus();
    });
    $('#name').focus();
  }

  function viewCode(code) {
    setNav();
    render(`<h1>Akun dibuat</h1>
      <div class="panel dark"><p>Kode siswa untuk anak Anda</p><p class="code" id="code">${esc(code)}</p>
      <p>Kode ini hanya ditampilkan sekali. Catat atau foto sekarang, lalu berikan kepada anak.</p>
      <p><button class="btn line" id="copy" style="color:#fff;border-color:#fff">Salin kode</button></p></div>
      <div class="panel"><h2>Langkah anak</h2><ol><li>Buka <a href="/child/">${esc(location.host)}/child</a> di laptop.</li><li>Masukkan kode di atas.</li><li>Kerjakan diagnostik gratis kapan saja. Hasilnya keluar setelah dikumpulkan.</li></ol></div>
      <p><a class="btn solid" href="#/beranda">Saya sudah mencatat kode</a></p>`);
    $('#copy').onclick = async () => { try { await navigator.clipboard.writeText(code); $('#copy').textContent = 'Kode tersalin'; } catch (e) { $('#copy').textContent = 'Salin manual dari layar'; } };
  }

  // ---------- masuk ----------
  function viewLogin() {
    render(`<h1>Masuk</h1>
      <form id="f" class="panel">
        <div class="field"><label for="email">Email</label><input id="email" type="email" autocomplete="email" required></div>
        <div class="field"><label for="pin">PIN (6 angka)</label><input id="pin" type="password" inputmode="numeric" autocomplete="current-password" maxlength="6" required></div>
        <div id="e" class="err" hidden></div>
        <button class="btn solid" type="submit">Masuk</button>
      </form>
      <p>Belum punya akun? <a href="#/daftar">Daftar gratis</a></p>`);
    $('#f').addEventListener('submit', async (ev) => {
      ev.preventDefault(); const btn = $('button', ev.target), err = $('#e'); btn.disabled = true; err.hidden = true;
      try {
        const r = await api.post('/api/parent/login', { email: $('#email').value.trim(), pin: $('#pin').value.trim() });
        if (r.status === 200) { sessionStorage.setItem(TK, r.json.token); location.hash = '#/beranda'; return route(); }
        err.textContent = ERR[r.json && r.json.error] || 'Belum berhasil masuk. Coba lagi.';
      } catch (e) { err.textContent = 'Tidak tersambung ke internet. Coba lagi.'; }
      err.hidden = false; btn.disabled = false;
    });
    $('#email').focus();
  }

  // ---------- dashboard ----------
  async function viewHome() {
    render('<p class="muted">Memuat…</p>');
    let h, rep;
    try {
      const [a, b] = await Promise.all([api.get('/api/parent/home'), api.get('/api/parent/report/latest')]);
      if (a.status === 401) { sessionStorage.removeItem(TK); return viewLogin(); }
      h = a.json; rep = b.json;
    } catch (e) { return render('<div class="err">Tidak tersambung. Muat ulang halaman.</div>'); }
    const paid = h.plan === 'utama' || h.plan === 'kejar';
    const atts = h.attempts.map((x) => {
      const name = x.tryout === 'DIAG' ? 'Diagnostik' : `Tryout minggu ke-${x.window}${/-2$/.test(x.tryout) ? ' (kedua)' : ''}`;
      return `<li><span>${esc(name)}<br><small class="muted">${esc(PHASE[x.window - 1] || '')}</small></span><span>${x.submitted_at ? `<strong>${esc(x.pct)}%</strong>` : '<span class="muted">belum dikumpulkan</span>'}</span></li>`;
    }).join('');
    let report = '<p class="muted">Laporan pertama terbit setelah tryout pertama dikumpulkan dan dianalisa.</p>';
    if (rep && rep.report) report = `<p><strong>${esc(rep.report.headline)}</strong></p><p class="muted">Minggu ke-${esc(rep.report.window)}</p>`;
    else if (rep && rep.terbit_pada) report = `<p class="muted">Laporan minggu ini terbit ${esc(new Date(rep.terbit_pada).toLocaleString('id-ID', { weekday: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' }))}.</p>`;
    else if (rep && rep.menunggu_analisa) report = '<p class="muted">Hasil tryout sedang dianalisa. Laporan terbit Senin pukul 07.00.</p>';
    const pending = h.orders.find((o) => o.status === 'menunggu');
    let buy;
    if (paid) buy = '<p class="ok"><strong>Paket utama aktif.</strong> Tryout terbuka setiap Jumat 17.00 sampai Minggu 16.00.</p>';
    else if (h.offer.amount_idr == null) buy = '<p class="muted">Paket untuk pendaftar setelah 9 Desember sedang disiapkan.</p>';
    else if (h.gateway === 'sim' && !h.playtest) buy = `<p>Paket utama <strong>${rp(h.offer.amount_idr)}</strong> untuk ${esc(h.offer.tryouts)} tryout sampai hari tes.</p><p class="muted">Pembayaran online segera dibuka. Diagnostik gratis tetap bisa dikerjakan sekarang.</p>`;
    else {
      const head = `<p>Paket utama <strong>${rp(h.offer.amount_idr)}</strong> untuk ${esc(h.offer.tryouts)} tryout sampai hari tes.</p>`;
      if (pending && pending.payment_url) buy = head + `<p class="muted">Ada pesanan yang menunggu pembayaran.</p><a class="btn solid" href="${esc(pending.payment_url)}">Lanjutkan pembayaran</a>
          <p class="muted" style="margin-top:.8em">Paket aktif otomatis beberapa saat setelah pembayaran berhasil. Muat ulang halaman ini setelah membayar.</p>`;
      else if (pending && h.playtest) buy = head + `<p class="muted">Pesanan ${esc(pending.order)} menunggu pembayaran.</p><button class="btn solid" id="pay" data-o="${esc(pending.order)}">Bayar (simulasi playtest)</button>
          <p class="muted" style="margin-top:.8em">Mode playtest: pembayaran disimulasikan, tidak ada uang berpindah.</p>`;
      else buy = head + '<button class="btn solid" id="order">Beli paket</button><p class="muted" style="margin-top:.8em">Anda akan diarahkan ke halaman pembayaran Duitku untuk memilih metode bayar.</p>';
    }
    render(`<h1>Dashboard</h1>
      <section class="panel"><h2>Paket</h2>${buy}<div id="e" class="err" hidden></div></section>
      <section class="panel"><h2>Laporan terbaru</h2>${report}</section>
      <section class="panel"><h2>Tryout anak</h2>${atts ? `<ul class="list">${atts}</ul>` : '<p class="muted">Belum ada tryout. Minta anak masuk ke <a href="/child/">ruang anak</a> dengan kode siswa, lalu kerjakan diagnostik.</p>'}</section>`);
    const err = $('#e');
    const order = $('#order'); if (order) order.onclick = async () => {
      order.disabled = true; const r = await api.post('/api/parent/orders', {});
      if (r.status === 200 && r.json.payment_url) { location.href = r.json.payment_url; return; }
      if (r.status === 200) return viewHome(); err.textContent = ERR[r.json && r.json.error] || 'Pesanan belum berhasil dibuat.'; err.hidden = false; order.disabled = false;
    };
    const pay = $('#pay'); if (pay) pay.onclick = async () => {
      pay.disabled = true; pay.textContent = 'Memproses…'; const r = await api.post('/api/playtest/orders/' + pay.dataset.o + '/pay', {});
      if (r.status === 200) return viewHome(); err.textContent = 'Pembayaran simulasi gagal.'; err.hidden = false; pay.disabled = false;
    };
  }

  route();
})();
