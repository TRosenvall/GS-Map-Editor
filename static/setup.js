const $ = s => document.querySelector(s);
const esc = t => String(t ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-GSMap': '1' }, body: JSON.stringify(body) };
  let r;
  try { r = await fetch(path, opt); } catch (e) { return { error: T("The app stopped answering. Quit it and open it again.") }; }
  try { return await r.json(); } catch (e) { return { error: T('Something went wrong (HTTP {status}).', { status: r.status }) }; }
}
let running = false;
async function refresh() {
  const r = await api('/api/setup/checks');
  if (r.error) { $('#msg').innerHTML = `<span class="err">${esc(r.error)}</span>`; return; }
  if (r.problem) { $('#msg').innerHTML = `<span class="err">${esc(r.problem)}</span>`; }
  const firstTodo = r.checks.findIndex(c => !c.ok);
  $('#steps').innerHTML = r.checks.map((c, i) => `<div class="step ${c.ok ? 'ok' : i === firstTodo ? 'todo' : ''}">
      <div class="mark">${c.ok ? '✓' : i + 1}</div>
      <div><b>${esc(c.title)}</b><span class="d">${esc(c.detail)}</span></div>
      <div>${c.action && i === firstTodo ? `<button class="primary" data-step="${c.id}" ${running ? 'disabled' : ''}>${esc(c.action)}</button>` : ''}</div>
    </div>`).join('');
  $('#launch').disabled = firstTodo !== -1 || running;
  if (firstTodo === -1 && !running && !r.problem) $('#msg').innerHTML = `<span class="ok">${T('Everything is ready.')}</span>`;
}
$('#steps').onclick = async e => {
  const step = e.target.closest('[data-step]')?.dataset.step; if (!step) return;
  const r = await api('/api/setup/run', { step });
  if (r.error) { $('#msg').innerHTML = `<span class="err">${esc(r.error)}</span>`; return; }
  if (step === 'brew') { $('#msg').textContent = T('brew.sh is open in your browser. Install Homebrew, then press Check again.'); return; }
  if (step === 'clt') $('#msg').textContent = T('Apple\'s installer should be open. When it finishes, press Check again.');
  follow();
};
async function follow() {
  running = true; refresh(); $('#log').style.display = 'block'; $('#log').textContent = '';
  let since = 0;
  for (;;) {
    const s = await api(`/api/setup/job?since=${since}`);
    if (s.error) { running = false; $('#msg').innerHTML = `<span class="err">${esc(s.error)}</span>`; return; }
    if (s.log?.length) { $('#log').textContent += s.log.join('\n') + '\n'; $('#log').scrollTop = $('#log').scrollHeight; }
    since = s.next ?? since;
    $('#msg').textContent = s.done ? '' : T('{name}: working… (you can leave this open)', { name: s.name });
    if (s.done) {
      running = false;
      $('#msg').innerHTML = s.ok ? `<span class="ok">${T('{name}: done.', { name: esc(s.name) })}</span>` : `<span class="err">${T("{name} didn't finish. You can press the button to try again; if it keeps failing, copy the text above into a bug report.", { name: esc(s.name) })}</span>`;
      break;
    }
    await new Promise(r => setTimeout(r, 700));
  }
  refresh();
}
$('#recheck').onclick = () => { $('#msg').textContent = ''; refresh(); };
$('#choose').onclick = async () => {
  let r = await api('/api/setup/choose', {});
  if (r.ask) {
    // No folder picker outside the Mac app: the path is typed instead.
    const folder = prompt(T('The full path of your copy of the game source (alchemy), for example {example}:', { example: '/home/you/alchemy' }));
    if (!folder) return;
    r = await api('/api/setup/choose', { folder });
  }
  if (r.error) $('#msg').innerHTML = `<span class="err">${esc(r.error)}</span>`;
  else if (r.root) $('#msg').innerHTML = `<span class="ok">${T('Using {folder}.', { folder: esc(r.root) })}</span>`;
  refresh();
};
$('#launch').onclick = async () => {
  $('#msg').textContent = T('Opening the editor… (reading every map takes a few seconds)');
  const r = await api('/api/setup/launch', {});
  if (r.error) { $('#msg').innerHTML = `<span class="err">${esc(r.error)}</span>`; return; }
  location.href = r.url;
};
(async () => { await refresh(); const j = await api('/api/setup/job'); if (j && !j.done) follow(); })();
