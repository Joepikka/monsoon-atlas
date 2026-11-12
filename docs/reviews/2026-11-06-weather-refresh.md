# Local refresh and weather capture review, 6 November 2026

A fresh-context, read-only review inspected T236/T237 after `08fd4d0`. It used
isolated reproductions and did not modify the repository or run shared pytest.
Verdict: with fixes; two Important findings, no Critical or Minor findings.

1. **Capture I/O failures skipped usable retained preparation.** A regression
   injected a raw-ledger append PermissionError after seeding valid CAP data.
   It failed before the fix. Recoverable capture exceptions now become a failed
   collection result and preparation continues from retained evidence. Capture
   diagnostics and dated validation clocks survive. Explicit source-disable and
   invalid-input errors still stop before preparation.
2. **A bad previous weather head lost the new completed pairing.** Pointer and
   prior-receipt corruption regressions both failed before the fix. The new
   immutable receipt is now saved and hash-verified before reading the old head.
   Head advancement remains blocked on corruption, and the failed result includes
   the saved receipt path/hash for recovery.

Both findings were fixed in one RED→GREEN pass. The combined refresh/weather
suite passed 24 checks in 21.72s. Final full suite: 563 passed, 1 skipped,
1 warning in 255.16s. Lint, formatting (164 files), dependency policy, amendment
parity and working-diff whitespace pass. The skip/warning remain the S36 PDF-tool
absence and MLflow deprecation. No second review replaced the regression checks.

Final: fixed retained CAP preparation after capture I/O failure — regression
RED→GREEN, with source-disable refusal retained. Final: fixed lost completed
weather pairing after bad previous pointer/receipt — both regressions RED→GREEN.
The whole suite passed after this one fix pass.

## Rulings on declined behavior

- Weather projection, cloud upload/admission, scheduling and statewide coverage
  remain outside this child. Ruling: those gates stand; source scope remains one
  verified grid point and partial. Ignoring them could misstate coverage or
  activate unapproved resources.
- The broader S01 field/null/quality policy remains the existing adapter's
  contract. Ruling: do not bypass it by selecting temperature directly from raw
  JSON after the adapter rejects a row. A faulty policy would affect data quality;
  this child adds no new model or accuracy claims.
- Earlier CAP parsing/preparation was excluded from this review. Ruling: retain
  its previous independent review fixes and conformance tests. A regression there
  could affect warning lifecycle or replay; the full suite remains required.

No Minor findings were deferred. No account, deployment or public approval was
performed by this review.
