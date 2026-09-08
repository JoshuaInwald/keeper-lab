import { chromium } from 'playwright';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 390, height: 780 } });
const errs = [];
p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
p.on('pageerror', e => errs.push(String(e)));
await p.goto('file://' + process.argv[2]);
await p.waitForTimeout(400);

// name gate
await p.fill('#nm', 'Test Reviewer');
await p.click('text=Start');
await p.waitForTimeout(300);
const first = await p.textContent('.pname');
const why = await p.textContent('.why');

// a KEEP on a non-price-check player should advance without asking a price
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

// back should return to the cut player with the price retained
await p.click('text=back');
await p.waitForTimeout(250);
const retained = await p.inputValue('#pr');
const backName = await p.textContent('.pname');

// reload: answers must survive
await p.reload();
await p.waitForTimeout(500);
const afterReload = await p.textContent('.pname');

// finish and export
await p.click('text=finish');
await p.waitForTimeout(350);
const out = await p.inputValue('#out');
const parsed = JSON.parse(out);

// no model output must appear anywhere on a card
await p.evaluate(() => { S.i = 0; save(); view(); });
await p.waitForTimeout(250);
const cardText = await p.textContent('.card');
const leaks = ['surplus', 'Replace $', 'Production $', 'keep_value', 'roto'].filter(
  w => cardText.toLowerCase().includes(w.toLowerCase()));

console.log('first player      :', first.trim(), '|', why.trim());
console.log('keep advanced     :', second.trim() !== first.trim());
console.log('cut showed price  :', priceShown);
console.log('next advanced     :', third.trim() !== second.trim());
console.log('back kept price   :', retained, 'on', backName.trim());
console.log('survived reload   :', afterReload.trim() === backName.trim());
console.log('export parses     :', parsed.who, '| answered', parsed.answered,
            '| keys', Object.keys(parsed.answers).length);
console.log('sample answer     :', JSON.stringify(Object.values(parsed.answers)[0]));
console.log('model output leak :', leaks.length ? leaks : 'none');
console.log('console errors    :', errs.length ? errs.slice(0, 3) : 'none');
await b.close();
