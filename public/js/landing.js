/* Landing: hitung mundur hari tes, tandai minggu berjalan, demo 1 soal interaktif, dan modal pratinjau akses. */
(function () {
  'use strict';

  // 1. Hitung mundur & penanda akhir pekan aktif pada peta musim
  var now = new Date();
  var test = new Date('2027-01-31T08:00:00+07:00');
  var days = Math.ceil((test - now) / 86400000);
  var cd = document.getElementById('countdown');
  if (cd && days > 0) {
    cd.textContent = days + ' hari lagi menuju tes tertulis, Minggu 31 Januari 2027';
  }
  var rows = Array.prototype.slice.call(document.querySelectorAll('.weeks li[data-fri]'));
  var next = rows.find(function (li) {
    return new Date(li.dataset.fri + 'T00:00:00+07:00').getTime() + 3 * 86400000 > now.getTime();
  });
  if (next) {
    next.classList.add('now');
    next.setAttribute('aria-current', 'date');
  }

  // 2. Demo interaktif 1 soal pecahan
  var CORRECT_CHOICE = 'B';
  var TRAP_NOTES = {
    A: 'Pilihan 4/6 muncul jika pembilang langsung ditambah pembilang (3+1=4) dan penyebut ditambah penyebut (4+2=6). Pada penjumlahan pecahan, penyebut tidak boleh langsung dijumlahkan sebelum disamakan!',
    C: 'Pilihan 4/4 muncul jika penyebut disamakan menjadi 4, tetapi pembilang 1/2 lupa ikut dikalikan 2. Saat penyebut 2 dikali 2 menjadi 4, pembilang 1 juga harus dikali 2 menjadi 2.',
    D: 'Pilihan 3/8 adalah hasil perkalian (3×1)/(4×2), bukan penjumlahan. Perhatikan tanda operasi + pada soal sebelum menghitung!'
  };

  var optButtons = Array.prototype.slice.call(document.querySelectorAll('.demo-opt'));
  var feedbackBox = document.getElementById('demo-feedback');
  var fbCard = document.getElementById('demo-fb-card');
  var fbTitle = document.getElementById('demo-fb-title');
  var fbMsg = document.getElementById('demo-fb-msg');
  var trapBox = document.getElementById('demo-trap');
  var trapText = document.getElementById('demo-trap-text');
  var retryBtn = document.getElementById('demo-retry');

  function resetDemo() {
    optButtons.forEach(function (btn) {
      btn.disabled = false;
      btn.classList.remove('is-wrong', 'is-correct', 'is-right-hint');
      btn.setAttribute('aria-pressed', 'false');
    });
    if (feedbackBox) feedbackBox.hidden = true;
    if (trapBox) trapBox.hidden = true;
    if (fbCard) fbCard.classList.remove('ok', 'no');
    if (optButtons[0]) optButtons[0].focus();
  }

  function handleChoice(btn) {
    var choice = btn.dataset.choice;
    var isRight = choice === CORRECT_CHOICE;

    optButtons.forEach(function (item) {
      item.disabled = true;
      item.classList.remove('is-wrong', 'is-correct', 'is-right-hint');
      item.setAttribute('aria-pressed', item === btn ? 'true' : 'false');
      if (!isRight && item.dataset.choice === CORRECT_CHOICE) {
        item.classList.add('is-right-hint');
      }
    });

    if (isRight) {
      btn.classList.add('is-correct');
      fbCard.classList.remove('no');
      fbCard.classList.add('ok');
      fbTitle.textContent = 'Tepat sekali! Jawaban 5/4 benar.';
      fbMsg.textContent = 'Kamu sudah menyamakan penyebut pecahan dengan benar sebelum menjumlahkannya.';
      trapBox.hidden = true;
    } else {
      btn.classList.add('is-wrong');
      fbCard.classList.remove('ok');
      fbCard.classList.add('no');
      fbTitle.textContent = 'Belum tepat — jawaban yang benar adalah 5/4 (pilihan B).';
      fbMsg.textContent = 'Tidak apa-apa! Di ruang latihan, setiap kesalahan langsung dijelaskan langkah demi langkah.';
      trapText.textContent = TRAP_NOTES[choice] || TRAP_NOTES.A;
      trapBox.hidden = false;
    }

    feedbackBox.hidden = false;
  }

  optButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      handleChoice(btn);
    });
  });

  if (retryBtn) {
    retryBtn.addEventListener('click', resetDemo);
  }

  // 3. Modal Pratinjau Akses (Paywall Modal)
  var modal = document.getElementById('paywall-modal');
  var openModalBtn = document.getElementById('open-paywall');
  var closeModalBtn = document.getElementById('close-paywall');
  var backdrop = document.getElementById('paywall-backdrop');

  function openModal() {
    if (!modal) return;
    modal.hidden = false;
    if (closeModalBtn) closeModalBtn.focus();
  }

  function closeModal() {
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    if (openModalBtn) openModalBtn.focus();
  }

  if (openModalBtn) openModalBtn.addEventListener('click', openModal);
  if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
  if (backdrop) backdrop.addEventListener('click', closeModal);
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') closeModal();
  });
})();
