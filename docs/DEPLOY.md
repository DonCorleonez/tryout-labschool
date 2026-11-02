# Deploy uji: labschool.doncorleonez.my.id

Satu proses Python (stdlib) + SQLite, di belakang Cloudflare Tunnel. Tidak perlu membuka port di router.

## 1. Di mesin server (Linux, Python 3.11+)
```bash
git clone https://github.com/DonCorleonez/tryout-labschool.git /opt/tryout
cd /opt/tryout/reference && python3 -c "import sqlite3; print('sqlite ok')"
```

Berkas `/etc/tryout.env` (izin 600, JANGAN masuk git):
```
HOST=127.0.0.1
PORT=8080
DB_PATH=/var/lib/tryout/play.db
PLAYTEST=1                         # mode uji: jam simulasi ?sim=... dan tombol bayar simulasi aktif
PUBLIC_HOST=labschool.doncorleonez.my.id
PRODUCTION_HOSTS=                  # kosong selama uji. Saat jual sungguhan: isi domain produksi, set PLAYTEST=0
TRUST_PROXY=1                      # IP asli dari header Cloudflare
WEBHOOK_SECRET=<acak 32+ karakter> # python3 -c "import secrets;print(secrets.token_urlsafe(32))"
ADMIN_TOKEN=<acak 32+ karakter>
BANK_DIR=                          # kosong = bank STUB (uji). Isi folder bank tervalidasi bila sudah ada.
```

Layanan systemd `/etc/systemd/system/tryout.service`:
```ini
[Unit]
Description=Tryout Labschool
After=network.target

[Service]
EnvironmentFile=/etc/tryout.env
WorkingDirectory=/opt/tryout/reference
ExecStart=/usr/bin/python3 server.py
Restart=always
User=tryout
StateDirectory=tryout

[Install]
WantedBy=multi-user.target
```
```bash
sudo useradd -r -s /usr/sbin/nologin tryout
sudo systemctl daemon-reload && sudo systemctl enable --now tryout
curl -s http://127.0.0.1:8080/healthz      # {"ok": true, "playtest": true}
```

## 2. Cloudflare Tunnel (domain doncorleonez.my.id sudah di Cloudflare)
```bash
cloudflared tunnel login
cloudflared tunnel create tryout
cloudflared tunnel route dns tryout labschool.doncorleonez.my.id
```
`~/.cloudflared/config.yml`:
```yaml
tunnel: tryout
credentials-file: /root/.cloudflared/<ID-TUNNEL>.json
ingress:
  - hostname: labschool.doncorleonez.my.id
    service: http://127.0.0.1:8080
  - service: http_status:404
```
```bash
sudo cloudflared service install && sudo systemctl enable --now cloudflared
```

## 3. Cek setelah naik
- `https://labschool.doncorleonez.my.id/` landing tampil; `/robots.txt` berisi `Disallow: /` (mode uji tidak diindeks).
- Daftar di `/parent/#/daftar`, catat kode, masuk ke `/child/`.
- Uji jendela tryout sebelum Jumat: `/child/?sim=2026-11-06T18:00` (hanya bekerja saat PLAYTEST=1).

## 4. Update
```bash
cd /opt/tryout && git pull && sudo systemctl restart tryout
```

## 5. Sebelum menerima pembayaran sungguhan
- `PLAYTEST=0`, isi `PRODUCTION_HOSTS` dengan domain jual, `BANK_DIR` wajib terisi. Server menolak start bila salah satu tidak terpenuhi.
- Adaptor gateway (P5) dan email (P6) harus sudah terpasang.
- Cadangan harian `DB_PATH` ke luar mesin.
