#!/usr/bin/env node
/* The drop-a-file checker, exercised as the code that actually ships.
 *
 * This pulls the `checker` IIFE out of verifier.html AND the verification it
 * depends on -- stableStringify, sha256, badFrom, esc -- so what runs is the
 * page's own code.
 *
 * It did not always. The first version injected its own stableStringify,
 * sha256 and badFrom into the VM, so the checker resolved them from the test
 * rather than from the page: with the page's badFrom stubbed to `return 0`,
 * every one of these checks still passed, including "a tampered chain is
 * BROKEN". A test that supplies the thing it is testing tests nothing, and
 * this file said in its own header that it did the opposite.
 *
 * The case that matters most is the one that used to be wrong: a file that is
 * NOT a receipt chain must never be reported as a BROKEN one. "Broken" says
 * somebody edited this. Saying that about an ordinary JSON export is a false
 * accusation, and it is exactly the kind of claim this project exists to be
 * careful about.
 *
 * Run: node tests/checker_smoke.js
 */
const fs = require('fs'), path = require('path'), vm = require('vm'), crypto = require('crypto');

const ROOT = path.join(__dirname, '..');
const page = fs.readFileSync(path.join(ROOT, 'step-3-verify/verifier.html'), 'utf8');
const rjs = fs.readFileSync(path.join(ROOT, 'step-3-verify/receipts.js'), 'utf8');
const REAL = JSON.parse(rjs.slice(rjs.indexOf('['), rjs.lastIndexOf(']') + 1));

function fromPage(start, end) {
  const a = page.indexOf(start);
  if (a < 0) throw new Error('verifier.html no longer contains: ' + start);
  const b = page.indexOf(end, a);
  if (b < 0) throw new Error('could not find the end of: ' + start);
  return page.slice(a, b + end.length);
}

const source = fromPage('(function checker(){', '\n})();');

const fails = [];
function check(ok, what) {
  console.log('  ' + (ok ? 'PASS' : 'FAIL') + ' ' + what);
  if (!ok) fails.push(what);
}

// A DOM just big enough for the shipped block to run against.
function harness() {
  // querySelectorAll is a real method the page calls on the verdict box to
  // wire up the chain links. Returning [] keeps the harness honest about what
  // it does NOT simulate -- clicking a link needs a real DOM -- while letting
  // the page's own code run to completion, which is the point of lifting it
  // out of the file rather than re-typing it.
  const node = () => ({textContent: '', innerHTML: '', className: '', hidden: true,
                       _on: {}, classList: {add(){}, remove(){}},
                       querySelectorAll(){ return []; },
                       addEventListener(e, f){ this._on[e] = f; }});
  const nodes = {cDrop: node(), cFile: node(), cVerdict: node(), cPrompt: node()};
  const ctx = {
    document: {getElementById: id => nodes[id] || null, addEventListener(){}},
    setTimeout, console,
    // Node has no WebCrypto under this name in every version; the page uses
    // crypto.subtle.digest. This is the ONE thing supplied, because it is the
    // platform, not the page's logic.
    crypto: {subtle: {digest: async (_alg, buf) =>
      crypto.createHash('sha256').update(Buffer.from(buf)).digest().buffer}},
    TextEncoder,
  };
  vm.createContext(ctx);
  // The page's own canonicalisation, hashing, chain check and escaping. If
  // verifier.html stops defining any of them this throws, rather than quietly
  // falling back to a copy that would hide the difference.
  vm.runInContext(fromPage('function escapeNonAscii', "+'}'; }"), ctx);
  vm.runInContext(fromPage('async function sha256', "join(''); }"), ctx);
  vm.runInContext(fromPage('async function badFrom', 'return 0; }'), ctx);
  vm.runInContext(fromPage('const esc =', "[c]));"), ctx);
  ctx.FileReader = class {
    readAsText(f) { this.result = f._text; setTimeout(() => this.onload && this.onload(), 0); }
  };
  vm.createContext(ctx);
  vm.runInContext(source, ctx);
  return nodes;
}

