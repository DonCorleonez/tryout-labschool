/* Landing: tandai akhir pekan yang sedang/akan berjalan dan hitung hari menuju tes. Tanpa animasi. */
(function () {
  'use strict';
  const now = new Date();
  const test = new Date('2027-01-31T08:00:00+07:00');
  const days = Math.ceil((test - now) / 86400000);
  const cd = document.getElementById('countdown');
  if (cd && days > 0) cd.textContent = days + ' hari lagi menuju tes tertulis, Minggu 31 Januari 2027';
  const rows = Array.from(document.querySelectorAll('.weeks li[data-fri]'));
  const next = rows.find((li) => new Date(li.dataset.fri + 'T00:00:00+07:00').getTime() + 3 * 86400000 > now.getTime());
  if (next) { next.classList.add('now'); next.setAttribute('aria-current', 'date'); }
})();
