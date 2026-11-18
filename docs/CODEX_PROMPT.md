You are continuing Monsoon Atlas, a Rs 0 open-data and ML portfolio project, in D:\monsoon-atlas
(Windows 10, Git Bash or PowerShell, Python 3.12 in .venv, everything on drive D). Work on the
**Karnataka part only**; do not start Kerala or Delhi work.

First read, in order: AGENTS.md, docs/CODEX_HANDOFF.md (current state, next tasks, pitfalls),
docs/plans/karnataka-ml-showcase.md, the top 30 entries of docs/decisions.md, and the T268-T289
entries in docs/amendments.yaml.

Then:
1. Run `git status` and `git log --oneline origin/p1/gate-core..HEAD`. Finish the in-progress T284
   (M21 locked test) exactly as the handoff says: if models/gates/m21.json has test_opened true,
   never open the test again; if false, write the interval method into the gate first, then open
   the test once. Record decisions D212 (text is in the handoff) and D219.
2. Run the full test suite, fix every failure caused by the recent work (keep S23 blocked until
   T270), regenerate docs/releases/final-manifest.json last, commit, push p1/gate-core and let
   PR 15 auto-merge after CI passes.
3. Continue the Karnataka tasks in the handoff order: T270 -> T271 -> T272 -> T273-T275 (M06) ->
   T276-T278 (M22) -> T279 -> T287 -> T288 -> T289, then the website redesign steps 3-4.

Rules you must keep (from AGENTS.md): real data only, never invent rows, labels or fields;
time-based splits, features known at issue time, compare with the strongest simple baseline, and
promote a model only if the lower 95% paired bootstrap CI of the improvement is above 0, otherwise
publish it as research-only; open each locked test once; Rs 0 only; keys stay in .env and are never
printed; never create accounts, sign in, accept terms or fill web forms (stop and ask the owner);
set TEMP/TMP to D:\monsoon-atlas\.cache\tmp before downloads; record every deviation in
docs/decisions.md before making it; each task ends with its acceptance tests passing and a commit
whose message starts with the task ID. One task per session; split if it grows.

When a task is done, say in plain words what changed, what the numbers were, what you did not
check, and which owner step (if any) is next.
