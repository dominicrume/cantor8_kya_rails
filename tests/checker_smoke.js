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
  const node = () => ({textContent: '', innerHTML: '', className: '', hidden: true,
                       _on: {}, classList: {add(){}, remove(){}},
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

  const tampered = JSON.parse(JSON.stringify(REAL));
  tampered[1].amount = '9999.0';
  v = await verdictFor('tampered.json', JSON.stringify(tampered));
  check(/BROKEN at entry 2/.test(v.innerHTML) && v.className.includes('bad'),
        'a tampered chain is BROKEN, and names the entry');
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

  console.log();
  if (fails.length) {
    console.log('CHECKER SMOKE FAILED - ' + fails.length + ':');
    fails.forEach(f => console.log('  - ' + f));
    process.exit(1);
  }
  console.log('anyone can check a file by dropping it on the page, and a file that');
  console.log('is not a chain is never called tampered.');
})();
