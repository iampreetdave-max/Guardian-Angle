"""The cross-cutting questions — the ones asked about the project, not a screen.

Hand-written rather than generated: these are the questions that decide how a
judge scores you, and the answers have to be short enough to say out loud.
"""

FAQ = [
    ("Is this real crime data?",
     "No, and we say so on every slide. It is fully synthetic and deterministic — "
     "generated from a fixed seed, no real individuals named anywhere. "
     "Ahmedabad publishes no per-neighbourhood crime dataset, so the alternative "
     "was inventing numbers and calling them real. The locality weightings are "
     "editorial estimates and documented as such."),

    ("What database?",
     "SQLite for everything relational — 34 tables, no ORM, plain sqlite3. "
     "FAISS for vectors, in three separate indexes. ChromaDB for the legal RAG. "
     "FAISS stores vectors and returns an ID; SQLite turns that ID into a camera, "
     "a timestamp and a thumbnail."),

    ("Why SQLite and not Postgres?",
     "It has to run on a police station machine with no internet and no DBA. "
     "Three files in a Docker volume, one compose command, done. "
     "The trade-off is real: SQLite is single-writer. That is fine at station "
     "scale, and because there is no ORM coupling, moving to Postgres and pgvector "
     "is a swap of the database and index layers, not a rewrite."),

    ("What models, and do you need a GPU?",
     "No GPU. Everything is CPU: torch 2.5.1+cpu, CUDA unavailable. "
     "Four models do the work — CLIP ViT-B/32 for text and image embeddings, "
     "YOLOv8n for detection, ArcFace/InsightFace for faces, and MiniLM for the "
     "legal RAG. YOLOv8n is 6.3 MB; the nano variant was chosen deliberately "
     "because detection runs on every keyframe of every camera, on CPU."),

    ("Search feels fast for a model — what is actually happening?",
     "Search never runs a vision model. All the expensive work — CLIP, YOLO, "
     "ArcFace — happens once at ingest. A query only embeds your sentence and "
     "does a FAISS lookup. Warm text search measures 37 to 80 ms."),

    ("How accurate is the search?",
     "84.6% recall on a hand-labelled ground-truth set, measured at the top-60 "
     "the UI actually uses. An earlier number of ours was lower because it was "
     "measured at top-20, which is not what the product does — we corrected it."),

    ("How accurate is the prediction?",
     "Hit-Rate@10 of about 0.78 and PAI@10 of about 2.34, from rolling-origin "
     "cross-validation with bootstrap confidence intervals, against an oracle "
     "ceiling so you can see how much headroom is left. It is a backtest on "
     "synthetic data — it demonstrates the methodology is sound, not that the "
     "model predicts real Ahmedabad crime."),

    ("Isn't this just off-the-shelf models glued together?",
     "The models are off the shelf and we do not pretend otherwise — that is the "
     "correct engineering decision, not a shortcut. The work is in what sits "
     "between them: per-detection crop embeddings so 'red car' can find one "
     "specific car, tracking so repeat sightings collapse into one result, and "
     "the honest evaluation harness. Anyone can call YOLO. Fewer people ablate "
     "their own scoring function and publish that two of its three terms "
     "contribute nothing."),

    ("What is genuinely novel here?",
     "Three things. Per-object CLIP retrieval, which lets a query exceed the "
     "detector's own vocabulary — YOLO has no class for 'red'. The closed loop "
     "from footage to evidence to a drafted legal instrument. And measured "
     "validation with the negative results left in."),

    ("What does not work?",
     "CLIP cannot do negation — 'empty street with no people' returns the busiest "
     "scene, because the model has no operator for 'no'. Hindi and Gujarati "
     "documents render malformed as PDFs because ReportLab does no Indic shaping; "
     "the interface is fully translated but the PDF body is not. And face "
     "matching degrades on low-resolution CCTV, which is most real CCTV."),

    ("Does it scale? You have 16 cameras, Ahmedabad has thousands.",
     "Honestly: not as it stands. Ingest is the bottleneck, and ultralytics is "
     "not thread-safe — we measured 7 of 8 concurrent threads crashing, so there "
     "is a global inference lock that caps throughput. The upgrade path is "
     "per-thread model instances and a worker queue, and the ceiling is named in "
     "a comment in the code rather than hidden."),

    ("What about privacy and misuse? This is face recognition on public CCTV.",
     "It is the right question to ask. Face search is scoped to footage already "
     "lawfully held, every search is written to an audit log, access is "
     "role-based, and nothing leaves the machine — no cloud inference, no API "
     "keys, no telemetry. It is a tool for an investigator working an existing "
     "case, not a surveillance dragnet, and the offline-first design is part of "
     "that argument rather than incidental to it."),

    ("What would it cost to deploy?",
     "Effectively the hardware already in the station. No GPU, no per-query API "
     "cost, no cloud bill. That is the whole point of running CPU-only and "
     "offline."),

    ("Why offline-first?",
     "Because station connectivity is unreliable and evidence should not leave "
     "the building. The hosted link is a convenience for you to click; the "
     "product is designed to work with the network unplugged."),

    ("How long did this take, and what is the code like?",
     "The interesting number is not lines of code. Six demo-breaking bugs were "
     "found and fixed by testing rather than reading — four of them were failing "
     "silently behind HTTP 200s. The evaluation harness exists specifically so "
     "claims can be checked rather than asserted."),
]


def faq_page(prev_nav, next_nav, prev_i, next_i):
    items = "".join(
        f"<details><summary>{q}</summary><div class='ans'>{a}</div></details>"
        for q, a in FAQ)
    return f"""
<section class="page" id="p{prev_i+1}" data-name="Common questions">
  <div class="crumb">Asked about the project, not a screen</div>
  <h1>Common questions</h1>
  <p class="lede">The {len(FAQ)} you are most likely to get. Short enough to say
    out loud. The uncomfortable ones are answered honestly on purpose &mdash;
    a judge who catches you hedging stops believing the rest.</p>
  <div class="qa">{items}</div>
  <div class="pager">
    <a class="nav prev" href="#p{prev_i}">&larr; {prev_nav}</a>
    <a class="nav next" href="#p{next_i}">{next_nav} &rarr;</a>
  </div>
</section>"""
