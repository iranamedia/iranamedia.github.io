(function () {
  var $ = function (id) { return document.getElementById(id); };
  var tv = $('tv'), stage = $('tvStage'), prog = $('tvProg');
  var slides = [], i = 0, timer = null, paused = false, soundOn = true, faVoices = [], speaking = false, startAt = 0, dur = 0, raf = 0;
  var synth = window.speechSynthesis || null, radio = false, wake = null, loopGap = 15000;
  // Voice ID: Baktash - one voice for the whole bulletin; prefers a device voice named "Baktash", else the first Persian voice
  var VOICE_ID = 'Baktash';
  var profiles = { intro: { v: 0, pitch: 1, rate: 0.95 }, news: { v: 0, pitch: 1, rate: 0.95 }, prince: { v: 0, pitch: 1, rate: 0.95 }, sum: { v: 0, pitch: 1, rate: 0.95 } };
  function pickVoice() {
    var all = []; try { all = synth.getVoices(); } catch (e) {}
    var re = new RegExp(VOICE_ID, 'i');
    for (var j = 0; j < all.length; j++) { if (re.test(all[j].name) || re.test(all[j].voiceURI || '')) return all[j]; }
    return faVoices[0];
  }

  // Pronunciation lexicon for the radio voice: changes only what is spoken, never what is shown
  var SAY_FIX = [
    [/ضرب\s*[\u200c]?\s*و\s*[\u200c]?\s*شتم/g, 'ضَرب و شَتم'],
    [/زرتشت\s+احمدی\s+راغب/g, 'زَرتُشتِ احمدیِ راغب'],
    [/احمدی\s+راغب/g, 'احمدیِ راغب'],
    [/حال[\u200c\s]?وش/g, 'حال‌وَش']
  ];
  function sayFix(t) { SAY_FIX.forEach(function (r) { t = t.replace(r[0], r[1]); }); return t; }
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function loadVoices() {
    if (!synth) return;
    try { faVoices = synth.getVoices().filter(function (v) { return /^fa/i.test(v.lang); }); } catch (e) { faVoices = []; }
  }
  if (synth) { loadVoices(); try { synth.onvoiceschanged = loadVoices; } catch (e) {} }

  function build() {
    slides = [];
    var stamp = txt(document.querySelector('.wrap .stamp'));
    var stories = [].slice.call(document.querySelectorAll('.wrap article.story'));
    var heads = [].slice.call(document.querySelectorAll('.headlines li')).map(txt);
    if (!heads.length) heads = stories.map(function (a) { return txt(a.querySelector('h3')); });
    $('tvStamp').textContent = stamp;
    $('tvLogo').src = (document.querySelector('.logo') || {}).src || '';
    var run = $('tvRun'); run.textContent = '';
    heads.forEach(function (h) { var s = document.createElement('span'); s.textContent = h; run.appendChild(s); });
    var top = heads.slice(0, 3);
    slides.push({ kind: 'intro', voice: 'intro', label: 'رسانه ایرانا', title: 'تیترهای مهم', list: top,
      say: sayFix('اینجا رسانه ایرانا است. ' + stamp + '. تیترهای مهم: ' + top.join('. ')) });
    var rot = ['news', 'prince', 'sum'];
    stories.forEach(function (a, n) {
      var t = txt(a.querySelector('h3')), b = txt(a.querySelector('p'));
      slides.push({ kind: a.closest('.prince') ? 'prince' : 'news', art: a.getAttribute('data-kind') || 'general', voice: rot[n % rot.length], label: 'رسانه ایرانا', title: t, body: b, say: sayFix(t + '. ' + b) });
    });
    document.querySelectorAll('.wrap section').forEach(function (sec) {
      var h = sec.querySelector(':scope > h2');
      if (h && txt(h) === 'جمع‌بندی') { var b = txt(sec.querySelector('p')); slides.push({ kind: 'sum', voice: 'intro', label: 'جمع‌بندی', title: 'جمع‌بندی', body: b, say: 'جمع‌بندی. ' + b }); }
    });
  }

  function render() {
    var s = slides[i]; stage.textContent = '';
    var w = document.createElement('div'); w.className = 'tv-slide';
    if (s.art) { var art = document.createElement('div'); art.className = 'tv-art'; art.setAttribute('data-kind', s.art); art.setAttribute('aria-hidden', 'true'); w.appendChild(art); }
    var l = document.createElement('span'); l.className = 'tv-label' + (s.kind === 'prince' ? ' prince' : ''); l.textContent = s.label; w.appendChild(l);
    var h = document.createElement('h2'); h.className = 'tv-title'; h.textContent = s.title; w.appendChild(h);
    if (s.list) { var ul = document.createElement('ul'); ul.className = 'tv-list'; s.list.forEach(function (x) { var li = document.createElement('li'); li.textContent = x; ul.appendChild(li); }); w.appendChild(ul); }
    if (s.body) { var p = document.createElement('p'); p.className = 'tv-body'; p.textContent = s.body; w.appendChild(p); }
    if (soundOn && !faVoices.length && i === 0) { var n = document.createElement('p'); n.className = 'tv-notice'; n.textContent = 'صدای فارسی روی این دستگاه نیست؛ پخش بی‌صدا ادامه می‌یابد.'; w.appendChild(n); }
    stage.appendChild(w); stage.scrollTop = 0;
    $('tvCount').textContent = (i + 1).toLocaleString('fa-IR') + ' از ' + slides.length.toLocaleString('fa-IR');
    $('tvPrev').disabled = i === 0;
  }

  function stopAll() { clearTimeout(timer); timer = null; cancelAnimationFrame(raf); speaking = false; if (synth) { try { synth.cancel(); } catch (e) {} } }
  function tick() { var f = Math.min(1, (Date.now() - startAt) / dur); prog.style.width = (f * 100) + '%'; if (f < 1 && !paused) raf = requestAnimationFrame(tick); }

  function speak(s) {
    var p = profiles[s.voice || s.kind], parts = s.say.split(/(?<=[.!؟?؛])\s+/).filter(Boolean), k = 0;
    var voice = pickVoice();
    speaking = true;
    function next() {
      if (!speaking) return;
      if (k >= parts.length) { speaking = false; advance(); return; }
      var u = new SpeechSynthesisUtterance(parts[k++]);
      u.lang = /^fa/i.test(voice.lang) ? voice.lang : 'fa-IR'; u.voice = voice; u.pitch = p.pitch; u.rate = p.rate;
      u.onend = next; u.onerror = next;
      try { synth.speak(u); } catch (e) { speaking = false; timed(s); }
    }
    next();
  }
  function timed(s) { dur = Math.max(8000, s.say.length * 75); startAt = Date.now(); prog.style.width = '0'; raf = requestAnimationFrame(tick); timer = setTimeout(advance, dur); }

  function show(n) {
    stopAll(); i = Math.max(0, Math.min(slides.length - 1, n)); render();
    if (paused) { prog.style.width = '0'; return; }
    var s = slides[i];
    if (soundOn && synth && faVoices.length) { prog.style.width = '100%'; speak(s); } else timed(s);
  }
  function advance() {
    if (i < slides.length - 1) { show(i + 1); return; }
    if (radio) { prog.style.width = '100%'; timer = setTimeout(function () { build(); show(0); }, loopGap); return; }
    paused = true; $('tvPause').textContent = 'از نو'; prog.style.width = '100%';
  }

  function open(asRadio) {
    radio = !!asRadio; tv.classList.toggle('radio', radio);
    build(); if (!slides.length) return;
    tv.hidden = false; document.body.style.overflow = 'hidden'; paused = false; $('tvPause').textContent = 'ایست';
    loadVoices();
    var hasFa = !!(synth && faVoices.length);
    $('tvSound').disabled = !hasFa; if (!hasFa) { $('tvSound').textContent = 'صدا در دسترس نیست'; $('tvSound').setAttribute('aria-pressed', 'false'); }
    try { if (tv.requestFullscreen) tv.requestFullscreen().catch(function () {}); } catch (e) {}
    show(0); $('tvPause').focus();
    if (radio && navigator.wakeLock) { navigator.wakeLock.request('screen').then(function (w) { wake = w; }).catch(function () {}); }
  }
  function close() {
    stopAll(); radio = false; tv.classList.remove('radio'); if (wake) { try { wake.release(); } catch (e) {} wake = null; } tv.hidden = true; document.body.style.overflow = '';
    try { if (document.fullscreenElement) document.exitFullscreen().catch(function () {}); } catch (e) {}
    $('tvOpen').focus();
  }

  $('tvOpen').addEventListener('click', function () { open(false); });
  $('radioOpen').addEventListener('click', function () { open(true); });
  // When the hourly update reaches an open page, keep the radio running on the new news
  try { if (window.claude && window.claude.hot && window.claude.hot.snapshot) window.claude.hot.snapshot(function () { return { radio: radio && !tv.hidden }; }); } catch (e) {}
  function boot(d) { if (d && d.radio) open(true); }
  try { if (window.claude && window.claude.hot && window.claude.hot.ready) window.claude.hot.ready(boot); else boot(window.claude && window.claude.hot && window.claude.hot.data); } catch (e) {}
  document.addEventListener('visibilitychange', function () { if (radio && !tv.hidden && document.visibilityState === 'visible' && navigator.wakeLock && !wake) navigator.wakeLock.request('screen').then(function (w) { wake = w; }).catch(function () {}); });
  $('tvClose').addEventListener('click', close);
  $('tvNext').addEventListener('click', function () { if (i < slides.length - 1) show(i + 1); });
  $('tvPrev').addEventListener('click', function () { show(i - 1); });
  $('tvPause').addEventListener('click', function () {
    if ($('tvPause').textContent === 'از نو') { paused = false; $('tvPause').textContent = 'ایست'; show(0); return; }
    paused = !paused; $('tvPause').textContent = paused ? 'ادامه' : 'ایست'; show(i);
  });
  $('tvSound').addEventListener('click', function () {
    soundOn = !soundOn; this.setAttribute('aria-pressed', String(soundOn)); this.textContent = soundOn ? 'صدا: روشن' : 'صدا: خاموش'; show(i);
  });
  document.addEventListener('keydown', function (e) {
    if (tv.hidden) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') $('tvNext').click();
    else if (e.key === 'ArrowRight') $('tvPrev').click();
    else if (e.key === ' ') { e.preventDefault(); $('tvPause').click(); }
  });
  document.addEventListener('fullscreenchange', function () { if (!document.fullscreenElement && !tv.hidden) { /* stay open in window */ } });
})();
