#!/usr/bin/env node
/* Prove the JavaScript implementation conforms to SPEC.md.
 *
 * This is the implementation that ships in verifier.html, extracted so CI can
 * run it. If this and conformance.py ever disagree, the receipt chain is
 * broken across languages and the format is worthless -- which is exactly the
 * failure this file exists to catch.
 *
 * Run: node tests/conformance.js
 */
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const V = JSON.parse(fs.readFileSync(path.join(__dirname, 'vectors.json'), 'utf8'));

// SPEC.md section 4. JSON.stringify neither sorts keys nor escapes non-ASCII,
// so neither can be relied on: both are done explicitly here.
function escapeNonAscii(s) {
  return s.replace(/[\u0080-\uffff]/g,
    c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
}
function stableStringify(o) {
  if (o === null || typeof o !== 'object') return escapeNonAscii(JSON.stringify(o));
  if (Array.isArray(o)) return '[' + o.map(stableStringify).join(',') + ']';
  return '{' + Object.keys(o).sort().map(
    k => escapeNonAscii(JSON.stringify(k)) + ':' + stableStringify(o[k])).join(',') + '}';
}
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
