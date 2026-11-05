# Continuation review: Monsoon Atlas

Baseline: `1747a53` on `p1/gate-core`, 5 November 2026. Read the uploaded combined
handoff, plan task specifications and model gate requirements, current amendments,
decisions, source reports, config/contracts, fetch boundary, M05 feature/model and
release code, relevant tests and CI. This is a focused continuation review, not a
line-by-line certification of every source adapter or a new M05 evaluation.

## Repository and environment

All 193 files in `handoff/monsoon-atlas-code.zip` match the checkout after CRLF/LF
normalization; no extraction or overwrite was needed. `handoff/plan.pdf` and
`docs/plan.pdf` are byte-identical. The active Codex chat is already assigned to
the local monsoon-atlas project with cwd `D:\monsoon-atlas`.

The code has an established Python 3.12 foundation: strict config/contracts,
allowlisted HTTPS ingestion, immutable raw evidence, Parquet manifests, as-of
features, source discovery records, model gates and separate owner approvals.
The product UI and hosting are still future tasks. M05 is the approved hindcast
release recorded in D43; its existing approval and release have not been edited.

## Findings and disposition

| Priority | Finding and evidence | Disposition |
|---|---|---|
| Important | Handoff section 9 put T129 before T114/T118, but plan T129 requires them and the later T046 gate. D29 also returned full T129 to P3. Treating a config file as full T129 completion would bypass the label and geography audit. | D44 splits the safe bootstrap into T226; full T129 is pending. A10 and Appendix Y record the dependency edges. T130's remaining scheduling/dependency conflict must be resolved before it starts. |
| Important, model readiness | `docs/sources/s32.md` and `s34.md` explicitly report no vertical datum. S34 archive links are not OCR-verified daily observations; S32 has a sampled long gap. T130 requires known datum and three years across eight dams. | The Kerala audit explicitly blocks a readiness claim. T114/T118 may prepare data; model fitting/promotion still requires the M07 gate. No assumption of mean sea level or daily interpolation is allowed. |
| Moderate | `.gitignore` omitted `data/models/`, although the handoff and D41 called those artifacts local-only. `git status` exposed fitted weights, metadata, split JSON and `mlflow.db` as untracked files. | Fixed narrowly in D45; existing files preserved, registry manifests remain tracked. |
| Moderate, existing model limitation | M05's recorded nominal 80% intervals cover 65.2%; the report and D43 prohibit publishing them. Probabilities exceed observed drought rates in both reported seasons. | Preserve those limits and the hindcast label. This review does not recalibrate against an already inspected test set, refit the model or claim new skill. Future calibration needs a predeclared evaluation design. |

The CI workflow installs core/dev only. Optional geo/ML and local raw-data tests
can skip there; local results therefore complement CI rather than being implied
by it. A release audit should retain both forms of evidence.

## Verification

Before changes: `python -m pytest -q` produced **358 passed, 1 skipped, 1 warning**
in 117.61 seconds. Ruff lint passed and format check reported 112 files formatted.
The warning is MLflow's upstream SQLAlchemy `noload` deprecation, not a failed test.
The first T226 check failed because `configs/states/kl.yaml` did not exist; after
adding it, all seven T226 checks passed. Final suite: **365 passed, 1 skipped,
1 warning in 110.57 seconds**. The skip is the S36 evidence text check because
`pdftotext` is not on PATH; T122 pins a PDF parser. Lint and format checks passed;
dependency policy found zero problems. Amendment Markdown/YAML parity and
`git diff --check` passed. The existing registry still resolves M05 to ridge.

Independent read-only review found no actionable issue in the continuation diff.
Its scope excluded future T129/M07 readiness, new upstream verification, M05
reevaluation and re-execution of tests or historical tool calls. Those exclusions
stand: this task certifies the bootstrap only; previous source evidence and recorded
evaluation results keep their existing limits. The executor verified archive parity,
chat association and final tests separately. No deferred minor findings remain.

No upstream downloads, account changes, public deployment or model retraining
were performed. No `.env` values or raw data were read into this report or added
to git. New commands use the repository interpreter; temp files stay on drive D.
