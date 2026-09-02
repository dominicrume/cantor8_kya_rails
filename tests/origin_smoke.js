#!/usr/bin/env node
/* The verifier's origin panel, exercised as the code that actually ships.
 *
 * This does not re-implement the comparison. It pulls the `origin` IIFE out
 * of verifier.html and runs it against a stub DOM, so what is tested is the
 * bytes a reader's browser executes. A re-implementation here would pass
 * happily while the page did something else.
 *
 * Run: node tests/origin_smoke.js
 */
const fs = require('fs'), path = require('path'), vm = require('vm');

const ROOT = path.join(__dirname, '..');
const page = fs.readFileSync(path.join(ROOT, 'step-3-verify/verifier.html'), 'utf8');
const rjs = fs.readFileSync(path.join(ROOT, 'step-3-verify/receipts.js'), 'utf8');
const RECEIPTS = JSON.parse(rjs.slice(rjs.indexOf('['), rjs.lastIndexOf(']') + 1));

const start = page.indexOf('(function origin(){');
if (start < 0) { console.log('FAIL: the origin block is not in verifier.html'); process.exit(1); }
const end = page.indexOf('})();', start) + 5;
const source = page.slice(start, end);

const fails = [];
function check(ok, what) {
  console.log('  ' + (ok ? 'PASS' : 'FAIL') + ' ' + what);
  if (!ok) fails.push(what);
}

// A stub DOM with exactly the four elements the panel touches.
function build() {
  const el = () => ({textContent: '', className: '', value: '', _fn: null,
                     addEventListener(_e, f){ this._fn = f; }});
  const nodes = {oHead: el(), oCount: el(), oPaste: el(), oVerdict: el()};
  const ctx = {RECEIPTS, document: {getElementById: id => nodes[id] || null}};
  vm.createContext(ctx);
  vm.runInContext(source, ctx);
  return nodes;
}

function verdictFor(text) {
  const n = build();
  n.oPaste.value = text;
  n._fn ? n._fn() : n.oPaste._fn();
  return n.oVerdict;
}

const HEAD = RECEIPTS[RECEIPTS.length - 1].seal;
console.log('KYA Rails - the verifier answers "is this anchored?" on the page');

const fresh = build();
check(fresh.oHead.textContent === HEAD, 'it shows this file\'s own chain head');
check(String(fresh.oCount.textContent) === String(RECEIPTS.length),
      'and the number of receipts that head covers');
check(/Not checked/.test(fresh.oVerdict.textContent),
      'before anything is pasted it says NOT CHECKED, not "unanchored"');

let v = verdictFor(HEAD);
check(/MATCHES/.test(v.textContent), 'pasting the matching seal gives MATCHES');
check(v.className.indexOf('good') !== -1, 'and turns green');

// The realistic paste: the whole terminal output, not a bare seal.
v = verdictFor('  2 anchor(s) on the ledger\n    MATCHES ' + HEAD +
               '  ' + RECEIPTS.length + ' receipts  DevNet (real Canton)\n');
check(/MATCHES/.test(v.textContent), 'pasting the whole --check output also works');

v = verdictFor('0'.repeat(64));
check(/DIFFERENT/.test(v.textContent), 'a different seal gives DIFFERENT');
check(v.className.indexOf('bad') !== -1, 'and turns red');

v = verdictFor('the network was down, sorry');
check(/No 64-character seal/.test(v.textContent),
      'text with no seal in it is not treated as a verdict either way');

// The attack the count exists for: a truncated chain's head is a REAL seal.
// Asserted on wording unique to the truncation verdict. An earlier version
// checked for the word "receipts", which the MATCHES message also contains --
// so deleting the count check entirely left this test green. Found by
// mutation, which is the only reason it is not still wrong.
v = verdictFor(HEAD + '   ' + (RECEIPTS.length + 3) + ' receipts');
check(/removed from the end/.test(v.textContent),
      'a matching seal with a different receipt count is flagged as truncation');
check(!/MATCHES/.test(v.textContent), 'and is NOT reported as a match');
check(v.className.indexOf('bad') !== -1, 'and turns red');

v = verdictFor('   ');
check(/Not checked/.test(v.textContent), 'whitespace is not a check');

console.log();
if (fails.length) {
  console.log('ORIGIN SMOKE FAILED - ' + fails.length + ':');
  fails.forEach(f => console.log('  - ' + f));
  process.exit(1);
}
console.log('the page answers the origin question, from what the reader supplies.');
