// Rebuild the Marcel archive in data/ (docs/FINDINGS.md #67).
//
// Baseball-Reference returns HTTP 403 to automated fetches, so this is not a
// Python script: paste it into the DevTools console on any baseball-reference
// .com page, in a normal logged-in browser session. It reads the projection
// tables straight out of the DOM and POSTs them to a loopback receiver.
//
// Why the DOM and not the rendered table: the player's Baseball-Reference id
// lives in `data-append-csv` on the player cell. It is NOT in the visible
// pitcher table, so copy-pasting that table loses it and forces fuzzy name
// matching. Read from the DOM it is present, and the bbref -> fg_id join
// through `key_bbref` is exact at 100% on all six files.
//
// The file year is the season PROJECTED, not the page it came from: BR files
// the 2026 projections under /leagues/majors/2025-projections.shtml.
//
// Run order:
//   1. python3 scripts/fetch_chadwick.py     (must keep key_bbref)
//   2. start the receiver, e.g.
//        python3 -c "$(sed -n '/^RECEIVER/,$p' scripts/fetch_marcel.js)"
//      or any tiny server that writes POST bodies to data/<name>.
//   3. paste this file into the console
//   4. python3 scripts/validate_marcel.py    (must print ALL IDENTITIES HOLD)

const PAGES = { 2026: '2025', 2025: '2024', 2024: '2023' };  // projected: source
const PORT = 8765;

function tableToCsv(doc, id) {
  const t = doc.getElementById(id);
  if (!t) return null;
  const hr = [...t.querySelectorAll('thead tr')].pop();
  const ths = [...hr.querySelectorAll('th')];
  const cols = ths.map(th => th.getAttribute('data-stat'));
  const labels = ths.map(th => th.innerText.trim());
  const q = v => (v.includes(',') || v.includes('"'))
    ? '"' + v.replace(/"/g, '""') + '"' : v;
  const out = [labels.concat(['Name-additional']).join(',')];
  for (const tr of t.querySelectorAll('tbody tr')) {
    if (tr.classList.contains('thead')) continue;   // BR repeats the header
    const pc = tr.querySelector('[data-stat="player"]');
    if (!pc) continue;
    const cells = cols.map(c => {
      const el = tr.querySelector('[data-stat="' + c + '"]');
      return q(el ? el.innerText.trim() : '');
    });
    out.push(cells.concat([pc.getAttribute('data-append-csv') || '']).join(','));
  }
  return out.join('\n');
}

const report = [];
for (const [proj, src] of Object.entries(PAGES)) {
  const r = await fetch('/leagues/majors/' + src + '-projections.shtml');
  // Secondary tables ship wrapped in HTML comments (BR's lazy-load); the live
  // page un-comments them but a fetched copy does not, so strip them.
  const html = (await r.text()).split('<!--').join('').split('-->').join('');
  const doc = new DOMParser().parseFromString(html, 'text/html');
  for (const [role, tid] of [['hitters', 'marcel_batting'],
                             ['pitchers', 'marcel_pitching']]) {
    const csv = tableToCsv(doc, tid);
    const name = 'marcel_' + proj + '_' + role + '.csv';
    if (!csv) { report.push(name + ': TABLE NOT FOUND'); continue; }
    const post = await fetch('http://127.0.0.1:' + PORT + '/' + name,
      { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: csv });
    report.push(name + ': ' + post.status + ' (' + (csv.split('\n').length - 1) + ' rows)');
  }
}
report;

/* RECEIVER -- extract with sed as shown above, or keep your own.
import re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
DEST = Path("data"); OK = re.compile(r"^marcel_(2024|2025|2026)_(hitters|pitchers)\.csv$")
class H(BaseHTTPRequestHandler):
    def _c(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    def do_OPTIONS(self):
        self.send_response(204); self._c(); self.end_headers()
    def do_POST(self):
        n = self.path.lstrip("/")
        if not OK.match(n):
            self.send_response(400); self._c(); self.end_headers(); return
        b = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        (DEST / n).write_bytes(b); print("wrote", n, len(b), flush=True)
        self.send_response(200); self._c(); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", 8765), H).serve_forever()
*/