function verdictFor(name, text) {
  return new Promise(resolve => {
    const n = harness();
    n.cFile._on.change({target: {files: [{name, _text: text}]}});
    setTimeout(() => resolve(n.cVerdict), 30);
  });
}

(async () => {
  console.log('KYA Rails - drop a receipts file on the page');

  let v = await verdictFor('receipts.json', JSON.stringify(REAL));
  check(/holds/.test(v.innerHTML) && v.className.includes('good'),
        'a real chain is accepted');
  check(/does not prove where the file came from/.test(v.innerHTML),
        'and says what a passing check does NOT prove');
  check((v.innerHTML.match(/class="lnk"/g) || []).length === REAL.length,
        'an intact chain draws every link unbroken');
  check(!/lnk broke|lnk after/.test(v.innerHTML),
        'with nothing marked as broken');

  const tampered = JSON.parse(JSON.stringify(REAL));
  tampered[1].amount = '9999.0';
  v = await verdictFor('tampered.json', JSON.stringify(tampered));
  check(/BROKEN at entry 2/.test(v.innerHTML) && v.className.includes('bad'),
        'a tampered chain is BROKEN, and names the entry');

  // The chain is drawn as one tile per entry, so the break is a thing you see
  // rather than a sentence you parse. The second tile must carry the break.
  check((v.innerHTML.match(/class="lnk/g) || []).length === REAL.length,
        'and draws one link per entry (' + REAL.length + ')');
  check(/class="lnk broke" data-n="2"/.test(v.innerHTML),
        'with entry 2 marked as the break itself');
  check(/class="lnk after" data-n="3"/.test(v.innerHTML),
        'and everything after it marked unreliable, not merely fine');
  check(/ask whoever gave you this file/.test(v.innerHTML),
        'and tells the reader what to do about it');

  // Shapes people actually have. These are chains, just wrapped.
  for (const [label, body] of [
    ['wrapped in an object', JSON.stringify({receipts: REAL})],
    ['an export with metadata', JSON.stringify({exported_at: '2026-01-01', data: REAL})],
  ]) {
    v = await verdictFor('x.json', body);
    check(/holds/.test(v.innerHTML) && v.className.includes('good'),
          'a chain ' + label + ' is found and verified, not called broken');
  }

  // THE ONE THAT WAS WRONG. Not a chain is not the same as tampered.
  for (const [label, body] of [
    ['a config file', JSON.stringify({setting: true, name: 'x'})],
    ['a list of something else', JSON.stringify([{id: 1}, {id: 2}])],
  ]) {
    v = await verdictFor('x.json', body);
    check(/not a receipt chain/.test(v.innerHTML) && v.className.includes('unknown'),
          label + ' is reported as NOT A CHAIN, never as broken');
    check(!/BROKEN/.test(v.innerHTML), '  and the word BROKEN never appears for ' + label);
  }

  v = await verdictFor('notes.txt', 'hello, this is not json at all');
  check(/not JSON this page can read/.test(v.innerHTML), 'a non-JSON file says so plainly');

  v = await verdictFor('receipts.js', rjs);
  check(/holds/.test(v.innerHTML), 'the reference receipts.js format is read as-is');

  // SPEC 6a. A verifier reports the level it ESTABLISHED. It cannot establish
  // origin from the file it was handed, so the answer is always self-attested
  // -- and when the file's own fields insist otherwise, the page has to say so,
  // because a reader who sees "Canton DevNet" inside a receipt and "holds" from
  // us will put those together into something neither of us said.
  check(/self-attested/.test(v.innerHTML),
        'the verdict names the assurance level, not just that it holds');

  // The chain must genuinely HOLD, or this asserts nothing: a broken chain
  // never reaches the verdict the warning lives on, and the check would pass
  // on the wrong branch. So reseal it with the page's own seal function -- a
  // perfectly valid chain whose every entry claims a ledger that never saw it.
  const liar = JSON.parse(JSON.stringify(REAL));
  let prevSeal = 'GENESIS';
  for (const r of liar) {
    r.ledger = 'Canton DevNet (real Canton) - an independent party decided this';
    r.prev = prevSeal;
    const body = {}; Object.keys(r).filter(k => k !== 'seal').sort()
      .forEach(k => { body[k] = r[k]; });
    // Sealed here with Node's crypto rather than through the page: this is
    // building a FIXTURE, not testing the seal. What is under test is what the
    // page concludes about it, and the page recomputes every seal itself.
    // Every field is ASCII, so plain stringify over sorted keys is byte-exact.
    r.seal = crypto.createHash('sha256')
      .update(JSON.stringify(body) + prevSeal).digest('hex');
    prevSeal = r.seal;
  }
  v = await verdictFor('claims-a-ledger.json', JSON.stringify(liar));
  check(/holds/.test(v.innerHTML), 'the lying chain genuinely holds -- its seals are correct');
  check(/Read this before you rely on it/.test(v.innerHTML),
        '  and is still flagged, because nothing substantiated the claim');

  v = await verdictFor('receipts.js', rjs);
  check(!/Read this before you rely on it/.test(v.innerHTML),
        'an honest self-attested chain gets no such warning');

  // A findings chain is the same format carrying something that is not money:
  // `amount` is a line number, `currency` is N/A, and COVERED is the good
  // outcome. The page has to read all three correctly, because an audit record
  // that renders "139 N/A" tells the reader they are looking at a payment, and
  // one that paints COVERED red says every good result is a failure.
  const findings = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'docs/findings/canton-contracts-access-control-v1.json'), 'utf8'));
  v = await verdictFor('findings.json', JSON.stringify(findings));
  check(/holds/.test(v.innerHTML) && v.className.includes('good'),
        'an audit findings chain is read by the same page, with nothing installed');

  // The two render helpers, lifted from the page rather than retyped.
  const rctx = {SYMBOL: {}, console};
  vm.createContext(rctx);
  vm.runInContext(fromPage('const SYMBOL =', "const tagClass = r => NEUTRAL[r.outcome] ? 'rule' : (GOOD[r.outcome] ? 'ok' : 'no');"), rctx);
  const render = r => vm.runInContext('subject(' + JSON.stringify(r) + ')', rctx);
  const colour = r => vm.runInContext('tagClass(' + JSON.stringify(r) + ')', rctx);

  const finding = findings.find(r => r.outcome === 'COVERED');
  const uncovered = findings.find(r => r.outcome === 'UNCOVERED');
  check(render(finding) === finding.payee + ':' + finding.amount,
        'a fence renders as file:line, not as an amount of money');
  check(!/N\/A/.test(render(finding)), '  and "N/A" never appears as a currency');
  check(colour(finding) === 'ok', 'COVERED is green: the good outcome reads as good');
  check(colour(uncovered) === 'no', 'UNCOVERED is red');

  // The change must not have moved money.
  const paid = REAL.find(r => r.outcome === 'ACCEPTED');
  const refused = REAL.find(r => r.outcome === 'REFUSED');
  check(/\u20b5/.test(render(paid)) && render(paid).includes(paid.payee),
        'a payment still renders with its symbol and its payee');
  check(colour(paid) === 'ok' && colour(refused) === 'no',
        'ACCEPTED is still green and REFUSED still red');

  // A chain may open by stating the rules it ran under. That entry is neither
  // a pass nor a failure, and painting it red says something was refused when
  // nothing was -- the same mistake COVERED used to make.
  const pol = {outcome: 'POLICY', currency: 'USD', amount: '100.00', payee: 'acme'};
  check(colour(pol) === 'rule', 'a POLICY entry is neither green nor red');
  check(/^limit /.test(render(pol)),
        'a policy renders as a LIMIT, not as money that moved to the payee');

  console.log();
  if (fails.length) {
    console.log('CHECKER SMOKE FAILED - ' + fails.length + ':');
    fails.forEach(f => console.log('  - ' + f));
    process.exit(1);
  }
  console.log('anyone can check a file by dropping it on the page, and a file that');
  console.log('is not a chain is never called tampered.');
})();
