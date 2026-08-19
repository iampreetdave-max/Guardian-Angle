"""Template half of the runbook generator — CSS, JS and the document shell.

Kept in its own module so the shell-quoting hazards of a big CSS/JS blob never
touch the data-shaping code in build_runbook.py.
"""

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#070d1a; --bg2:#0c1526; --card:#111c31; --line:#1e2d47;
  --ink:#e8eefc; --dim:#93a3c0; --faint:#6b7c9c;
  --gold:#f0a830; --green:#37c98a; --red:#f4645f; --amber:#e8a838; --blue:#5b9dff;
  --mono:ui-monospace,"Cascadia Code",Consolas,monospace;
}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15.5px/1.6 -apple-system,"Segoe UI",Inter,system-ui,sans-serif;
  display:grid;grid-template-columns:290px 1fr;min-height:100vh}

aside{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--bg2);
  border-right:1px solid var(--line);padding:18px 0 40px}
.brand{padding:0 18px 14px;border-bottom:1px solid var(--line);margin-bottom:10px}
.brand b{font-size:17px;letter-spacing:.2px}
.brand small{display:block;color:var(--faint);font-size:11.5px;margin-top:3px}
.links{padding:12px 14px;display:grid;gap:7px;border-bottom:1px solid var(--line);margin-bottom:10px}
.links a{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;
  background:#16233c;color:var(--ink);text-decoration:none;font-size:12.5px;font-weight:600;
  border:1px solid var(--line)}
