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

// Projection-basis selector: swapping BOARD/FA/teams/constants in place
// (app/template.html's setBasis()) must actually change displayed numbers,
// must round-trip back to identical numbers, and the <select> must reflect
// the active basis after each switch.
const basisResult = await page.evaluate(() => {
  go('board');
  const before = Object.fromEntries(BOARD.map(r => [g(r, 'fg_id'), g(r, 'roto_points')]));
  setBasis('projection');
  const afterProj = Object.fromEntries(BOARD.map(r => [g(r, 'fg_id'), g(r, 'roto_points')]));
  const changedProj = Object.keys(before).filter(id => before[id] !== afterProj[id]).length;
  const selAfterProj = document.querySelector('#basisbar select')?.value;
  setBasis('actuals');
  const afterAct = Object.fromEntries(BOARD.map(r => [g(r, 'fg_id'), g(r, 'roto_points')]));
  const changedAct = Object.keys(before).filter(id => before[id] !== afterAct[id]).length;
  setBasis('blend');
  const back = Object.fromEntries(BOARD.map(r => [g(r, 'fg_id'), g(r, 'roto_points')]));
  const mismatchRoundtrip = Object.keys(before).filter(id => before[id] !== back[id]).length;
  const selAfterBlend = document.querySelector('#basisbar select')?.value;
  return { total: Object.keys(before).length, changedProj, changedAct, mismatchRoundtrip,
          selAfterProj, selAfterBlend };
});
const basisBad = basisResult.changedProj === 0 || basisResult.changedAct === 0
  || basisResult.mismatchRoundtrip !== 0 || basisResult.selAfterProj !== 'projection'
  || basisResult.selAfterBlend !== 'blend';
if (basisBad) console.log('  BASIS SELECTOR MISMATCH:', JSON.stringify(basisResult));

// Auction-estimator drawer panel (klab/auction_estimator.py): must render
// for a player who has an estimate, must be absent (not crash) for one who
// doesn't, and its "regression fair value" must track the active basis --
// it's computed per-basis in build_app.py for exactly the reason #42 gives
// for teams/constants: it's derived from the board's own redraft_value.
const auctionResult = await page.evaluate(() => {
  go('board');
  const withEst = BOARD.find(r => AUCTION_EST[g(r, 'fg_id')]);
  const withoutEst = BOARD.find(r => !AUCTION_EST[g(r, 'fg_id')]);
  showPlayer(g(withEst, 'fg_id'));
  const panelHtml = $('dbody').innerHTML;
  const hasPanel = panelHtml.includes('Next-auction estimate');
  const nCompRows = document.querySelectorAll('#dbody table tbody tr').length;
  const fairBlend = AUCTION_EST[g(withEst, 'fg_id')].fair;
  showPlayer(g(withoutEst, 'fg_id'));
  const noPanelForMissing = !$('dbody').innerHTML.includes('Next-auction estimate');
  setBasis('actuals');
  const fairActuals = AUCTION_EST[g(withEst, 'fg_id')].fair;
  setBasis('blend');
  return { hasPanel, nCompRows, noPanelForMissing, fairBlend, fairActuals,
          basisAware: fairBlend !== fairActuals };
});
const auctionBad = !auctionResult.hasPanel || auctionResult.nCompRows === 0
  || !auctionResult.noPanelForMissing || !auctionResult.basisAware;
if (auctionBad) console.log('  AUCTION ESTIMATOR PANEL MISMATCH:', JSON.stringify(auctionResult));

// ROS-basis toggle (out/FINDINGS.md #45/#46): switching it must move
// PROJ_PTS (proves recomputeProjections() ran), round-trip exactly, and --
// the real bug this specifically guards against -- survive a PROJECTION_BASIS
// switch afterward, since setBasis() replaces BOARD/FA wholesale with rows
// that carry the default ros_* signal and has to reapply S.rosBasis or a
// user's choice silently reverts.
const rosBasisResult = await page.evaluate(() => {
  go('standings');
  const totalPts = () => TEAMS.reduce((s, t) => s + PROJ_PTS[t].TOTAL, 0);
  const before = totalPts();
  const perTeamBefore = Object.fromEntries(TEAMS.map(t => [t, PROJ_PTS[t].TOTAL]));
  setRosBasis('prorated');
  const afterProrated = totalPts();
  const perTeamChanged = TEAMS.some(t => PROJ_PTS[t].TOTAL !== perTeamBefore[t]);
  setBasis('projection');   // an unrelated toggle -- must not silently reset rosBasis
  const survivedBasisSwitch = S.rosBasis === 'prorated';
  setRosBasis('ros');
  const back = totalPts();
  setBasis('blend'); setRosBasis('ros');   // restore defaults for later checks in this file
  const selValue = document.querySelector('.bar select[onchange^="setRosBasis"]')?.value;
  return { before, afterProrated, back, perTeamChanged, survivedBasisSwitch, selValue };
});
const rosBasisBad = !rosBasisResult.perTeamChanged
  || Math.abs(rosBasisResult.back - rosBasisResult.before) > 1e-6
  || !rosBasisResult.survivedBasisSwitch || rosBasisResult.selValue !== 'ros';
