# Monsoon Atlas

A free, public map of Indian states that shows what is happening now, what models predict next, and how accurate past predictions were. Karnataka first, then Kerala, then Delhi.

**Status:** P1 in progress. Data contracts, the approved M05 drought hindcast and a local React map shell are built. No public deployment or MVP completion is claimed. See [current handoff](docs/HANDOFF.md) for completed tasks and source/review blockers.

Run the local map with the pinned Node toolchain: `powershell -NoProfile -File scripts/web.ps1 run dev`.
Setup and checks: [web shell](docs/web-shell.md).
Place reports: [frozen links and print/PDF](docs/web-lens.md).
Hosting preparation: [local Worker](docs/worker.md); [owner account steps](docs/account-setup.md).

> Monsoon Atlas is an independent research project. It is not an emergency service and does not replace official information. In an emergency, contact the appropriate emergency service.

## Documents

- [Plan](docs/plan.pdf): full planning handover (tasks, model cards, data sources)
- [Amendments v1](docs/amendments.md): changes to the plan; these win where they conflict
- [Decisions log](docs/decisions.md)
- [Agent rules](AGENTS.md)
- Background: [research notes](docs/research/kw-live-and-india-data-research.md), [planning PDFs](docs/planning/)

## Licence

Original code is MIT licensed (see [LICENSE](LICENSE)). Each dataset keeps its own licence and attribution terms.
