# JOB: step-3-verify
IN:   receipts.js written by the agent
DO:   one self-contained page: WhatsApp-style chat replay + receipt chain panel
      + VERIFY button (recomputes every seal) + TAMPER button (edits one receipt,
      chain cascades red)
OUT:  verifier.html, double-click to open, works with no network at all
DONE: green chain on load, red cascade on tamper, judge can read every receipt in plain words.
NOT:  no ledger calls from this page. It checks records; it does not create them.
