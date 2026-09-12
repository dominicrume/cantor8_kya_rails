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
    document: {getElementById: id => nodes[id] || null, addEventListener(){},
               createElement: () => node()},
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
  // SPEC 6b. The disclosure path and the two helpers its cards render through.
  vm.runInContext(fromPage('function looksLikeDisclosure', "(!!e.body !== !!e.withheld));\n}"), ctx);
  vm.runInContext(fromPage('async function checkDisclosure', "withheld:es.length-shown};\n}"), ctx);
  vm.runInContext(fromPage('const SYMBOL =',
    "const tagClass = r => NEUTRAL[r.outcome] ? 'rule' : (GOOD[r.outcome] ? 'ok' : 'no');"), ctx);
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

  // SPEC 6b, and the reason this section exists. A regulated issuer hands over
  // its refusals without its payments. Before this, the page pulled `entries`
  // out of the document, saw `seal` and `prev` on them, verified them as
  // receipts and reported a valid disclosure as TAMPERED AT ENTRY 1 -- the
  // false accusation the rest of this file is about, made against the one file
  // format we tell people to send.
  //
  // The document is produced by the PYTHON here, not typed into this test, so
  // what is asserted is that the two halves agree. A fixture would freeze one
  // side and pass forever after the other moved.
  console.log();
  console.log('a disclosure: the refusals travel, the payments stay shut');
  const gen = require('child_process').spawnSync('python3', ['-c', `
import sys, json
sys.path.insert(0, ${JSON.stringify(path.join(ROOT, 'pkg', 'src'))})
from knowyouragenticai_receipts import Policy, guard, Refused, disclose
p = Policy(cap="250000.00", currency="USD",
           allow=["merchant-4471", "merchant-8820", "treasury-ops"],
           period_seconds=86400)
c = p.open()
@guard(p, c)
def settle(amount, payee): return "settled"
settle("120000.00", "merchant-4471")
settle("60000.00", "merchant-8820")
for a, who in [("95000.00", "merchant-4471"), ("5000.00", "merchant-9902")]:
    try: settle(a, who)
    except Refused: pass
settle("40000.00", "treasury-ops")
try: settle("-250.00", "merchant-4471")
except Refused: pass
print(json.dumps(disclose(c.receipts)))
`], {encoding: 'utf8'});
  check(gen.status === 0, 'the python produces a disclosure (' +
        (gen.status === 0 ? 'ok' : String(gen.stderr).trim().split('\n').pop()) + ')');
  const DOC = gen.status === 0 ? JSON.parse(gen.stdout) : null;

  if (DOC) {
    v = await verdictFor('settlement-refusals.json', JSON.stringify(DOC));
    check(/is a <b>disclosure<\/b>, and it holds/.test(v.innerHTML) &&
          v.className.includes('good'),
          'the page accepts what the python wrote, with nothing installed');
    check(/3<\/b> withheld/.test(v.innerHTML) && /4<\/b> shown/.test(v.innerHTML),
          '  and says how many entries it is not being shown');
    check(/every entry whose outcome is not ACCEPTED/.test(v.innerHTML),
          '  and repeats the promise the document makes about itself');

    // The point of the file. A verdict about refusals is not the refusals.
    check(/would exceed the cap/.test(v.innerHTML),
          'the refusals themselves are rendered, not just counted');
    check(/not on the allow-list/.test(v.innerHTML), '  including the payee rule');
    check(/120000\.00/.test(v.innerHTML) === false &&
          /merchant-8820<\/b>/.test(v.innerHTML) === false,
          '  while no withheld payment amount is drawn on the page');
    check((v.innerHTML.match(/class="r withheld"/g) || []).length === 3,
          '  and each withheld entry is a visible gap, by number');

    // Every attack the python checks, the page must also catch. Removing a
    // refusal is the one that matters: it is what "we had no incidents" is.
    const cut = JSON.parse(JSON.stringify(DOC));
    const at = cut.entries.findIndex(e => e.outcome === 'REFUSED');
    cut.entries.splice(at, 1);
    cut.count = cut.entries.length;
    cut.shown = cut.entries.filter(e => e.body).length;
    cut.head = cut.entries[cut.entries.length - 1].seal;
    v = await verdictFor('tidied.json', JSON.stringify(cut));
    check(/does <b>not<\/b> hold/.test(v.innerHTML) && v.className.includes('bad'),
          'a refusal removed and the counts corrected is still caught');

    // The links alone catch that deletion, so the position check was not what
    // caught it: with the position check removed, the mutation harness still
    // found this suite green, and reported BLIND. What the numbering actually
    // guards is a document whose links are intact and whose numbers lie, which
    // moves a refusal to a different point in the run.
    const renumbered = JSON.parse(JSON.stringify(DOC));
    renumbered.entries.forEach((e, i) => { e.n = i + 10; });
    v = await verdictFor('renumbered.json', JSON.stringify(renumbered));
    check(/does <b>not<\/b> hold/.test(v.innerHTML) && /numbered/.test(v.innerHTML),
          '  and so is renumbering entries while leaving the links intact');

    const softened = JSON.parse(JSON.stringify(DOC));
    softened.entries[at].body.rule = 'a routine check, nothing unusual';
    v = await verdictFor('softened.json', JSON.stringify(softened));
    check(/does <b>not<\/b> hold/.test(v.innerHTML),
          'softening the rule on a shown refusal is caught in the browser');

    const held = JSON.parse(JSON.stringify(DOC));
    delete held.entries[at].body;
    held.entries[at].withheld = true;
    held.shown = held.entries.filter(e => e.body).length;
    v = await verdictFor('held.json', JSON.stringify(held));
    check(/promises to show every refusal/.test(v.innerHTML),
          'withholding a refusal under a promise to show them all is caught');
  }

  // A plain chain wrapped as {entries: [...]} is NOT a disclosure. It has no
  // bodies, so judging it as one would tell an honest exporter their file is
  // broken -- the same false accusation, arrived at from the other direction.
  v = await verdictFor('wrapped.json', JSON.stringify({entries: REAL}));
  check(/holds/.test(v.innerHTML) && !/disclosure/.test(v.innerHTML),
        'a chain wrapped as {entries} is still read as a chain, not a broken disclosure');

  console.log();
  if (fails.length) {
    console.log('CHECKER SMOKE FAILED - ' + fails.length + ':');
    fails.forEach(f => console.log('  - ' + f));
    process.exit(1);
  }
  console.log('anyone can check a file by dropping it on the page, and a file that');
  console.log('is not a chain is never called tampered.');
})();
