#!/usr/bin/env node
/* What the two screens say when the desk stops answering.
 *
 * A page with payout authority has one failure mode worse than an error, and
 * it is silence. Both screens had it:
 *
 *   operator.html  `await (await fetch(...)).json()` threw on an unreachable
 *                  desk. The handler died mid-way, the button sat disabled
 *                  reading "Asking the ledger..." forever, and the operator
 *                  was left guessing whether the money moved.
 *
 *   customer.html  reported ANY non-ok response as "No deal found for R-1234"
 *                  -- a false statement, made to someone whose crypto is
 *                  already in flight, at the moment they are most likely to
 *                  panic and send it twice. A 404 and a 502 are not the same
 *                  news. fetch() rejecting was not caught at all: it threw
 *                  inside a setInterval, silently, every five seconds.
 *
 * Both are now handled, and neither is testable by looking at the server. So
 * this runs the PAGES' OWN code -- lifted out of the HTML, never re-typed --
 * against a fetch that fails in each of the ways a real one does.
 *
 * Run: node tests/frontend_offline.js
 */
const fs = require('fs'), path = require('path'), vm = require('vm');

const ROOT = path.join(__dirname, '..');
const OP = fs.readFileSync(path.join(ROOT, 'step-5-operator/operator.html'), 'utf8');
const CUST = fs.readFileSync(path.join(ROOT, 'step-5-operator/customer.html'), 'utf8');

const fails = [];
function check(ok, what) {
  console.log('  ' + (ok ? 'PASS' : 'FAIL') + ' ' + what);
  if (!ok) fails.push(what);
}

function fromPage(page, name, start, end) {
  const a = page.indexOf(start);
  if (a < 0) throw new Error(name + ' no longer contains: ' + start);
  const b = page.indexOf(end, a);
  if (b < 0) throw new Error(name + ': could not find the end of ' + start);
  return page.slice(a, b + end.length);
}

function node() {
  return {textContent: '', innerHTML: '', hidden: false, className: '',
          disabled: false, value: '', style: {}, dataset: {},
          classList: {add() {}, remove() {}}};
}

/* --------------------------------------------------------------------- */
/* operator.html: api() and the connection strip                          */
/* --------------------------------------------------------------------- */
function operatorCtx(fetchImpl) {
  const nodes = {link: node(), send: node()};
  const rendered = [];
  const ctx = {
    fetch: fetchImpl,
    console,
    setInterval: () => 1, clearInterval: () => {},
    $: id => nodes[id] || node(),
    esc: t => String(t).replace(/[&<>"]/g, c =>
      ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])),
    render: s => rendered.push(s),
  };
  vm.createContext(ctx);
  vm.runInContext(
    fromPage(OP, 'operator.html', 'let retrying = null;', '  render(s);\n}'), ctx);
  return {ctx, nodes, rendered};
}

async function operatorChecks() {
  console.log('operator.html - the desk stops answering');

  // 1. The network is gone. This is the case that used to throw.
  let h = operatorCtx(() => Promise.reject(new TypeError('Failed to fetch')));
  let out = await h.ctx.api('/api/state');
  check(out && out.error, 'an unreachable desk returns an error, it does not throw');
  check(!h.nodes.link.hidden, 'and the connection strip is showing');
  check(/not answering/i.test(h.nodes.link.innerHTML),
        'saying the desk is not answering');
  check(/[Dd]o not assume a payment failed/.test(h.nodes.link.innerHTML),
        'and warning against assuming the payment failed');

  // 2. refresh() must not render a half-state on top of a good one.
  h = operatorCtx(() => Promise.reject(new TypeError('Failed to fetch')));
  await h.ctx.refresh();
  check(h.rendered.length === 0,
        'refresh() renders nothing rather than blanking the last known state');

  // 3. Something in front of the desk returns an HTML error page.
  h = operatorCtx(() => Promise.resolve(
    {status: 502, text: () => Promise.resolve('<html>502 Bad Gateway</html>')}));
  out = await h.ctx.api('/api/state');
  check(out.error && /cannot read/.test(out.error),
        'an HTML error page is reported as unreadable, not as a parse crash');
  check(/502/.test(out.error), 'and the status code is carried through');

  // 4. A refusal from the desk itself is NOT a connection problem.
  h = operatorCtx(() => Promise.resolve(
    {status: 400, text: () => Promise.resolve('{"error":"amount is required"}')}));
  out = await h.ctx.api('/api/request', {});
  check(out.error === 'amount is required', "the desk's own 400 comes through verbatim");
  check(h.nodes.link.hidden,
        'and it does NOT raise the connection strip -- the desk answered fine');

  // 5. Recovery.
  h = operatorCtx(() => Promise.resolve(
    {status: 200, text: () => Promise.resolve('{"open":true,"receipts":[]}')}));
  h.nodes.link.hidden = false;
  await h.ctx.refresh();
  check(h.nodes.link.hidden, 'the strip clears the moment the desk answers again');
  check(h.rendered.length === 1, 'and the screen is rendered from the fresh state');
}

