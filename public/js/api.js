/* Klien API tipis. Token sesi disimpan di memori (bukan localStorage) untuk anak; orang tua boleh sessionStorage. */
(function (root) {
  'use strict';
  let _memDev = '';
  function _deviceId() {
    const key = 'tryout_device_id';
    try {
      const existing = root.localStorage && root.localStorage.getItem(key);
      if (existing) return existing;
    } catch (e) { }
    if (_memDev) return _memDev;
    let id = '';
    try {
      if (root.crypto && typeof root.crypto.randomUUID === 'function') {
        id = 'dev_' + root.crypto.randomUUID().replace(/-/g, '').slice(0, 16);
      } else if (root.crypto && typeof root.crypto.getRandomValues === 'function') {
        const buf = new Uint8Array(8);
        root.crypto.getRandomValues(buf);
        id = 'dev_' + Array.from(buf, b => b.toString(16).padStart(2, '0')).join('');
      }
    } catch (e) { }
    if (!id) id = 'dev_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-6);
    _memDev = id;
    try {
      if (root.localStorage) root.localStorage.setItem(key, id);
    } catch (e) { }
    return id;
  }
  function Api(base, getToken, simTime) {
    return {
      deviceId: _deviceId,
      async post(path, body) { return this._do('POST', path, body); },
      async get(path) { return this._do('GET', path); },
      async _do(method, path, body) {
        const h = { 'Content-Type': 'application/json', 'X-Device-Id': _deviceId() };
        const t = getToken && getToken(); if (t) h['X-Token'] = t;
        if (simTime) h['X-Sim-Time'] = simTime();          // hanya dipakai di mode playtest server
        const res = await fetch(base + path, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
        let json = null; try { json = await res.json(); } catch (e) { }
        return { status: res.status, json };
      }
    };
  }
  Api.deviceId = _deviceId;
  if (typeof module !== 'undefined' && module.exports) module.exports = { Api };
  else root.Api = Api;
})(typeof window !== 'undefined' ? window : globalThis);
