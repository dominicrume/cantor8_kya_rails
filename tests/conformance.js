#!/usr/bin/env node
/* Prove the JavaScript that SHIPS conforms to SPEC.md.
 *
 * It now reads stableStringify out of verifier.html rather than carrying a
 * copy. That distinction is not pedantry: this file used to have its own copy
 * WITH the non-ASCII escaping, while the page shipped a version WITHOUT it. So
 * "CONFORMANT: 16/16 cases" was true of this file and false of the page, for
 * as long as the two differed -- and canonical-escapes-non-ascii, the vector
 * written specifically to catch that class of bug, could never see it.
 *
 * A test that re-implements its subject tests nothing. checker_smoke.js and
 * origin_smoke.js already read the page; this one did not, and the one that
 * did not is the one that was wrong.
 *
 * Run: node tests/conformance.js
 */
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const V = JSON.parse(fs.readFileSync(path.join(__dirname, 'vectors.json'), 'utf8'));

// Lifted out of the page itself. If verifier.html stops defining these, this
// throws rather than silently falling back to a local copy -- a fallback would
// reintroduce exactly the blindness this replaced.
const PAGE = fs.readFileSync(
  path.join(__dirname, '..', 'step-3-verify', 'verifier.html'), 'utf8');

function fromPage(start, end) {
  const a = PAGE.indexOf(start);
  if (a < 0) throw new Error('verifier.html no longer contains: ' + start);
  const b = PAGE.indexOf(end, a);
  if (b < 0) throw new Error('could not find the end of: ' + start);
  return PAGE.slice(a, b + end.length);
}

const { escapeNonAscii, stableStringify } = new Function(
  fromPage('function escapeNonAscii', "+'}'; }")
  + '; return { escapeNonAscii, stableStringify };')();
const sha256 = s => crypto.createHash('sha256').update(s, 'utf8').digest('hex');
const seal = (body, prev) => sha256(stableStringify(body) + prev);

function nonAsciiField(body) {          // SPEC.md section 5
  for (const k of Object.keys(body)) {
    for (const s of [k, body[k]]) {
      if (typeof s === 'string' && /[\u0080-\uffff]/.test(s)) return k;
    }
  }
  return null;
}
function verify(receipts) {
  let prev = 'GENESIS';
  for (const r of receipts) {
    if (r.prev !== prev) return r.n;
    const body = {}; for (const k in r) if (k !== 'seal') body[k] = r[k];
    if (seal(body, prev) !== r.seal) return r.n;
    prev = r.seal;
  }
  return 0;
}

const fails = [];
function check(ok, c, detail) {
  if (!ok) fails.push(c.name + ': ' + detail);
  console.log('  ' + (ok ? 'PASS' : 'FAIL') + ' ' + c.name.padEnd(34) + ' ' + c.kind);
}

console.log('KYA Receipt Chain ' + V.spec_version + ' - JavaScript conformance');
for (const c of V.cases) {
  if (c.kind === 'canonical') {
    // Canonical form only. The body carries characters above 0x7E, which
    // SPEC.md section 5 rejects before sealing -- the case exists so that
    // implementations agree on the escaping anyway, per section 4. This is
    // the case JSON.stringify fails by default.
    const gotC = stableStringify(c.body);
    check(gotC === c.canonical, c, 'canonical mismatch: want ' + c.canonical + ' got ' + gotC);
  } else if (c.kind === 'seal') {
    const gotC = stableStringify(c.body);
    if (gotC !== c.canonical) {
      check(false, c, 'canonical mismatch: want ' + c.canonical + ' got ' + gotC);
    } else {
      const gotS = seal(c.body, c.prev);
      check(gotS === c.seal, c, 'seal want ' + c.seal + ' got ' + gotS);
    }
  } else if (c.kind === 'chain') {
    const got = verify(c.receipts);
    const want = c.verdict === 'PASS' ? 0 : c.fail_at;
    check(got === want, c, 'expected fail_at=' + want + ', got ' + got);
  } else if (c.kind === 'reject') {
    const field = nonAsciiField(c.body);
    check(field === c.offending_field, c,
          'expected rejection naming ' + c.offending_field + ', got ' + field);
  } else {
    check(false, c, 'unknown case kind ' + c.kind);
  }
}
console.log();
if (fails.length) {
  console.log('NOT CONFORMANT - ' + fails.length + ' failure(s):');
  fails.forEach(f => console.log('  - ' + f));
  process.exit(1);
}
console.log('CONFORMANT: ' + V.cases.length + '/' + V.cases.length + ' cases');
