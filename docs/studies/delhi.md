# Delhi bus study registration (T150)

**The study cannot start.** It needs the S38 Delhi Open Transit Data feed, and S38 is blocked on
owner step H04 (registration, key, Terms; see [s38.md](../sources/s38.md), D135, D136). Nothing
below is measured or invented: every row says what is unknown and why. Config:
[`configs/states/dl.yaml`](../../configs/states/dl.yaml) (all sources disabled).

## Registration

| Item | Status | Basis |
|---|---|---|
| Access approval | none | H04 pending; no form submitted, no key, Terms not accepted (S38 e02 to e07) |
| Protobuf schema | not published, not read | The documentation lists GTFS file names only and no field list (S38 e05); no sample was obtained |
| Trip linkage | unknown | Whether positions carry a trip that matches `trips.txt` is unread (S38 `field_map`) |
| Selected routes | none | No route is selected before the static GTFS is read; the public page counts (543 bus, 36 DMRC routes) are counts, not a selection |
| Study dates | not frozen | The plan's start of 2028-01-17 assumed approval on schedule; the whole manifest shifts and nothing earlier is invented |
| Decoder (`worker/src/protobuf.ts`) | deferred | No real sample and no feed to decode; pinned protobufjs not added (D137) |

## Order of work once H04 is done

1. Owner completes H04 and puts `OTD_API_KEY` in `.env` and the static ZIP in `data/raw/S38`.
2. Re-run T148: one real sample, its protobuf fields, units, timestamp meaning, trip and calendar
   match, quota, and whether the Terms allow this use.
3. Select 20 routes from the real static files; record the trip linkage; exclude unmatched trips.
4. Add the decoder from the documented schema with pinned protobufjs; inspect the real sample size.
5. Only after the collection-ready gate (T152), freeze the study dates in the study manifest.

Related blocked source: S24 CPCB stations (T146, D133), also disabled in `dl.yaml`.
