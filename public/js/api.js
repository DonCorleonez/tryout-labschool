/* Klien API tipis. Token sesi disimpan di memori (bukan localStorage) untuk anak; orang tua boleh sessionStorage. */
(function (root) {
  'use strict';
  function Api(base, getToken, simTime) {
    return {
      async post(path, body) { return this._do('POST', path, body); },
      async get(path) { return this._do('GET', path); },
      async _do(method, path, body) {
        const h = { 'Content-Type': 'application/json' }; const t = getToken && getToken(); if (t) h['X-Token'] = t;
        if (simTime) h['X-Sim-Time'] = simTime();          // hanya dipakai di mode playtest server
        const res = await fetch(base + path, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
        let json = null; try { json = await res.json(); } catch (e) { }
        return { status: res.status, json };
      }
    };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { Api };
  else root.Api = Api;
})(typeof window !== 'undefined' ? window : globalThis);
