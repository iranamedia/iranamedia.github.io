(function () {
  var $ = function (id) { return document.getElementById(id); };
  var audio = $('audio'), player = $('player'), current = null;

  function fmt(s) { if (!isFinite(s)) return '0:00'; s = Math.floor(s); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }

  function render(b) {
    $('stamp').hidden = false; $('stamp').textContent = b.stamp;
    $('pSub').textContent = b.stamp;
    var sec = $('news'); sec.textContent = '';
    (b.items || []).forEach(function (it) {
      var a = document.createElement('article'); a.className = 'story';
      var h = document.createElement('h3'); h.textContent = it.title; a.appendChild(h);
      var p = document.createElement('p'); p.textContent = it.body; a.appendChild(p);
      sec.appendChild(a);
    });
    var src = 'latest.mp3?v=' + encodeURIComponent(b.stamp);
    if (current !== src) {                           // a new hour: load the new broadcast
      var wasPlaying = !audio.paused; current = src; audio.src = src;
      if (wasPlaying) audio.play().catch(function () {});
    }
  }

  function load() {
    fetch('latest.json?t=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(render)
      .catch(function () { if (!current) $('news').innerHTML = '<p class="status">اتصال برقرار نیست؛ کمی بعد دوباره بکوشید.</p>'; });
  }

  $('play').addEventListener('click', function () {
    if (!current) return;
    if (audio.paused) audio.play().catch(function () { $('pSub').textContent = 'پخش ممکن نشد؛ دوباره بزنید.'; });
    else audio.pause();
  });
  audio.addEventListener('play', function () { player.classList.add('on'); $('play').setAttribute('aria-label', 'ایست'); });
  audio.addEventListener('pause', function () { player.classList.remove('on'); $('play').setAttribute('aria-label', 'پخش برنامهٔ این ساعت'); });
  audio.addEventListener('timeupdate', function () {
    $('tCur').textContent = fmt(audio.currentTime); $('tDur').textContent = fmt(audio.duration);
    $('fill').style.width = (audio.duration ? audio.currentTime / audio.duration * 100 : 0) + '%';
  });
  $('bar').addEventListener('click', function (e) {
    if (!audio.duration) return; var r = this.getBoundingClientRect();
    audio.currentTime = (e.clientX - r.left) / r.width * audio.duration;
  });

  // Install: Android/desktop prompt, iPhone hint
  var deferred = null;
  window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); deferred = e; $('installBtn').hidden = false; });
  $('installBtn').addEventListener('click', function () { if (deferred) { deferred.prompt(); deferred = null; this.hidden = true; } });
  var ios = /iphone|ipad|ipod/i.test(navigator.userAgent), standalone = window.navigator.standalone || matchMedia('(display-mode: standalone)').matches;
  if (ios && !standalone) $('iosHint').classList.add('show');

  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(function () {});
  if ('mediaSession' in navigator) navigator.mediaSession.metadata = new MediaMetadata({ title: 'رادیو ایرانا', artist: 'رسانه ایرانا', artwork: [{ src: 'icon-512.png', sizes: '512x512', type: 'image/png' }] });

  load();
  setInterval(load, 5 * 60 * 1000);                  // check for the new hour every five minutes
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') load(); });
})();
