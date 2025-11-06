let DREAMS_DATA=[];

function renderDreambookCount(){
  const L=(typeof I18N!=="undefined" ? (I18N[document.documentElement.lang]||I18N.ru) : I18N.ru);
  const counter=document.getElementById('dreamCount');
  if(!DREAMS_DATA.length){ counter.textContent=L.dbNoData; return; }
  counter.textContent=L.dbFound.replace("{n}", DREAMS_DATA.length);
}

(function(){
  const DATA_URL = location.pathname.includes('/oneiro-scope')
    ? '/oneiro-scope/data/dreams_curated.json'
    : 'data/dreams_curated.json';

  const L=(typeof I18N!=="undefined" ? (I18N[document.documentElement.lang]||I18N.ru) : I18N.ru);

  const dbTbody = document.querySelector('#dreamTable tbody');
  const counter = document.getElementById('dreamCount');
  const search = document.getElementById('dreamSearch');

  fetch(DATA_URL, {cache:'no-store'})
    .then(r=>r.ok?r.json():[])
    .then(j=>{ DREAMS_DATA = Array.isArray(j)? j : []; renderDreambookCount(); render(DREAMS_DATA); })
    .catch(()=>{ counter.textContent = L.dbNoData; });

  function render(rows){
    dbTbody.innerHTML = '';
    rows.slice(0,500).forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:600">${(r.symbol||'').toString()}</td>
        <td>${((r.modern_interpretation||'')+'').slice(0,220)}${((r.modern_interpretation||'').length>220?'…':'')}</td>
        <td>${(r.confidence??'').toString()}</td>`;
      dbTbody.appendChild(tr);
    });
    counter.textContent = L.dbFound.replace("{n}", rows.length);
  }

  function filter(q){
    q = q.trim().toLowerCase();
    if (!q) return DREAMS_DATA;
    return DREAMS_DATA.filter(r =>
      (r.symbol||'').toLowerCase().includes(q) ||
      (r.contexts||[]).some(c => (c||'').toLowerCase().includes(q))
    );
  }

  if(search){
    search.placeholder = L.dbSearchPlaceholder;
    search.addEventListener('input', (e)=> render(filter(e.target.value)));
  }

  /* ===== Клиентский «Разбор сна» ===== */
  const dreamEl = document.getElementById("dreamText");
  const lunarEl = document.getElementById("lunarHint");
  const btn = document.getElementById("analyzeBtn");
  const box = document.getElementById("interpretResult");
  const chips = document.getElementById("hitSymbols");
  const explain = document.getElementById("explain");
  const advices = document.getElementById("advices");
  const status = document.getElementById("interpretStatus");

  function clientOnlyAnalyze(text, lunarDay){
    const L=(I18N[document.documentElement.lang]||I18N.ru);
    const t = (text||"").toLowerCase();
    const hits = DREAMS_DATA.filter(r => t.includes((r.symbol||"").toLowerCase()));
    const top = hits.slice(0,5);

    const symList = top.map(h => `• <b>${h.symbol}</b>: ${(h.modern_interpretation||'').slice(0,180)}${(h.modern_interpretation||'').length>180?'…':''}`).join('<br>');
    const lunarNote = (lunarDay && window.TABLES?.ru?.[lunarDay])
      ? `<div class="muted" style="margin-top:6px">Лунные сутки ${lunarDay}: ${window.TABLES.ru[lunarDay].type} — ${window.TABLES.ru[lunarDay].notes}</div>`
      : "";

    explain.innerHTML = top.length
      ? `<p>${L.interpretFoundHeading || 'Найденные символы и ориентиры (оценочно):'}</p><p>${symList}</p>${lunarNote}`
      : `<p class="muted">${L.interpretNoSymbols}</p>`;

    advices.innerHTML = L.adviceDefault;

    chips.innerHTML = "";
    top.forEach(h=>{
      const b=document.createElement('button');
      b.className='btn';
      b.style.cssText='padding:6px 10px;border-radius:20px;background:#0F1418;border:1px solid var(--border)';
      b.textContent = h.symbol;
      b.title = (h.modern_interpretation||'').slice(0,240);
      chips.appendChild(b);
    });

    box.style.display='block';
  }

  btn?.addEventListener('click', ()=>{
    const L=(I18N[document.documentElement.lang]||I18N.ru);
    status.textContent = L.interpretAnalyzing;
    try{
      const text = (dreamEl?.value||"").trim();
      const lunarDay = Number(lunarEl?.value) || null;
      if(!text){ dreamEl?.focus(); status.textContent=""; return; }
      clientOnlyAnalyze(text, lunarDay);
    } finally {
      status.textContent = "";
    }
  });
})();