if (rosBasisBad) console.log('  ROS-BASIS TOGGLE MISMATCH:', JSON.stringify(rosBasisResult));

// Board tab "ROS value" column (out/FINDINGS.md #46): must sort correctly
// (not the raw unsorted BOARD array -- curRows() applies the filter+sort)
// and must respond to the same rest-of-2026 toggle as Standings/Trade.
const boardRosResult = await page.evaluate(() => {
  go('board');
  sortBy('ros_value');
  const sorted = curRows().slice(0, 10).map(r => rosVal(r));
  const isDescending = sorted.every((v, i) => i === 0 || sorted[i - 1] >= v);
  const before = rosVal(curRows()[0]);
  setRosBasis('prorated');
  const after = rosVal(curRows()[0]);
  setRosBasis('ros'); S.sort = 'surplus_multiyear'; S.desc = true; // restore defaults
  return { isDescending, before, after, changedOnToggle: before !== after };
});
const boardRosBad = !boardRosResult.isDescending || !boardRosResult.changedOnToggle;
if (boardRosBad) console.log('  BOARD ROS-VALUE COLUMN MISMATCH:', JSON.stringify(boardRosResult));

// Historical standings (out/FINDINGS.md #48): season picker must render a
// real table for a past year and cleanly return to the live view.
const historyResult = await page.evaluate(() => {
  go('standings');
  const years = HISTORY_YEARS.slice();
  if (!years.length) return { skipped: true };
  const yr = years[0];
  S.standSeason = String(yr);
  render();
  const rowsShown = document.querySelectorAll('#view tbody tr').length;
  const expected = (HISTORY[yr] || []).length;
  S.standSeason = 'live';
  render();
  const backToLive = document.querySelector('#view .bar select')?.value === 'live';
  return { skipped: false, rowsShown, expected, backToLive };
});
const historyBad = !historyResult.skipped
  && (historyResult.rowsShown !== historyResult.expected || !historyResult.backToLive);
if (historyBad) console.log('  HISTORICAL STANDINGS MISMATCH:', JSON.stringify(historyResult));

// 2027 keeper-only standings (out/FINDINGS.md #49): must render all 10
// teams and must vary with PROJECTION_BASIS, since the keeper set's 2027
// production is basis-dependent -- unlike history (#48), which isn't.
const keeper2027Result = await page.evaluate(() => {
  go('standings');
  S.standSeason = 'keepers2027';
  render();
  const rowsShown = document.querySelectorAll('#view tbody tr').length;
  const before = KEEPER_STANDINGS_2027.find(r => r.team === 'NPB No Stars')?.points;
  setBasis('actuals');
  const after = KEEPER_STANDINGS_2027.find(r => r.team === 'NPB No Stars')?.points;
  setBasis('blend');
  S.standSeason = 'live'; render();
  return { rowsShown, before, after, basisAware: before !== after };
});
const keeper2027Bad = keeper2027Result.rowsShown !== 10 || !keeper2027Result.basisAware;
if (keeper2027Bad) console.log('  2027 KEEPER STANDINGS MISMATCH:', JSON.stringify(keeper2027Result));

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
console.log(basisBad ? 'FAIL  projection-basis selector did not swap/round-trip correctly'
                     : `PASS  basis selector changes ${basisResult.changedProj}/${basisResult.total} `
                       + `players on switch and round-trips back exactly`);
console.log(auctionBad ? 'FAIL  auction-estimator panel missing, empty, or not basis-aware'
                       : 'PASS  auction-estimator panel renders, hides when absent, tracks basis');
console.log(rosBasisBad ? 'FAIL  ROS-basis toggle did not recompute, round-trip, or survive a basis switch'
                        : 'PASS  ROS-basis toggle recomputes standings, round-trips, and survives a basis switch');
console.log(boardRosBad ? 'FAIL  board ROS-value column does not sort correctly or ignores the toggle'
                        : 'PASS  board ROS-value column sorts correctly and tracks the rest-of-2026 toggle');
console.log(historyBad ? 'FAIL  historical standings did not render or did not return to the live view'
                       : 'PASS  historical standings render and return to the live view cleanly');
console.log(keeper2027Bad ? 'FAIL  2027 keeper standings missing teams or ignores projection basis'
                          : 'PASS  2027 keeper standings render all 10 teams and track projection basis');
await browser.close();
process.exit(bad || errs.length || suggBad.length || basisBad || auctionBad || rosBasisBad
            || boardRosBad || historyBad || keeper2027Bad ? 1 : 0);
