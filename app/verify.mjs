/**
 * Diff the browser's arithmetic against pandas.
 *
 * The app re-implements one thing in JavaScript: the rest-of-season standings
 * calculation, so a trade can be re-scored without a server. Re-implementations
 * drift. This loads the built HTML in headless Chromium, runs the same trade
 * the Python side ran, and compares all 25 quantities against
 * `out/app_reference.json`. It also walks every tab and fails on any console
 * error, which is how the PA_x/PA_y column collision was caught.
 *
 *     PYTHONPATH=. python3 scripts/build_app.py
 *     node app/verify.mjs
 *
 * Needs `npm i playwright` and a Chromium; set CHROME to override the path.
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const HTML = path.join(ROOT, 'out', 'keeper_lab.html');
const REF = JSON.parse(fs.readFileSync(path.join(ROOT, 'out', 'app_reference.json'), 'utf8'));

// Payload floats are rounded to 4dp, so a sum of a handful of players can
// legitimately differ in the 4th decimal. Standings points must match exactly.
const TOL_MONEY = 1e-3, TOL_POINTS = 1e-9;

const opts = process.env.CHROME ? { executablePath: process.env.CHROME } : {};
const browser = await chromium.launch(opts);
const page = await browser.newPage();
const errs = [];
page.on('pageerror', e => errs.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });

await page.goto('file://' + HTML);
await page.waitForTimeout(300);

const got = await page.evaluate(ref => {
  const id = n => {
    const hit = BOARD.filter(r => g(r, 'name') === n);
    if (hit.length !== 1) throw new Error(`name "${n}" resolved to ${hit.length} players`);
    return g(hit[0], 'fg_id');
  };
  const aOut = ref.a_sends.map(id), bOut = ref.b_sends.map(id);
  const swap = {};
  aOut.forEach(i => swap[i] = ref.team_b);
  bOut.forEach(i => swap[i] = ref.team_a);
  const after = rotoPoints(catTotals(rosterAgg(swap)));
  const sum = (ids, c) => ids.reduce((s, i) => s + (g(byId[i], c) || 0), 0);
  const surp = (o, i) => (sum(i, 'redraft_value') - sum(i, 'keeper_cost'))
                       - (sum(o, 'redraft_value') - sum(o, 'keeper_cost'));
  const out = { points_before: {}, points_after: {} };
  for (const t of TEAMS) {
    out.points_before[t] = PROJ_PTS[t].TOTAL;
    out.points_after[t] = after[t].TOTAL;
  }
  out.a_dS = surp(aOut, bOut);
  out.b_dS = surp(bOut, aOut);
  out.a_dMY = sum(bOut, 'surplus_multiyear') - sum(aOut, 'surplus_multiyear');
  out.a_dP = after[ref.team_a].TOTAL - PROJ_PTS[ref.team_a].TOTAL;
  out.b_dP = after[ref.team_b].TOTAL - PROJ_PTS[ref.team_b].TOTAL;
  return out;
}, REF);

// Every tab, the drawer, the filters, a re-sort -- anything that throws shows
// up in `errs`.
for (const t of ['board', 'teams', 'trade', 'standings', 'fa', 'model']) {
  await page.evaluate(t => go(t), t);
  await page.waitForTimeout(50);
}
await page.evaluate(() => { go('board'); showPlayer(g(BOARD[0], 'fg_id')); closeDrawer(); });
await page.evaluate(() => { S.infl = true; S.only = 'keep'; S.q = 'a'; refilter(); });
await page.evaluate(() => { S.infl = false; S.only = ''; S.q = ''; sortBy('redraft_value'); });
await page.evaluate(() => { go('fa'); S.role = 'PIT'; refilter(); S.role = ''; });
await page.waitForTimeout(100);

// Trade-suggestion cards: this caught a real bug once (embedding a player
// name with an apostrophe -- "Spehr's Army", "O'Brien" -- as a raw JS
// string literal inside a double-quoted onclick attribute breaks HTML
// parsing; fixed by moving to data-* attributes). The generic tab walk
// above only renders the panel for whichever pair T.a/T.b default to, and
// never clicks anything inside it, so it would not have caught this.
const suggResult = await page.evaluate(() => {
  const pairs = [["NPB No Stars", "Spehr's Army"], ["McBlocks", "Spehr's Army"],
                 ["Pookie 2.0", "Producers"], ["All-Stars", "Lisbon Long Balls"]];
  const out = [];
  go('trade');
  for (const [a, b] of pairs) {
    T.a = a; T.b = b; T.aOut = []; T.bOut = [];
    render();
    const buttons = document.querySelectorAll('.sugg-card button.act');
    let loadedOk = 0;
    buttons.forEach(btn => {
      btn.click();
      if (T.aOut.length === 1 && T.bOut.length === 1) loadedOk++;
      T.aOut = []; T.bOut = [];
    });
    out.push({ pair: `${a}/${b}`, buttons: buttons.length, loadedOk });
  }
  return out;
});
const suggBad = suggResult.filter(r => r.loadedOk !== r.buttons);
if (suggBad.length) console.log('  SUGGESTION PANEL MISMATCH:', JSON.stringify(suggBad));

let bad = 0;
const cmp = (label, a, e, tol) => {
  if (!(Math.abs(a - e) <= tol)) { console.log(`  MISMATCH ${label}: js ${a} vs py ${e}`); bad++; }
};
for (const k of Object.keys(REF.points_before)) {
  cmp('before.' + k, got.points_before[k], REF.points_before[k], TOL_POINTS);
  cmp('after.' + k, got.points_after[k], REF.points_after[k], TOL_POINTS);
}
for (const k of ['a_dP', 'b_dP']) cmp(k, got[k], REF[k], TOL_POINTS);
for (const k of ['a_dS', 'b_dS', 'a_dMY']) cmp(k, got[k], REF[k], TOL_MONEY);

const n = Object.keys(REF.points_before).length * 2 + 5;
console.log(bad ? `FAIL  ${bad}/${n} quantities disagree`
                : `PASS  JS matches pandas on all ${n} quantities`);
console.log(errs.length ? 'JS ERRORS:\n  ' + errs.join('\n  ')
                        : 'PASS  no console errors across six tabs, drawer, filters, re-sort');
console.log(suggBad.length ? `FAIL  trade-suggestion load-into-picker mismatched on ${suggBad.length} pair(s)`
                            : 'PASS  trade-suggestion panel renders and loads correctly on every tested pair');
await browser.close();
process.exit(bad || errs.length || suggBad.length ? 1 : 0);