/* --------------------------------------------------------------------- */
/* customer.html: 404 is not the same news as 502                         */
/* --------------------------------------------------------------------- */
function customerCtx(fetchImpl, reference) {
  const nodes = {body: node(), stale: node(), qr: node()};
  const ctx = {
    fetch: fetchImpl, console,
    ref: reference === undefined ? 'R-1234' : reference,
    $: id => nodes[id] || node(),
    esc: t => String(t).replace(/[&<>"]/g, c =>
      ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])),
    render: () => {}, drawQR: () => {},
    encodeURIComponent,
  };
  vm.createContext(ctx);
  vm.runInContext(
    fromPage(CUST, 'customer.html', 'let shown = false;',
             "if (d.state === 'QUOTED') drawQR(d.depositAddress);\n}"), ctx);
  return {ctx, nodes};
}

const reply = (status, body) => () =>
  Promise.resolve({status, ok: status >= 200 && status < 300,
                   json: () => Promise.resolve(JSON.parse(body)),
                   text: () => Promise.resolve(body)});

async function customerChecks() {
  console.log('\ncustomer.html - someone whose crypto is already in flight');

  // THE ONE THAT WAS WRONG. A desk that is down is not a deal that is gone.
  let h = customerCtx(() => Promise.reject(new TypeError('Failed to fetch')));
  await h.ctx.load();
  const offline = h.nodes.body.innerHTML;
  check(!/No deal found/.test(offline),
        'an unreachable desk is NEVER reported as "no deal found"');
  check(/[Cc]annot reach the desk/.test(offline), 'it says the desk cannot be reached');
  check(/[Dd]o not send again/.test(offline),
        'and tells them not to send a second time -- the actual risk');

  h = customerCtx(reply(502, 'nope'));
  await h.ctx.load();
  check(!/No deal found/.test(h.nodes.body.innerHTML),
        'nor is a 502 reported as "no deal found"');
  check(/502/.test(h.nodes.body.innerHTML), 'the status is named so it can be reported');

  // A real 404 still says so. The fix must not blur the true case.
  h = customerCtx(reply(404, ''));
  await h.ctx.load();
  check(/No deal found for R-1234/.test(h.nodes.body.innerHTML),
        'a genuine 404 still says the deal was not found');

  // Once something true is on screen, a blip must not wipe it.
  h = customerCtx(reply(200, '{"state":"QUOTED","depositAddress":"TAddr"}'));
  await h.ctx.load();
  check(h.nodes.stale.hidden, 'a good load leaves no warning strip');
  h.ctx.fetch = () => Promise.reject(new TypeError('Failed to fetch'));
  const before = h.nodes.body.innerHTML;
  await h.ctx.load();
  check(h.nodes.body.innerHTML === before,
        'a later blip does not wipe the deal already on screen');
  check(!h.nodes.stale.hidden && /Do not send again/.test(h.nodes.stale.textContent),
        'it warns above the deal instead, so the customer keeps what they had');

  h = customerCtx(() => Promise.resolve(
    {status: 200, ok: true, json: () => Promise.reject(new SyntaxError('bad')),
     text: () => Promise.resolve('not json')}));
  await h.ctx.load();
  check(/cannot read/.test(h.nodes.body.innerHTML),
        'an unreadable reply says so rather than throwing into a setInterval');
}

(async () => {
  await operatorChecks();
  await customerChecks();
  console.log();
  if (fails.length) {
    console.log('FRONTEND OFFLINE FAILED - ' + fails.length + ':');
    fails.forEach(f => console.log('  - ' + f));
    process.exit(1);
  }
  console.log('neither screen goes silent, and neither tells the reader');
  console.log('something that is not true about their money.');
})();