.links a:hover{background:#1c2c4a}
.dot{width:8px;height:8px;border-radius:50%;background:var(--faint);flex:none}
.dot.up{background:var(--green);box-shadow:0 0 7px var(--green)}
.dot.down{background:var(--red)}
nav ol{list-style:none;margin:0;padding:0 10px}
nav a{display:flex;align-items:center;gap:9px;padding:7px 10px;border-radius:7px;
  color:var(--dim);text-decoration:none;font-size:13px;line-height:1.3}
nav a:hover{background:#16233c;color:var(--ink)}
nav a.on{background:var(--gold);color:#231a06;font-weight:700}
.ni{font:600 10.5px/1 var(--mono);color:var(--faint);min-width:17px;text-align:right}
nav a.on .ni{color:#5c4610}
.badge{margin-left:auto;background:var(--red);color:#fff;font:700 10px/1 var(--mono);
  padding:3px 5px;border-radius:5px}

main{padding:0 46px 90px;max-width:1120px}
.page{display:none;padding-top:34px;animation:fadein .18s ease}
.page.on{display:block}
@keyframes fadein{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.crumb{color:var(--faint);font:600 11px/1 var(--mono);letter-spacing:.9px;text-transform:uppercase}
h1{font-size:29px;margin:9px 0 6px;letter-spacing:-.4px;line-height:1.2}
.lede{color:var(--dim);font-size:16px;margin:0 0 14px;max-width:80ch}
.route{background:#101a2e;border-left:3px solid var(--blue);padding:9px 13px;
  border-radius:0 7px 7px 0;font-size:13.5px;color:var(--dim);margin-bottom:26px}
.route b{color:var(--ink)}

h2{font-size:12px;letter-spacing:1.3px;text-transform:uppercase;margin:32px 0 12px;
  padding-bottom:7px;border-bottom:1px solid var(--line)}
.h-show{color:var(--gold)} .h-in{color:var(--blue)} .h-q{color:var(--green)}
.h-warn{color:var(--red)} .h-num{color:var(--dim)}

ol.show{list-style:none;counter-reset:s;margin:0;padding:0;display:grid;gap:13px}
ol.show li{counter-increment:s;position:relative;background:linear-gradient(180deg,#15213a,#111c31);
  border:1px solid #26385a;border-left:3px solid var(--gold);border-radius:10px;
  padding:15px 17px 15px 54px}
ol.show li::before{content:counter(s);position:absolute;left:15px;top:14px;
  width:25px;height:25px;border-radius:50%;background:var(--gold);color:#231a06;
  font:800 13px/25px var(--mono);text-align:center}
.what{font-size:16.5px;font-weight:650;line-height:1.4}
.steps{margin-top:9px;background:#0a1226;border:1px solid var(--line);
  border-radius:7px;padding:8px 11px;font-family:var(--mono);font-size:12.5px;color:#cfe0ff}
.steps b{color:var(--gold);font-family:inherit}
.why{margin-top:8px;color:var(--dim);font-size:13.5px}

table{width:100%;border-collapse:collapse;font-size:13.5px}
.inputs th,.tested th{text-align:left;color:var(--faint);font:600 10.5px/1 var(--mono);
  letter-spacing:.8px;text-transform:uppercase;padding:0 10px 8px;border-bottom:1px solid var(--line)}
.inputs td{padding:10px;border-bottom:1px solid #16233c;vertical-align:top}
.inputs .f{color:var(--dim);width:23%}
.inputs .x{color:var(--dim);width:42%;font-size:13px}
code.copy{display:inline-block;background:#0a1226;border:1px solid #2a3d5f;color:#8fd4ff;
  padding:5px 9px;border-radius:6px;font-family:var(--mono);font-size:13px;cursor:pointer;
  user-select:all;transition:.12s}
code.copy:hover{border-color:var(--blue);background:#111d33}
code.copy.done{background:var(--green);color:#04240f;border-color:var(--green)}

.qa details{background:var(--card);border:1px solid var(--line);border-radius:9px;margin-bottom:8px}
.qa summary{cursor:pointer;padding:12px 15px;font-weight:620;font-size:14.5px;list-style:none}
.qa summary::-webkit-details-marker{display:none}
.qa summary::before{content:"> ";color:var(--green);font-weight:800;font-family:var(--mono)}
.qa details[open] summary::before{content:"v "}
.qa details[open] summary{border-bottom:1px solid var(--line)}
.ans{padding:13px 15px;color:var(--dim);font-size:14px;white-space:pre-wrap}

ul.warn,ul.nums{margin:0;padding-left:19px;display:grid;gap:7px}
ul.warn li{color:#ffc9c6} ul.nums li{color:var(--dim);font-size:13.5px}

details.log{margin-top:30px;border-top:1px solid var(--line);padding-top:14px}
details.log summary{cursor:pointer;color:var(--faint);font:600 11.5px/1 var(--mono);
  letter-spacing:.6px;text-transform:uppercase;padding:6px 0}
.tested td{padding:8px 10px;border-bottom:1px solid #16233c;vertical-align:top;font-size:12.5px}
.tested tr.bad td{background:#2a1114} .tested tr.warn td{background:#291f0f}
.tag{font:700 9.5px/1 var(--mono);padding:3px 6px;border-radius:4px;white-space:nowrap}
.tag.ok{background:#0d3a26;color:var(--green)} .tag.bad{background:#3d1417;color:var(--red)}
.tag.warn{background:#3a2c0c;color:var(--amber)} .tag.na{background:#1c2740;color:var(--faint)}

.pager{display:flex;justify-content:space-between;gap:14px;margin-top:44px;
  padding-top:18px;border-top:1px solid var(--line)}
.nav{color:var(--ink);text-decoration:none;background:var(--card);border:1px solid var(--line);
  padding:11px 17px;border-radius:9px;font-size:13.5px;font-weight:620;max-width:47%}
.nav:hover{border-color:var(--gold);color:var(--gold)}

.kbd{position:fixed;right:16px;bottom:14px;color:var(--faint);font:11px/1 var(--mono);
  background:var(--bg2);border:1px solid var(--line);padding:7px 11px;border-radius:7px}

@media print{
  body{grid-template-columns:1fr;background:#fff;color:#000}
  aside,.kbd,.pager{display:none}
  .page{display:block !important;page-break-after:always}
}
@media (max-width:900px){
  body{grid-template-columns:1fr}
  aside{position:static;height:auto}
  main{padding:0 18px 60px}
}
"""

JS = r"""
const pages=[...document.querySelectorAll('.page')];
const links=[...document.querySelectorAll('nav a')];
let cur=0;
function show(i){
  i=Math.max(0,Math.min(pages.length-1,i));
  pages.forEach((p,k)=>p.classList.toggle('on',k===i));
  links.forEach((a,k)=>a.classList.toggle('on',k===i));
  cur=i;
  history.replaceState(null,'','#p'+i);
  const on=links[i]; if(on) on.scrollIntoView({block:'nearest'});
  window.scrollTo(0,0);
}
document.addEventListener('click',ev=>{
  const a=ev.target.closest('nav a, a.nav');
  if(a && a.getAttribute('href') && a.getAttribute('href').startsWith('#p')){
    ev.preventDefault(); show(+a.getAttribute('href').slice(2)); return;
  }
  const c=ev.target.closest('code.copy');
  if(c && navigator.clipboard){
    navigator.clipboard.writeText(c.textContent).then(()=>{
      c.classList.add('done'); setTimeout(()=>c.classList.remove('done'),750);
    });
  }
});
document.addEventListener('keydown',ev=>{
  if(/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName))return;
  if(ev.key==='ArrowRight'||ev.key==='PageDown'){ev.preventDefault();show(cur+1);}
  if(ev.key==='ArrowLeft'||ev.key==='PageUp'){ev.preventDefault();show(cur-1);}
  if(ev.key==='Home')show(0);
  if(ev.key==='End')show(pages.length-1);
});
// Reachability only: no-cors tells us the host answered, not that it is healthy.
function ping(url,el){
  if(!el)return;
  const t=setTimeout(()=>{el.className='dot down';},6000);
  fetch(url+'/api/health',{mode:'no-cors',cache:'no-store'})
    .then(()=>{clearTimeout(t);el.className='dot up';})
    .catch(()=>{clearTimeout(t);el.className='dot down';});
}
const m=/^#p(\d+)$/.exec(location.hash);
show(m?+m[1]:0);
"""


def document(*, total, tot_tested, tot_pass, tot_in, tot_q, nav, pages_html, local, live):
    return f"""<title>CityShield Demo Runbook</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<aside>
  <div class="brand">
    <b>Demo Runbook</b>
    <small>CityShield &middot; VisionScan &mdash; {total} screens,
      {tot_pass}/{tot_tested} controls passing</small>
  </div>
  <div class="links">
    <a href="{local}" target="_blank" rel="noopener">
      <span class="dot" id="dl"></span>Local &nbsp;localhost:8080</a>
    <a href="{live}" target="_blank" rel="noopener">
      <span class="dot" id="dv"></span>Live &nbsp;Codespace</a>
  </div>
  <nav><ol>{nav}</ol></nav>
</aside>
<main>{pages_html}</main>
<div class="kbd">&larr; &rarr; to move &middot; click any value to copy</div>
<script>{JS}
[['dl','dl2',{local!r}],['dv','dv2',{live!r}]].forEach(([a,b,u])=>{{
  ping(u,document.getElementById(a)); ping(u,document.getElementById(b));
}});
</script>"""
