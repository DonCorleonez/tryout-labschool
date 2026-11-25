/* Portal orang tua: daftar (kode siswa tampil sekali) -> masuk email+PIN -> dashboard
 * (paket, laporan lengkap 60-detik, buku salah cetak, jalur prestasi).
 * Semua angka (harga, status, laporan) datang dari server. */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const app = $('#app'), nav = $('#nav');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
  const rp = (n) => 'Rp' + Number(n).toLocaleString('id-ID');
  const qs = new URLSearchParams(location.search);
  if (qs.get('sim')) sessionStorage.setItem('sim', qs.get('sim'));
  const sim = sessionStorage.getItem('sim');
  const loaded = Date.now();
  const simBase = sim ? Date.parse(sim + (/[Z+]/.test(sim.slice(10)) ? '' : '+07:00')) : null;
  const simHeader = simBase ? () => new Date(simBase + (Date.now() - loaded) + 7 * 3600e3).toISOString().slice(0, 19) : null;
  const TK = 'parentToken';
  const api = window.Api('', () => sessionStorage.getItem(TK), simHeader);

  const ERR = {
    email_atau_pin_salah: 'Email atau PIN tidak cocok.',
    terkunci: 'Terlalu banyak percobaan. Coba lagi dalam 15 menit atau gunakan Lupa PIN.',
    akses_dinonaktifkan: 'Akun ini sedang dinonaktifkan. Hubungi kami.',
    sudah_terdaftar: 'Email atau nomor WhatsApp ini sudah terdaftar. Silakan masuk dengan PIN Anda.',
    paket_sudah_aktif: 'Paket utama sudah aktif.',
    harga_belum_ditetapkan: 'Paket ini belum dibuka.',
    gateway_gagal: 'Halaman pembayaran belum bisa dibuka. Coba lagi beberapa menit lagi.',
    token_tidak_valid: 'Token reset tidak berlaku atau sudah kedaluwarsa.',
    bukti_sudah_dipakai: 'Referensi bukti ini sudah pernah digunakan.',
  };

  const FIELD = {
    name: 'Isi nama orang tua atau wali.',
    whatsapp: 'Nomor WhatsApp diawali 08 atau +62.',
    email: 'Periksa alamat email.',
    consent: 'Centang persetujuan untuk melanjutkan.',
    pin: 'PIN berisi 6 angka.',
    proof_ref: 'Isi nomor atau referensi bukti prestasi minimal 4 karakter.',
  };

  const PHASE = [
    'Diagnostik', 'Fondasi', 'Fondasi', 'Fondasi', 'Fondasi', 'Fondasi',
    'Akselerasi', 'Akselerasi', 'Akselerasi', 'Intensif', 'Intensif', 'Gladi bersih'
  ];

  const LETTERS = ['A', 'B', 'C', 'D'];

  const MATRIX_CELLS = [
    {
      key: 'efisien',
      title: 'Nilai Baik + Tempo Pas',
      desc: 'Efisien. Pertahankan ketelitian, tidak perlu menambah volume latihan berlebih.'
    },
    {
      key: 'paham_belum_lancar',
      title: 'Nilai Baik + Tempo Lambat',
      desc: 'Paham tetapi belum lancar. Latih melewati soal sulit lebih dulu, lalu kembali bila waktu tersisa.'
    },
    {
      key: 'terburu_buru',
      title: 'Nilai Perlu Naik + Cepat',
      desc: 'Terburu-buru. Minta siswa pelan: baca soal sampai habis, tandai ragu daripada menebak. Targetnya lebih teliti, bukan lebih cepat.'
    },
    {
      key: 'konsep_belum_paham',
      title: 'Nilai Perlu Naik + Lambat',
      desc: 'Konsep dasar perlu diulang terlebih dahulu. Jangan didesak lebih cepat; kecepatan menyusul setelah paham.'
    }
  ];

  function render(html) {
    app.innerHTML = html;
    app.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  function setNav() {
    nav.innerHTML = sessionStorage.getItem(TK)
      ? '<a href="#/beranda">Dashboard</a><a href="#" id="logout">Keluar</a>'
      : '<a href="#/masuk">Masuk</a><a href="#/daftar">Daftar</a>';
    const lo = $('#logout');
    if (lo) {
      lo.onclick = (e) => {
        e.preventDefault();
        sessionStorage.removeItem(TK);
        location.hash = '#/masuk';
      };
    }
  }

  window.addEventListener('hashchange', route);
  function route() {
    setNav();
    const h = location.hash.replace(/^#\/?/, '');
    if (h === 'daftar') return viewRegister();
    if (h === 'lupa-pin') return viewPinReset();
    if (h === 'masuk' || !sessionStorage.getItem(TK)) return viewLogin();
    return viewHome();
  }

  // ---------- daftar ----------
  function viewRegister() {
    render(`<h1>Daftar dan coba diagnostik gratis</h1>
      <p class="muted">Satu akun untuk satu siswa. Setelah daftar, Anda mendapat kode siswa untuk anak masuk ke ruang tryout.</p>
      <form id="f" class="panel" novalidate>
        <div class="field">
          <label for="name">Nama orang tua atau wali</label>
          <input id="name" type="text" autocomplete="name" required>
        </div>
        <div class="field">
          <label for="whatsapp">Nomor WhatsApp</label>
          <input id="whatsapp" type="tel" inputmode="tel" autocomplete="tel" placeholder="08xxxxxxxxxx" required>
        </div>
        <div class="field">
          <label for="email">Email</label>
          <input id="email" type="email" autocomplete="email" required>
          <span class="hint">Laporan Senin dikirim ke sini. Dipakai juga untuk masuk.</span>
        </div>
        <div class="field">
          <label for="campus">Kampus tujuan (dianjurkan)</label>
          <select id="campus">
            <option value="">Pilih kampus tujuan...</option>
            <option value="Cibubur">Cibubur</option>
            <option value="Kebayoran">Kebayoran</option>
            <option value="Jakarta">Jakarta</option>
            <option value="Lainnya">Lainnya</option>
          </select>
        </div>
        <div class="field">
          <label for="track">Jalur pendaftaran rencana (dianjurkan)</label>
          <select id="track">
            <option value="">Pilih jalur...</option>
            <option value="Jalur Tes">Jalur Tes</option>
            <option value="Jalur Prestasi">Jalur Prestasi</option>
            <option value="Belum tahu">Belum tahu</option>
          </select>
        </div>
        <div class="field">
          <label for="grade">Kelas siswa saat ini</label>
          <select id="grade">
            <option value="">Pilih kelas...</option>
            <option value="6">Kelas 6 SD</option>
            <option value="5">Kelas 5 SD</option>
          </select>
        </div>
        <div class="field">
          <label for="pin">PIN masuk (6 angka)</label>
          <input id="pin" type="password" inputmode="numeric" autocomplete="new-password" maxlength="6" required>
          <span class="hint">Simpan PIN ini. Anda memakainya bersama email untuk masuk.</span>
        </div>
        <div class="field check">
          <input id="consent" type="checkbox">
          <label for="consent" style="font-weight:400">Saya setuju data ini dipakai untuk akun dan laporan siswa. Data belajar disimpan terpisah dari data kontak.</label>
        </div>
        <div id="e" class="err" hidden></div>
        <button class="btn solid" type="submit">Daftar</button>
      </form>
      <p>Sudah punya akun? <a href="#/masuk">Masuk</a></p>`);

    $('#f').addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const btn = $('button[type=submit]', ev.target), err = $('#e');
      btn.disabled = true;
      err.hidden = true;
      app.querySelectorAll('[aria-invalid]').forEach((x) => x.removeAttribute('aria-invalid'));
      const body = {
        name: $('#name').value.trim(),
        whatsapp: $('#whatsapp').value.trim(),
        email: $('#email').value.trim(),
        campus: $('#campus').value,
        track: $('#track').value,
        grade: $('#grade').value,
        pin: $('#pin').value.trim(),
        consent: $('#consent').checked
      };
      try {
        const r = await api.post('/api/parent/register', body);
        if (r.status === 200) {
          sessionStorage.setItem(TK, r.json.token);
          return viewCode(r.json.child_code, r.json.access_code);
        }
        if (r.status === 422) {
          const bad = JSON.parse(r.json.message || '{}');
          Object.keys(bad).forEach((k) => {
            const el = $('#' + k);
            if (el) el.setAttribute('aria-invalid', 'true');
          });
          err.innerHTML = Object.keys(bad).map((k) => esc(FIELD[k] || k)).join('<br>');
        } else if (r.json && r.json.error === 'sudah_terdaftar') {
          err.innerHTML = 'Email atau nomor WhatsApp ini sudah terdaftar. <a href="#/masuk">Masuk dengan PIN</a>.';
        } else {
          err.textContent = 'Pendaftaran belum berhasil. Coba lagi.';
        }
      } catch (e) {
        err.textContent = 'Tidak tersambung ke internet. Coba lagi.';
      }
      err.hidden = false;
      btn.disabled = false;
      const first = app.querySelector('[aria-invalid=true]');
      if (first) first.focus();
    });
    $('#name').focus();
  }

  function viewCode(code, accessCode) {
    setNav();
    const fullCode = accessCode || ('LAB-' + code);
    render(`<h1>Akun dibuat</h1>
      <div class="panel dark">
        <p>Kode siswa untuk anak Anda</p>
        <p class="code" id="code">${esc(code)}</p>
        <div class="code-badge-sub">Kode lengkap: ${esc(fullCode)}</div>
        <p>Kode ini hanya ditampilkan sekali. Catat atau foto sekarang, lalu berikan kepada anak.</p>
        <p><button class="btn line" id="copy">Salin kode</button></p>
      </div>
      <div class="panel">
        <h2>Langkah anak</h2>
        <ol>
          <li>Buka <a href="/child/">${esc(location.host)}/child</a> di laptop atau tablet.</li>
          <li>Masukkan kode di atas.</li>
          <li>Kerjakan diagnostik gratis kapan saja. Hasilnya keluar setelah dikumpulkan.</li>
        </ol>
      </div>
      <p><a class="btn solid" href="#/beranda">Saya sudah mencatat kode</a></p>`);

    $('#copy').onclick = async () => {
      try {
        await navigator.clipboard.writeText(code);
        $('#copy').textContent = 'Kode tersalin';
      } catch (e) {
        $('#copy').textContent = 'Salin manual dari layar';
      }
    };
  }

  // ---------- masuk ----------
  function viewLogin() {
    render(`<h1>Masuk</h1>
      <form id="f" class="panel">
        <div class="field"><label for="email">Email</label><input id="email" type="email" autocomplete="email" required></div>
        <div class="field"><label for="pin">PIN (6 angka)</label><input id="pin" type="password" inputmode="numeric" autocomplete="current-password" maxlength="6" required></div>
        <div id="e" class="err" hidden></div>
        <div class="actions" style="margin-top:12px">
          <button class="btn solid" type="submit">Masuk</button>
          <a class="btn line" href="#/lupa-pin">Lupa PIN?</a>
        </div>
      </form>
      <p>Belum punya akun? <a href="#/daftar">Daftar gratis</a></p>`);

    $('#f').addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const btn = $('button[type=submit]', ev.target), err = $('#e');
      btn.disabled = true;
      err.hidden = true;
      try {
        const r = await api.post('/api/parent/login', {
          email: $('#email').value.trim(),
          pin: $('#pin').value.trim()
        });
        if (r.status === 200) {
          sessionStorage.setItem(TK, r.json.token);
          location.hash = '#/beranda';
          return route();
        }
        err.textContent = ERR[r.json && r.json.error] || 'Belum berhasil masuk. Coba lagi.';
      } catch (e) {
        err.textContent = 'Tidak tersambung ke internet. Coba lagi.';
      }
      err.hidden = false;
      btn.disabled = false;
    });
    $('#email').focus();
  }

  // ---------- lupa PIN ----------
  function viewPinReset() {
    render(`<h1>Lupa PIN</h1>
      <p class="muted">Masukkan email terdaftar untuk meminta token atur ulang PIN, lalu masukkan token dan PIN baru 6 angka.</p>
      <form id="f-req" class="panel">
        <h2>1. Minta token reset</h2>
        <div class="field"><label for="reset-email">Email terdaftar</label><input id="reset-email" type="email" autocomplete="email" required></div>
        <div id="req-msg" class="ok-box" hidden></div>
        <div id="req-err" class="err" hidden></div>
        <button class="btn sky" type="submit">Kirim instruksi reset PIN</button>
      </form>
      <form id="f-reset" class="panel">
        <h2>2. Pasang PIN baru</h2>
        <div class="field"><label for="reset-token">Token reset dari email</label><input id="reset-token" type="text" required></div>
        <div class="field"><label for="new-pin">PIN baru (6 angka)</label><input id="new-pin" type="password" inputmode="numeric" maxlength="6" required></div>
        <div id="reset-ok" class="ok-box" hidden></div>
        <div id="e" class="err" hidden></div>
        <button class="btn solid" type="submit">Simpan PIN baru</button>
      </form>
      <p><a href="#/masuk">Kembali ke halaman masuk</a></p>`);

    $('#f-req').addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const btn = $('button[type=submit]', ev.target), msg = $('#req-msg'), err = $('#req-err');
      btn.disabled = true; msg.hidden = true; err.hidden = true;
      try {
        const r = await api.post('/api/parent/pin/reset-request', { email: $('#reset-email').value.trim() });
        if (r.status === 200) {
          msg.textContent = (r.json && r.json.message) || 'Jika email terdaftar, tautan reset PIN telah dikirim.';
          msg.hidden = false;
        } else {
          err.textContent = 'Permintaan belum berhasil. Coba lagi.';
          err.hidden = false;
        }
      } catch (e) {
        err.textContent = 'Tidak tersambung ke internet. Coba lagi.';
        err.hidden = false;
      }
      btn.disabled = false;
    });

    $('#f-reset').addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const btn = $('button[type=submit]', ev.target), ok = $('#reset-ok'), err = $('#e');
      btn.disabled = true; ok.hidden = true; err.hidden = true;
      try {
        const r = await api.post('/api/parent/pin/reset', {
          token: $('#reset-token').value.trim(),
          pin: $('#new-pin').value.trim()
        });
        if (r.status === 200) {
          ok.innerHTML = 'PIN berhasil diperbarui. <a href="#/masuk">Masuk dengan PIN baru</a>.';
          ok.hidden = false;
        } else if (r.status === 422) {
          err.textContent = FIELD.pin;
          err.hidden = false;
        } else {
          err.textContent = ERR[r.json && r.json.error] || 'Token reset tidak valid atau kedaluwarsa.';
          err.hidden = false;
        }
      } catch (e) {
        err.textContent = 'Tidak tersambung ke internet. Coba lagi.';
        err.hidden = false;
      }
      btn.disabled = false;
    });
  }

  // ---------- helper grafik & laporan ----------
  function barClass(pct) {
    if (pct >= 70) return 'good';
    if (pct >= 50) return 'mid';
    return 'low';
  }

  function statusClass(status) {
    if (status === 'Siap Diuji') return 'siap';
    if (status === 'Mengejar') return 'mengejar';
    return 'belum';
  }

  function aggregateSubjects(trends) {
    const map = {};
    (trends || []).forEach((tr) => {
      const subs = tr.subjects || {};
      Object.keys(subs).forEach((s) => {
        if (!map[s]) map[s] = { c: 0, t: 0 };
        map[s].c += subs[s].c || 0;
        map[s].t += subs[s].t || 0;
      });
    });
    return Object.keys(map).map((s) => ({
      subject: s,
      c: map[s].c,
      t: map[s].t,
      pct: map[s].t ? Math.round((1000 * map[s].c) / map[s].t) / 10 : 0
    }));
  }

  function formatChosen(item) {
    if (item.chosen_idx == null || item.chosen_idx < 0 || item.chosen_idx >= (item.options || []).length) {
      return 'Tidak dijawab (kosong)';
    }
    return `${LETTERS[item.chosen_idx] || ''}. ${item.options[item.chosen_idx]}`;
  }

  function formatCorrect(item) {
    if (item.correct_idx == null || item.correct_idx < 0 || item.correct_idx >= (item.options || []).length) {
      return '-';
    }
    return `${LETTERS[item.correct_idx] || ''}. ${item.options[item.correct_idx]}`;
  }

  function renderOverviewTab(h, rep, full) {
    const paid = h.plan === 'utama' || h.plan === 'kejar';
    const atts = (h.attempts || []).map((x) => {
      const name = x.tryout === 'DIAG'
        ? 'Diagnostik'
        : `Tryout minggu ke-${x.window}${/-2$/.test(x.tryout) ? ' (kedua)' : ''}`;
      return `<li><span>${esc(name)}<br><small class="muted">${esc(PHASE[x.window - 1] || '')}</small></span><span>${x.submitted_at ? `<strong>${esc(x.pct)}%</strong>` : '<span class="muted">belum dikumpulkan</span>'}</span></li>`;
    }).join('');

    let report = '<p class="muted">Laporan pertama terbit setelah tryout pertama dikumpulkan dan dianalisa.</p>';
    if (rep && rep.report) {
      report = `<p><strong>${esc(rep.report.headline)}</strong></p><p class="muted">Minggu ke-${esc(rep.report.window)}</p>`;
    } else if (rep && rep.terbit_pada) {
      report = `<p class="muted">Laporan minggu ini terbit ${esc(new Date(rep.terbit_pada).toLocaleString('id-ID', {
        weekday: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta'
      }))}.</p>`;
    } else if (rep && rep.menunggu_analisa) {
      report = '<p class="muted">Hasil tryout sedang dianalisa. Laporan terbit Senin pukul 07.00.</p>';
    }

    const pending = (h.orders || []).find((o) => o.status === 'menunggu');
    const activeName = h.plan === 'kejar' ? 'Paket kejar' : 'Paket utama';
    const offerName = (h.offer && h.offer.plan === 'kejar') ? 'Paket kejar' : 'Paket utama';
    const cutoffNote = (h.offer && h.offer.plan === 'kejar')
      ? 'Pemesanan mulai 9 Des 2026 (00.00 WIB) menggunakan tarif Paket Kejar.'
      : 'Tarif Paket Utama berlaku untuk pemesanan s.d. 8 Des 2026 (pemesanan mulai 9 Des 2026 memakai Paket Kejar Rp129.000).';
    let buy;
    if (paid) {
      buy = `<p class="ok-box"><strong>${esc(activeName)} aktif.</strong> Tryout terbuka setiap Jumat 17.00 sampai Minggu 16.00. Laporan mingguan terbit Senin pukul 07.00.</p>`;
    } else if (h.offer.amount_idr == null) {
      buy = '<p class="muted">Paket untuk pemesanan mulai 9 Desember sedang disiapkan.</p>';
    } else if (h.gateway === 'sim' && !h.playtest) {
      buy = `<p>${esc(offerName)} <strong>${rp(h.offer.amount_idr)}</strong> untuk ${esc(h.offer.tryouts)} tryout pada jendela tersisa sampai hari tes.</p>
        <p class="muted">${esc(cutoffNote)}</p>
        <p class="muted">Pembayaran online segera dibuka. Diagnostik gratis tetap bisa dikerjakan sekarang.</p>`;
    } else {
      const simTag = h.playtest ? ' <span class="pill sim">Simulasi</span>' : '';
      const head = `<p>${esc(offerName)} <strong>${rp(h.offer.amount_idr)}</strong>${simTag} untuk ${esc(h.offer.tryouts)} tryout pada jendela tersisa sampai hari tes.</p>
        <p class="muted">${esc(cutoffNote)}</p>`;
      if (pending && pending.payment_url) {
        buy = head + `<p class="muted">Ada pesanan yang menunggu pembayaran.</p>
          <a class="btn solid" href="${esc(pending.payment_url)}">Lanjutkan pembayaran</a>
          <p class="muted" style="margin-top:.8em">Paket aktif otomatis beberapa saat setelah pembayaran berhasil. Muat ulang halaman ini setelah membayar.</p>`;
      } else if (pending && h.playtest) {
        buy = head + `<p class="muted">Pesanan ${esc(pending.order)} menunggu pembayaran.</p>
          <button class="btn solid" id="pay" data-o="${esc(pending.order)}">Bayar (simulasi playtest)</button>
          <p class="muted" style="margin-top:.8em">Mode playtest: pembayaran disimulasikan, tidak ada uang berpindah.</p>`;
      } else {
        buy = head + `<button class="btn solid" id="order">Beli paket</button>
          <p class="muted" style="margin-top:.8em">Anda akan diarahkan ke halaman pembayaran Duitku untuk memilih metode bayar.</p>`;
      }
    }

    // Laporan Lengkap 60-Detik dari /api/parent/reports
    const sum = (full && full.summary) || {
      status: 'Belum Siap',
      disclaimer: 'Alat ukur latihan mandiri, bukan prediksi penerimaan dan tidak berafiliasi dengan instansi sekolah mana pun.',
      tryouts_completed: 0,
      tryouts_total: h.offer ? h.offer.tryouts : 14,
      drills_completed: 0,
      drills_assigned: 0,
      missed_windows: [],
      latest_headline: 'Belum ada data tryout'
    };
    const trends = (full && full.trends) || [];
    const topicTrends = (full && full.topic_trends) || [];
    const drillHist = (full && full.drill_history) || [];
    const wrongItems = (full && full.wrong_items) || [];
    const recs = (full && full.recommendations) || [];
    const subjTrends = aggregateSubjects(trends);
    const missed = sum.missed_windows || [];
    const missedNote = missed.length
      ? `Minggu ke-${missed.map((m) => m.window).join(', ')} terlewat — tidak masalah, fokus pada latihan berikutnya.`
      : 'Semua jendela tersedia diikuti dengan baik.';

    const latestTrend = trends.length ? trends[trends.length - 1] : null;
    const activeCell = latestTrend && latestTrend.matrix ? latestTrend.matrix.cell : null;
    let staminaNote = 'Belum ada data pengerjaan.';
    if (latestTrend) {
      if (latestTrend.blank_tail) {
        staminaNote = 'Catatan waktu habis (blank tail): ada beberapa soal kosong di sepertiga akhir. Biasanya karena waktu habis, bukan kelelahan—latih melewati soal sulit lebih awal.';
      } else if (latestTrend.stamina_drop) {
        staminaNote = 'Catatan stamina: akurasi sepertiga akhir turun dibanding sepertiga awal. Jaga jeda napas singkat tiap 5 soal agar fokus terjaga.';
      } else {
        staminaNote = 'Stamina terjaga: akurasi awal dan akhir pengerjaan relatif seimbang.';
      }
    }

    const trendBarsHtml = trends.length
      ? trends.map((t) => {
          const label = t.tryout_id === 'DIAG' ? 'Diagnostik' : `${t.tryout_id} (M-${t.window})`;
          return `<div class="bar-row">
            <span><strong>${esc(label)}</strong><br><small class="muted">${esc(t.phase || '')}</small></span>
            <div class="bar-track"><div class="bar-fill ${barClass(t.pct)}" style="width:${Math.min(100, Math.max(0, t.pct))}%"></div></div>
            <span class="bar-num">${esc(t.pct)}% <small class="muted">(${esc(t.correct)}/${esc(t.total)})</small></span>
          </div>`;
        }).join('')
      : '<p class="muted">Belum ada tryout yang dikumpulkan. Setelah siswa menyelesaikan diagnostik, tren skor akan muncul di sini.</p>';

    const subjBarsHtml = subjTrends.length
      ? subjTrends.map((s) => `<div class="bar-row">
          <span><strong>${esc(s.subject)}</strong></span>
          <div class="bar-track"><div class="bar-fill ${barClass(s.pct)}" style="width:${Math.min(100, Math.max(0, s.pct))}%"></div></div>
          <span class="bar-num">${esc(s.pct)}% (${esc(s.c)}/${esc(s.t)})</span>
        </div>`).join('')
      : '<p class="muted">Data per mata uji muncul setelah tryout pertama selesai.</p>';

    const topicBarsHtml = topicTrends.length
      ? topicTrends.map((t) => `<div class="bar-row">
          <span>${esc(t.topic)}</span>
          <div class="bar-track"><div class="bar-fill ${barClass(t.pct)}" style="width:${Math.min(100, Math.max(0, t.pct))}%"></div></div>
          <span class="bar-num">${esc(t.pct)}% (${esc(t.c)}/${esc(t.t)})</span>
        </div>`).join('')
      : '<p class="muted">Rincian topik terlemah hingga terkuat muncul setelah tryout pertama selesai.</p>';

    const matrixHtml = `<div class="matrix-grid">
      ${MATRIX_CELLS.map((c) => `<div class="matrix-cell${activeCell === c.key ? ' active' : ''}">
        <strong>${esc(c.title)}${activeCell === c.key ? ' · Posisi Saat Ini' : ''}</strong>
        <span>${esc(c.desc)}</span>
      </div>`).join('')}
    </div>`;

    const wrongRowsHtml = wrongItems.length
      ? `<div style="overflow-x:auto"><table class="report-table">
          <thead><tr><th>Sumber</th><th>Topik</th><th>Soal</th><th>Jawaban Siswa vs Kunci</th><th>Pembahasan &amp; Cara Cepat</th></tr></thead>
          <tbody>
            ${wrongItems.slice(0, 12).map((w) => `<tr>
              <td><small>${esc(w.source_type === 'drill' ? 'Drill' : 'Tryout')} M-${esc(w.window)}</small></td>
              <td><strong>${esc(w.subject)}</strong><br><small class="muted">${esc(w.topic)}</small></td>
              <td>${esc(w.stem)}</td>
              <td>
                <span style="color:#C2410C"><strong>Siswa:</strong> ${esc(formatChosen(w))}</span><br>
                <span style="color:#166534"><strong>Kunci:</strong> ${esc(formatCorrect(w))}</span>
              </td>
              <td>
                <div>${esc(w.explanation || '-')}</div>
                ${w.shortcut ? `<div class="shortcut-box"><strong>Cara cepat:</strong> ${esc(w.shortcut)}</div>` : ''}
              </td>
            </tr>`).join('')}
          </tbody>
        </table></div>
        ${wrongItems.length > 12 ? `<p class="muted no-print" style="margin-top:10px">Menampilkan 12 dari ${esc(wrongItems.length)} soal salah. Buka tab <strong>Buku Salah Cetak</strong> untuk daftar lengkap siap cetak.</p>` : ''}`
      : '<p class="muted">Belum ada soal salah yang tercatat.</p>';

    return `
      <section class="panel"><h2>Paket</h2>${buy}<div id="e" class="err" hidden></div></section>
      <section class="panel"><h2>Laporan terbaru</h2>${report}</section>
      <section class="panel"><h2>Tryout anak</h2>${atts ? `<ul class="list">${atts}</ul>` : '<p class="muted">Belum ada tryout. Minta anak masuk ke <a href="/child/">ruang anak</a> dengan kode siswa, lalu kerjakan diagnostik.</p>'}</section>

      <section class="panel" aria-labelledby="rep-head">
        <div class="head-row">
          <div>
            <h2 id="rep-head" style="margin-bottom:6px">Laporan Kesiapan Siswa (Ringkasan 60 Detik)</h2>
            <span class="pill ${statusClass(sum.status)}">${esc(sum.status)}</span>
          </div>
          <button type="button" class="btn sky no-print" id="print-report">Cetak / Simpan PDF</button>
        </div>
        <p style="margin-top:12px"><strong>${esc(sum.latest_headline)}</strong></p>
        <div class="disclaimer-box">${esc(sum.disclaimer)}</div>

        <div class="effort-grid">
          <div class="effort-card">
            <div class="label">Tryout Dikerjakan</div>
            <div class="val">${esc(sum.tryouts_completed)} / ${esc(sum.tryouts_total)}</div>
            <p class="sub">Total tryout selesai sepanjang musim</p>
          </div>
          <div class="effort-card">
            <div class="label">Konsistensi Drill</div>
            <div class="val">${esc(sum.drills_completed)} / ${esc(sum.drills_assigned)} sesi</div>
            <p class="sub">Latihan penguatan topik mingguan</p>
          </div>
          <div class="effort-card">
            <div class="label">Jendela Terlewat</div>
            <div class="val">${esc(missed.length)} jendela</div>
            <p class="sub">${esc(missedNote)}</p>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2>Tren Skor &amp; Performa per Mata Uji</h2>
        <h3>Riwayat per Tryout</h3>
        ${trendBarsHtml}
        <h3 style="margin-top:18px">Rata-rata per Mata Uji</h3>
        ${subjBarsHtml}
        <h3 style="margin-top:18px">Peta Topik (Terlemah ke Terkuat)</h3>
        ${topicBarsHtml}
      </section>

      <section class="panel">
        <h2>Manajemen Waktu (Matriks 2×2) &amp; Stamina</h2>
        ${latestTrend && latestTrend.avg_sec != null ? `<p>Rata-rata waktu bersih terakhir: <strong>${esc(latestTrend.avg_sec)} detik/soal</strong>.</p>` : ''}
        ${matrixHtml}
        <div class="disclaimer-box" style="margin-top:14px">
          <strong>Stamina &amp; Penyelesaian Akhir:</strong> ${esc(staminaNote)}
        </div>
      </section>

      ${drillHist.length ? `<section class="panel">
        <h2>Riwayat Drill Penguatan</h2>
        <ul class="list">${drillHist.map((d) => `<li><span><strong>Minggu ke-${esc(d.window)} · ${esc(d.topic)}</strong><br><small class="muted">Fokus: ${esc(d.focus)}</small></span><span><strong>${esc(d.sessions_done)} / ${esc(d.sessions_total)} sesi</strong></span></li>`).join('')}</ul>
      </section>` : ''}

      <section class="panel accent-sun">
        <h2>3 Rekomendasi Mingguan</h2>
        ${recs.length ? `<ol style="margin:0;padding-left:1.3em">${recs.map((r) => `<li style="margin:6px 0">${esc(r)}</li>`).join('')}</ol>` : '<p class="muted">Rekomendasi terbit setelah tryout pertama selesai dianalisa.</p>'}
      </section>

      <section class="panel">
        <h2>Tinjauan Soal Salah</h2>
        ${wrongRowsHtml}
      </section>
    `;
  }

  function renderBukuSalahTab(bsData, filterSubject) {
    if (!bsData) return '<section class="panel"><p class="muted">Memuat Buku Salah…</p></section>';
    const items = bsData.items || [];
    const subjects = Array.from(new Set(items.map((x) => x.subject).filter(Boolean)));
    const filtered = filterSubject ? items.filter((x) => x.subject === filterSubject) : items;

    const addonBanner = (bsData.plan === 'free' || bsData.addon_available)
      ? `<div class="panel accent-sun">
          <strong>Produk add-on untuk pengguna diagnostik gratis (Harga: TBD)</strong>
          <p class="muted" style="margin:6px 0 0">Anda dapat melihat dan mencetak pratinjau soal salah dari diagnostik gratis di bawah ini. Versi lengkap mencakup seluruh riwayat tryout dan drill mingguan.</p>
        </div>`
      : '';

    const cards = filtered.length
      ? filtered.map((item, idx) => {
          const optsHtml = (item.options || []).map((opt, oi) => {
            const isChosen = item.chosen_idx === oi;
            const isCorrect = item.correct_idx === oi;
            const cls = isCorrect ? 'opt-correct' : (isChosen ? 'opt-chosen' : '');
            const tag = isCorrect ? ' (Kunci)' : (isChosen ? ' (Jawaban siswa)' : '');
            return `<li class="${cls}">${esc(LETTERS[oi] || '')}. ${esc(opt)}${esc(tag)}</li>`;
          }).join('');

          return `<article class="buku-card">
            <div class="buku-meta">
              <span class="pill mengejar">#${idx + 1} · ${esc(item.source_type === 'drill' ? 'Drill' : 'Tryout')} Minggu ${esc(item.window)}</span>
              <span class="pill sim">${esc(item.subject)} · ${esc(item.topic)}</span>
            </div>
            <p style="font-weight:700">${esc(item.stem)}</p>
            <ul class="buku-opts">${optsHtml}</ul>
            ${item.chosen_idx == null ? '<p class="muted"><strong>Jawaban siswa:</strong> Tidak dijawab (kosong)</p>' : ''}
            <p><strong>Pembahasan:</strong> ${esc(item.explanation || 'Pembahasan tersedia setelah analisa.')}</p>
            ${item.shortcut ? `<div class="shortcut-box"><strong>Cara cepat terverifikasi:</strong> ${esc(item.shortcut)}</div>` : ''}
          </article>`;
        }).join('')
      : '<section class="panel"><p class="muted">Belum ada soal salah pada filter ini.</p></section>';

    return `
      <section class="panel">
        <div class="head-row">
          <div>
            <h2 style="margin-bottom:4px">Buku Salah Cetak (${esc(filtered.length)} soal)</h2>
            <p class="muted" style="margin:0">Kumpulan soal yang masih keliru beserta pembahasan dan cara cepat terverifikasi untuk dipelajari ulang.</p>
          </div>
          <button type="button" class="btn sky no-print" id="print-buku-salah">Cetak Buku Salah (PDF)</button>
        </div>
        ${subjects.length ? `<div class="field no-print" style="margin-top:14px;margin-bottom:0;max-width:300px">
          <label for="bs-filter">Filter mata uji</label>
          <select id="bs-filter">
            <option value="">Semua mata uji (${esc(items.length)})</option>
            ${subjects.map((s) => `<option value="${esc(s)}"${filterSubject === s ? ' selected' : ''}>${esc(s)}</option>`).join('')}
          </select>
        </div>` : ''}
      </section>
      ${addonBanner}
      ${cards}
    `;
  }

  function renderPrestasiTab(lastClaim) {
    const resultHtml = lastClaim ? `<div class="panel accent-grape" style="margin-top:16px">
      <h3>Kode Diskon Jalur Prestasi Anda</h3>
      <p><span class="discount-code" id="prestasi-code">${esc(lastClaim.discount_code)}</span>
      <button type="button" class="btn line no-print" id="copy-prestasi" style="margin-left:10px">Salin kode</button></p>
      <p style="margin-bottom:4px"><strong>Bentuk:</strong> Diskon (bukan tunai) · <strong>Persen diskon:</strong> ${esc(lastClaim.discount_percent || 'TBD')}</p>
      <p class="muted" style="margin:0">Kode ini dapat dipindahtangankan ke siswa lain apabila tidak digunakan untuk akun ini.</p>
    </div>` : '';

    return `
      <section class="panel">
        <h2>Jalur Prestasi (Kode Diskon)</h2>
        <p class="muted">Jika siswa memiliki sertifikat atau piagam prestasi lomba akademik/non-akademik, ajukan nomor atau referensi bukti di bawah ini untuk menerima kode diskon yang dapat dipindahtangankan. Bentuk penghargaan adalah potongan biaya (bukan tunai); persentase diskon sedang difinalisasi (TBD).</p>
        <form id="prestasi-form" novalidate>
          <div class="field">
            <label for="proof-ref">Nomor atau Referensi Bukti Prestasi</label>
            <input id="proof-ref" type="text" placeholder="Mis. CERT-OSN-2026-014 atau tautan dokumen" required>
            <span class="hint">Tidak perlu mengunggah file rapor sekolah di sini.</span>
          </div>
          <div class="field">
            <label for="proof-note">Catatan singkat (opsional)</label>
            <input id="proof-note" type="text" placeholder="Mis. Juara 2 Olimpiade Sains tingkat kota 2026">
          </div>
          <div id="prestasi-err" class="err" hidden></div>
          <button class="btn solid" type="submit">Ajukan Kode Diskon Prestasi</button>
        </form>
      </section>
      ${resultHtml}
    `;
  }

  // ---------- dashboard ----------
  async function viewHome() {
    render('<p class="muted">Memuat…</p>');
    let h, rep, full;
    try {
      const [a, b, c] = await Promise.all([
        api.get('/api/parent/home'),
        api.get('/api/parent/report/latest'),
        api.get('/api/parent/reports')
      ]);
      if (a.status === 401) {
        sessionStorage.removeItem(TK);
        return viewLogin();
      }
      h = a.json;
      rep = b.json;
      full = c.status === 200 ? c.json : null;
    } catch (e) {
      return render('<div class="err">Tidak tersambung. Muat ulang halaman.</div>');
    }

    let activeTab = 'ringkasan';
    let bukuSalahCache = null;
    let bsFilter = '';
    let lastPrestasiClaim = null;

    function paintDashboard() {
      let bodyHtml = '';
      if (activeTab === 'ringkasan') bodyHtml = renderOverviewTab(h, rep, full);
      else if (activeTab === 'buku-salah') bodyHtml = renderBukuSalahTab(bukuSalahCache, bsFilter);
      else if (activeTab === 'prestasi') bodyHtml = renderPrestasiTab(lastPrestasiClaim);

      render(`<h1>Dashboard</h1>
        <div class="sub-tabs no-print" role="tablist" aria-label="Menu Dashboard">
          <button type="button" class="tab-btn" role="tab" id="tab-ringkasan" aria-selected="${activeTab === 'ringkasan'}">Ringkasan &amp; Laporan</button>
          <button type="button" class="tab-btn" role="tab" id="tab-buku-salah" aria-selected="${activeTab === 'buku-salah'}">Buku Salah Cetak</button>
          <button type="button" class="tab-btn" role="tab" id="tab-prestasi" aria-selected="${activeTab === 'prestasi'}">Jalur Prestasi</button>
        </div>
        <div id="tab-content">${bodyHtml}</div>`);

      $('#tab-ringkasan').onclick = () => { activeTab = 'ringkasan'; paintDashboard(); };
      $('#tab-buku-salah').onclick = async () => {
        activeTab = 'buku-salah';
        paintDashboard();
        if (!bukuSalahCache) {
          try {
            const r = await api.get('/api/parent/buku-salah');
            if (r.status === 401) { sessionStorage.removeItem(TK); return viewLogin(); }
            if (r.status === 200) bukuSalahCache = r.json;
          } catch (e) { bukuSalahCache = { plan: h.plan, addon_available: h.plan === 'free', items: [], total: 0 }; }
          if (activeTab === 'buku-salah') paintDashboard();
        }
      };
      $('#tab-prestasi').onclick = () => { activeTab = 'prestasi'; paintDashboard(); };

      bindTabHandlers();
    }

    function bindTabHandlers() {
      const err = $('#e');
      const order = $('#order');
      if (order) {
        order.onclick = async () => {
          order.disabled = true;
          const r = await api.post('/api/parent/orders', {});
          if (r.status === 200 && r.json.payment_url) { location.href = r.json.payment_url; return; }
          if (r.status === 200) return viewHome();
          err.textContent = ERR[r.json && r.json.error] || 'Pesanan belum berhasil dibuat.';
          err.hidden = false;
          order.disabled = false;
        };
      }

      const pay = $('#pay');
      if (pay) {
        pay.onclick = async () => {
          pay.disabled = true;
          pay.textContent = 'Memproses…';
          const r = await api.post('/api/playtest/orders/' + pay.dataset.o + '/pay', {});
          if (r.status === 200) return viewHome();
          err.textContent = 'Pembayaran simulasi gagal.';
          err.hidden = false;
          pay.disabled = false;
        };
      }

      const printRep = $('#print-report');
      if (printRep) printRep.onclick = () => window.print();

      const printBs = $('#print-buku-salah');
      if (printBs) printBs.onclick = () => window.print();

      const filterEl = $('#bs-filter');
      if (filterEl) {
        filterEl.onchange = () => {
          bsFilter = filterEl.value;
          paintDashboard();
        };
      }

      const pForm = $('#prestasi-form');
      if (pForm) {
        pForm.addEventListener('submit', async (ev) => {
          ev.preventDefault();
          const btn = $('button[type=submit]', pForm), perr = $('#prestasi-err');
          btn.disabled = true; perr.hidden = true;
          try {
            const r = await api.post('/api/parent/prestasi', {
              proof_ref: $('#proof-ref').value.trim(),
              note: $('#proof-note').value.trim()
            });
            if (r.status === 200) {
              lastPrestasiClaim = r.json;
              paintDashboard();
              return;
            }
            if (r.status === 422) {
              perr.textContent = FIELD.proof_ref;
            } else {
              perr.textContent = ERR[r.json && r.json.error] || 'Pengajuan belum berhasil.';
            }
          } catch (e) {
            perr.textContent = 'Tidak tersambung ke internet. Coba lagi.';
          }
          perr.hidden = false;
          btn.disabled = false;
        });
      }

      const copyP = $('#copy-prestasi');
      if (copyP && lastPrestasiClaim) {
        copyP.onclick = async () => {
          try {
            await navigator.clipboard.writeText(lastPrestasiClaim.discount_code);
            copyP.textContent = 'Tersalin';
          } catch (e) {
            copyP.textContent = 'Salin manual';
          }
        };
      }
    }

    paintDashboard();
  }

  route();
})();
