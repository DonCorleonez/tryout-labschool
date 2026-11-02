/* Runner tryout (frontend). Tanggung jawab: merekam jejak per soal, menyimpan lokal (tahan refresh/putus),
 * mengirim batch event ke server secara idempoten, dan mengumpulkan jawaban dengan percobaan ulang.
 * TIDAK pernah memegang kunci jawaban. Timer resmi = deadline dari server; jam klien hanya untuk tampilan.
 * Tidak bergantung pada kerangka kerja; dipakai dari modul tampilan mana pun. */
(function (root) {
  'use strict';
  function Runner(opts) {
    this.api = opts.api;                 // {post(path, body) -> Promise<{status, json}>}
    this.attempt = opts.attempt;         // ref 'att_xxx'
    this.n = opts.questions.length;
    this.deadline = Date.parse(opts.deadlineAt);
    this.store = opts.storage || null;   // localStorage-like (opsional)
    this.now = opts.now || (() => Date.now());
    this.key = 'runner:' + this.attempt;
    this.t0 = this.now();
    const saved = this._load();
    this.state = saved || { seq: 0, cur: null, answers: {}, flags: {}, queue: [], sent: 0, submitted: false };
  }
  Runner.prototype._load = function () { try { return this.store ? JSON.parse(this.store.getItem(this.key) || 'null') : null; } catch (e) { return null; } };
  Runner.prototype._save = function () { try { if (this.store) this.store.setItem(this.key, JSON.stringify(this.state)); } catch (e) { /* kuota penuh: abaikan */ } };
  Runner.prototype._ev = function (kind, q, value) {
    this.state.queue.push({ seq: ++this.state.seq, kind: kind, q: q, value: value, ms: this.now() - this.t0 });
    this._save();
  };
  Runner.prototype.visit = function (q) { if (this.state.cur != null) { /* waktu soal sebelumnya dihitung server dari selisih visit */ } this.state.cur = q; this._ev('visit', q); };
  Runner.prototype.answer = function (q, idx) { this.state.answers[q] = idx; this._ev('answer', q, idx); };
  Runner.prototype.toggleFlag = function (q) { this.state.flags[q] = !this.state.flags[q]; this._ev('flag', q, this.state.flags[q]); };
  Runner.prototype.idle = function (sec) { if (this.state.cur != null && sec > 0) this._ev('idle', this.state.cur, Math.round(sec)); };
  Runner.prototype.remainingSec = function () { return Math.max(0, Math.round((this.deadline - this.now()) / 1000)); };
  Runner.prototype.progress = function () { const a = this.state.answers; return { answered: Object.keys(a).length, total: this.n, flagged: Object.keys(this.state.flags).filter(k => this.state.flags[k]).length }; };
  // Pantau visibilitas tab: waktu tersembunyi dicatat sebagai idle (dikeluarkan dari waktu bersih oleh server).
  Runner.prototype.attachVisibility = function (doc) {
    let hiddenAt = null; const self = this;
    doc.addEventListener('visibilitychange', function () {
      if (doc.hidden) hiddenAt = self.now(); else if (hiddenAt != null) { self.idle((self.now() - hiddenAt) / 1000); hiddenAt = null; }
    });
  };
  // Kirim semua event tertunda. Aman diulang: server mengabaikan seq yang sudah ada.
  Runner.prototype.flush = async function () {
    if (!this.state.queue.length) return { sent: 0 };
    const batch = this.state.queue.slice();
    const r = await this.api.post('/api/child/attempts/' + this.attempt + '/events', { events: batch });
    if (r.status !== 200) throw new Error('flush gagal ' + r.status);
    this.state.queue = this.state.queue.filter(e => e.seq > batch[batch.length - 1].seq); this.state.sent += batch.length; this._save();
    return { sent: batch.length };
  };
  // Kumpulkan: flush -> submit. Gagal jaringan => jawaban tetap tersimpan lokal, UI boleh memanggil lagi.
  Runner.prototype.submit = async function (retries) {
    retries = retries == null ? 2 : retries; let lastErr;
    this._ev('end', this.state.cur);
    for (let i = 0; i <= retries; i++) {
      try {
        await this.flush();
        const r = await this.api.post('/api/child/attempts/' + this.attempt + '/submit', { answers: this.state.answers, flags: this.state.flags });
        if (r.status === 409) return { ok: false, closed: true, error: r.json.error };      // jendela tutup: jangan coba ulang
        if (r.status !== 200) throw new Error('submit ' + r.status);
        this.state.submitted = true; this._save(); return { ok: true, result: r.json };
      } catch (e) { lastErr = e; }
    }
    return { ok: false, retryable: true, error: String(lastErr) };
  };
  Runner.prototype.clear = function () { try { if (this.store) this.store.removeItem(this.key); } catch (e) { } };
  if (typeof module !== 'undefined') module.exports = Runner; else root.Runner = Runner;
})(typeof window !== 'undefined' ? window : this);
