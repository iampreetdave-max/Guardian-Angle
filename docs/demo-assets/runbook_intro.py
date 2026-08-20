"""The START HERE page — the only page that is written rather than generated.

Everything else in the runbook is rendered from measured test results. This one
is the presenter's cockpit: the two links, the route, the logins, and the short
list of things that end a demo.
"""

LOCAL = "http://localhost:8080"
LIVE = "https://ominous-space-happiness-wrqrp69j95jv3g6-8080.app.github.dev"


def intro_page(total, tot_tested, tot_pass, tot_fail, first_nav):
    return f"""
<section class="page on" id="p0" data-name="START HERE">
  <div class="crumb">Start here</div>
  <h1>Demo runbook</h1>
  <p class="lede">Every screen below was driven in a real browser overnight &mdash;
    {tot_tested} individual controls clicked, typed into and measured.
    {tot_pass} passed, {tot_fail} did not. What follows is what actually happens,
    not what the code suggests should happen.</p>

  <div class="hero">
    <a class="hero-link" href="{LOCAL}" target="_blank" rel="noopener">
      <span class="dot" id="dl2"></span>
      <b>Local</b><span>localhost:8080</span>
      <em>Present from this. No network needed.</em>
    </a>
    <a class="hero-link" href="{LIVE}" target="_blank" rel="noopener">
      <span class="dot" id="dv2"></span>
      <b>Live</b><span>Codespace</span>
      <em>Hand this to judges. Verified: 16 cameras, same data.</em>
    </a>
  </div>

  <h2 class="h-show">The six-minute route</h2>
  <ol class="show route-list">
    <li><div class="what">Dashboard &mdash; &ldquo;this is a live station, not a mockup&rdquo;</div>
      <div class="why">2,000+ complaints, 9 cases, 16 feeds. Point at the 14-day chart:
        every bar populated, including today.</div></li>
    <li><div class="what">VisionScan &mdash; search &ldquo;red car&rdquo; in Object mode</div>
      <div class="steps"><b>Do:</b> Object tab &rarr; Grouping moments ON &rarr; red car &rarr; Enter</div>
      <div class="why">24 cards, each a distinct tracked vehicle with a box drawn on it.
        This is the moment that lands. Say: &ldquo;YOLO has no class for
        <em>red</em> &mdash; the system routes around its own model&rsquo;s vocabulary.&rdquo;</div></li>
    <li><div class="what">Suspect Face &mdash; upload the probe crop</div>
      <div class="steps"><b>Do:</b> Suspect Face tab &rarr; upload
        <code>docs/demo-assets/suspect_face.jpg</code></div></li>
    <li><div class="what">Draft FIR in Arbiter &mdash; the hand-off button on the results header</div>
      <div class="why">Shows the pipeline: footage &rarr; evidence &rarr; legal instrument,
        with sections retrieved from a real corpus.</div></li>
    <li><div class="what">City Map &mdash; the predictive forecast</div>
      <div class="why">Where the hardest questions come. Answers are on that page,
        including the ablation that found two of the three terms contribute nothing.</div></li>
    <li><div class="what">Language &rarr; &#2361;&#2367;&#2344;&#2381;&#2342;&#2368; &mdash; the whole UI switches</div>
      <div class="why">Per-user setting, ~760 keys. Search queries stay English on
        purpose &mdash; CLIP&rsquo;s text encoder is English-only. Say that before they ask.</div></li>
  </ol>

  <h2 class="h-warn">Do not click these</h2>
  <ul class="warn">
    <li><b>Admin &rarr; security &rarr; &ldquo;Sign out all my sessions&rdquo;</b> &mdash;
      logs you out instantly, mid-demo.</li>
    <li><b>Any query phrased as a negation</b> (&ldquo;empty street with
      <em>no</em> people&rdquo;) &mdash; CLIP cannot do negation and returns the busiest
      scene. If asked, own it: it is a property of the model, not a bug in the app.</li>
    <li><b>Hindi or Gujarati PDF documents</b> &mdash; the UI translates, but ReportLab
      does no Indic shaping so the PDF body renders malformed. Demo PDFs in English.</li>
    <li><b>Do not run <code>demo_reset.py</code></b> before presenting &mdash; it wipes
      the closed cases, evidence and ratings that make the dashboard look alive.</li>
  </ul>

  <h2 class="h-in">Logins</h2>
  <table class="inputs"><tbody>
    <tr><td class="f">Station Admin</td><td><code class="copy">admin@city.gov</code>
      <code class="copy">admin123</code></td><td class="x">Everything. Use this.</td></tr>
    <tr><td class="f">Officer</td><td><code class="copy">officer@city.gov</code>
      <code class="copy">officer123</code></td><td class="x">For showing role-based access.</td></tr>
  </tbody></table>

  <h2 class="h-num">If something breaks</h2>
  <ul class="nums">
    <li><b>A screen is empty or spinning</b> &mdash; reload the tab first. Most
      one-off failures overnight were the backend restarting, not a real fault.</li>
    <li><b>Thumbnails show as broken images</b> &mdash; you hit the rate limiter.
      Wait ten seconds and re-run the search.</li>
    <li><b>The live link is down</b> &mdash; switch to local and keep going. Say the
      hosted copy is a convenience; the product is offline-first by design. That is
      a genuine strength, not a save.</li>
    <li><b>Do not debug on stage.</b> Move to the next screen and come back.</li>
  </ul>

  <div class="pager"><span></span>
    <a class="nav next" href="#p1">{first_nav} &rarr;</a></div>
</section>"""


EXTRA_CSS = """
.hero{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:22px 0 8px}
.hero-link{display:grid;gap:3px;padding:16px 18px;border-radius:11px;text-decoration:none;
  background:linear-gradient(180deg,#15213a,#111c31);border:1px solid #26385a;color:var(--ink)}
.hero-link:hover{border-color:var(--gold)}
.hero-link b{font-size:17px}
.hero-link span:not(.dot){font-family:var(--mono);font-size:12.5px;color:#8fd4ff}
.hero-link em{color:var(--dim);font-size:12.5px;font-style:normal;margin-top:4px}
.hero-link .dot{position:absolute;margin-top:6px;margin-left:-1px}
.hero-link{position:relative;padding-left:34px}
.hero-link .dot{left:16px;top:20px;position:absolute;margin:0}
ol.route-list li{padding-top:13px;padding-bottom:13px}
@media (max-width:900px){.hero{grid-template-columns:1fr}}
"""
