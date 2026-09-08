// Checks out/keeper_survey.html end to end in a phone viewport.
//
// The survey's central design rule is that it shows the reviewer NO model
// output (docs/FINDINGS.md #77): a reviewer shown a number reviews that number.
// That rule is invisible in the source and would break silently the first time
// someone adds a helpful column, so it is asserted here. The rest drives the
// real flow, because a survey that loses answers on a reload is worse than no
// survey at all.
//
//   node app/verify_survey.mjs "$PWD/out/keeper_survey.html"
import { chromium } from 'playwright';

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 390, height: 780 } });
const errs = [];
p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
p.on('pageerror', e => errs.push(String(e)));
await p.goto('file://' + process.argv[2]);
await p.waitForTimeout(400);

await p.fill('#nm', 'Test Reviewer');
await p.click('text=Start');
await p.waitForTimeout(300);
const first = await p.textContent('.pname');
const why = await p.textContent('.why');

// a KEEP on a non-price-check player advances without asking a price
await p.click('button.keep');
await p.waitForTimeout(250);
const second = await p.textContent('.pname');

// a CUT must reveal the price box
await p.click('button.cut');
await p.waitForTimeout(250);
const priceShown = await p.isVisible('#pr');
await p.fill('#pr', '17');
await p.click('text=Next');
await p.waitForTimeout(250);
const third = await p.textContent('.pname');

// back returns to the cut player with his price retained
await p.click('text=back');
await p.waitForTimeout(250);
const retained = await p.inputValue('#pr');
const backName = await p.textContent('.pname');

// answers survive a reload
await p.reload();
await p.waitForTimeout(500);
const afterReload = await p.textContent('.pname');

// finish, export, and both return paths
await p.click('text=finish');
await p.waitForTimeout(350);
const out = await p.inputValue('#out');
const parsed = JSON.parse(out);
const hasDownload = await p.isVisible('text=Download file');
const hasCopy = await p.isVisible('text=Copy text');

// no model output may appear on a card
await p.evaluate(() => { S.i = 0; save(); view(); });
await p.waitForTimeout(250);
const cardText = await p.textContent('.card');
const leaks = ['surplus', 'Replace $', 'Production $', 'keep_value', 'roto']
  .filter(w => cardText.toLowerCase().includes(w.toLowerCase()));

const ok = second.trim() !== first.trim() && priceShown && third.trim() !== second.trim()
  && retained === '17' && afterReload.trim() === backName.trim()
  && parsed.who === 'Test Reviewer' && Object.keys(parsed.answers).length === 2
  && hasDownload && hasCopy && leaks.length === 0 && errs.length === 0;

console.log('first player      :', first.trim(), '|', why.trim());
console.log('keep advanced     :', second.trim() !== first.trim());
console.log('cut showed price  :', priceShown);
console.log('back kept price   :', retained, 'on', backName.trim());
console.log('survived reload   :', afterReload.trim() === backName.trim());
console.log('export parses     :', parsed.who, '| answers', Object.keys(parsed.answers).length);
console.log('both return paths :', hasDownload && hasCopy);
console.log('model output leak :', leaks.length ? leaks : 'none');
console.log('console errors    :', errs.length ? errs.slice(0, 3) : 'none');
console.log(ok ? '\nPASS  survey flow, persistence, export and blindness all hold'
               : '\nFAIL  survey check');
await b.close();
process.exit(ok ? 0 : 1);
