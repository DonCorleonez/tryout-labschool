const assert = require('assert'); const Runner = require('../public/js/runner.js');
const mem = () => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = v; }, removeItem: k => { delete m[k]; }, _m: m }; };
let t = 0; const now = () => t;
function mkApi(script) { const calls = []; return { calls, async post(path, body) { calls.push({ path, body }); return script(path, calls.length); } }; }
(async () => {
  // 1) merekam jejak dan menghitung kemajuan
  const store = mem(), api = mkApi(() => ({ status: 200, json: { diterima: 1 } }));
  const r = new Runner({ api, attempt: 'att_x', questions: new Array(12), deadlineAt: new Date(7200 * 1000).toISOString(), storage: store, now });
  r.visit(1); t = 3000; r.answer(1, 2); r.toggleFlag(1); t = 5000; r.visit(2); t = 8000; r.answer(2, 0); r.answer(2, 1);
  assert.deepStrictEqual(r.progress(), { answered: 2, total: 12, flagged: 1 });
  assert.strictEqual(r.remainingSec(), 7200 - 8);
  // 2) tahan refresh: instance baru memuat antrean yang sama
  const r2 = new Runner({ api, attempt: 'att_x', questions: new Array(12), deadlineAt: new Date(7200 * 1000).toISOString(), storage: store, now });
  assert.strictEqual(r2.state.queue.length, 6); assert.strictEqual(r2.state.answers[2], 1);
  // 3) flush idempoten dan urutan seq naik
  await r2.flush(); assert.strictEqual(api.calls[0].body.events.map(e => e.seq).join(), '1,2,3,4,5,6'); assert.strictEqual(r2.state.queue.length, 0);
  // 4) submit: gagal jaringan -> bisa dicoba lagi; jawaban tetap ada
  let n = 0; const flaky = mkApi((p) => { if (p.endsWith('/submit') && n++ < 3) throw new Error('offline'); return { status: 200, json: { score: 1 } }; });
  const r3 = new Runner({ api: flaky, attempt: 'att_y', questions: new Array(12), deadlineAt: new Date(7200 * 1000).toISOString(), storage: mem(), now });
  r3.visit(1); r3.answer(1, 3);
  const bad = await r3.submit(1); assert.strictEqual(bad.ok, false); assert.strictEqual(bad.retryable, true); assert.strictEqual(r3.state.answers[1], 3);
  const good = await r3.submit(2); assert.strictEqual(good.ok, true); assert.strictEqual(r3.state.submitted, true);
  // 5) jendela tutup (409) tidak dicoba ulang
  const closed = mkApi((p) => (p.endsWith('/submit') ? { status: 409, json: { error: 'waktu_habis' } } : { status: 200, json: {} }));
  const r4 = new Runner({ api: closed, attempt: 'att_z', questions: new Array(12), deadlineAt: new Date(7200 * 1000).toISOString(), storage: mem(), now });
  r4.visit(1); const c = await r4.submit(5); assert.deepStrictEqual([c.ok, c.closed, c.error], [false, true, 'waktu_habis']);
  assert.strictEqual(closed.calls.filter(x => x.path.endsWith('/submit')).length, 1);
  // 6) idle dicatat dari tab tersembunyi
  const listeners = {}; const doc = { hidden: false, addEventListener: (e, f) => { listeners[e] = f; } };
  const r5 = new Runner({ api, attempt: 'att_i', questions: new Array(12), deadlineAt: new Date(9e6).toISOString(), storage: mem(), now }); r5.visit(4); r5.attachVisibility(doc);
  t = 10000; doc.hidden = true; listeners.visibilitychange(); t = 55000; doc.hidden = false; listeners.visibilitychange();
  const idle = r5.state.queue.find(e => e.kind === 'idle'); assert.strictEqual(idle.value, 45); assert.strictEqual(idle.q, 4);
  console.log('runner.test.js OK (6 pengujian)');
})().catch(e => { console.error(e); process.exit(1); });
