// SPEC 6d. A disclosure may pin its independence claim to a topology
// snapshot. This proves the shipped verifier accepts a well formed one,
// refuses every malformed shape by name, and treats absence as a smaller
// claim rather than a worse document.
//
// WHY THE FIELD EXISTS. On forum.canton.network topic 9323, Georgi Radev of
// LimeChain established on 2026-11-04 that the ledger names parties and not
// their operators: distinct node identifiers are not distinct operators, and
// participation in a particular transaction is not recoverable at all. The
// claim was split in two in public on 2026-11-09 as a result.
//
// tonozzibeverley953 proposed the remedy on 2026-11-13: tie the assertion to
// a specific topology export by recording its hash, time and validity
// interval. It does not prove who controlled the nodes. It stops the claim
// floating free of the configuration it describes.
//
// The reply on that thread said "Adding it as a field in the audit package,
// credited to you." This file is that promise kept rather than restated.
//
//     node tests/topology_smoke.js
//
// It lifts checkDisclosure out of the shipped page, the same way
// checker_smoke.js does, so it tests verifier.html and not a copy of it.

const fs = require('fs'), path = require('path'), vm = require('vm'),
      crypto = require('crypto');

const ROOT = path.dirname(__dirname);
const page = fs.readFileSync(
  path.join(ROOT, 'step-3-verify', 'verifier.html'), 'utf8');

function fromPage(start, end) {
  const a = page.indexOf(start);
  if (a < 0) throw new Error('verifier.html no longer contains: ' + start);
  const b = page.indexOf(end, a);
  if (b < 0) throw new Error('no end marker after: ' + start);
  return page.slice(a, b + end.length);
}

const ctx = {
  console, setTimeout, TextEncoder,
  crypto: {subtle: {digest: async (_alg, buf) =>
    crypto.createHash('sha256').update(Buffer.from(buf)).digest().buffer}},
};
vm.createContext(ctx);
vm.runInContext(fromPage('function escapeNonAscii', "+'}'; }"), ctx);
vm.runInContext(fromPage('async function sha256', "join(''); }"), ctx);
vm.runInContext(fromPage('function looksLikeDisclosure',
  "(!!e.body !== !!e.withheld));\n}"), ctx);
vm.runInContext(fromPage('async function checkDisclosure',
  "withheld:es.length-shown};\n}"), ctx);

let failures = 0;
function check(ok, what) {
  console.log('  ' + (ok ? 'PASS' : 'FAIL') + ' ' + what);
  if (!ok) failures++;
}

// A disclosure whose entries are all withheld, so nothing below depends on
// seal arithmetic and every result is about the topology field.
const MINIMAL = {
  disclosing: 'a chosen subset',
  entries: [{n: 1, outcome: 'REFUSED', prev: 'GENESIS',
             seal: 'a'.repeat(64), withheld: true}]
};
const GOOD = {
  digest: 'sha256:' + 'a'.repeat(64),
  exportedAt: '2026-11-13T22:00:00Z',
  validFrom: '2026-11-01T00:00:00Z',
  validTo: 'OPEN'
};
const base = () => JSON.parse(JSON.stringify(MINIMAL));
const run = d => ctx.checkDisclosure(d);
const saysTopology = r => String(r && r.why || '').includes('topology');

(async () => {
  console.log('SPEC 6d: topology pins an independence claim to a snapshot');

  // CONTROL. A document with no topology must not be failed BY topology.
  // Without this, every refusal below could be the harness rejecting the
  // minimal document for an unrelated reason.
  const none = await run(base());
  check(!saysTopology(none),
        'CONTROL: a disclosure with no topology raises no topology complaint');

  const good = base();
  good.topology = Object.assign({}, GOOD);
  check(!saysTopology(await run(good)),
        'a well formed topology raises no topology complaint');

  const malformed = [
    ['not an object', 'a string where an object belongs'],
    [[], 'an array where an object belongs'],
    [null, 'null where an object belongs'],
    [{}, 'an empty object, all four fields missing'],
    [Object.assign({}, GOOD, {digest: 'a'.repeat(64)}), 'digest with no sha256: prefix'],
    [Object.assign({}, GOOD, {digest: 'sha256:' + 'A'.repeat(64)}), 'digest in uppercase hex'],
    [Object.assign({}, GOOD, {digest: 'sha256:' + 'a'.repeat(63)}), 'digest one character short'],
    [Object.assign({}, GOOD, {exportedAt: '2026-11-13 22:00:00'}), 'exportedAt with no T and no Z'],
    [Object.assign({}, GOOD, {validFrom: 'yesterday'}), 'validFrom in prose'],
    [Object.assign({}, GOOD, {validTo: 'open'}), 'validTo lowercase, OPEN is the only word'],
  ];
  for (const [t, what] of malformed) {
    const d = base();
    d.topology = t;
    const r = await run(d);
    check(r.ok === false && saysTopology(r), 'refused: ' + what);
  }

  for (const k of ['digest', 'exportedAt', 'validFrom', 'validTo']) {
    const d = base();
    d.topology = Object.assign({}, GOOD);
    delete d.topology[k];
    const r = await run(d);
    check(r.ok === false && String(r.why).includes(k),
          'refused and names the missing field: ' + k);
  }

  console.log('');
  if (failures) {
    console.log('FAILED: ' + failures);
    process.exit(1);
  }
  console.log('topology is optional, shape-checked, and claims nothing more.');
})();
