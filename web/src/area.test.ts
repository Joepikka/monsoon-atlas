import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { parseSnapshot } from './data';
import { visibleRecords } from './map/Layers';
import { buildReport } from './report';
const area = JSON.parse(readFileSync(new URL('../tests/fixtures/sachet-ka-area.json',import.meta.url),'utf8'));
const place = JSON.parse(readFileSync(new URL('../tests/fixtures/bangalore-place.json',import.meta.url),'utf8'));
const body = {schema_version:1,state:'ka',release_id:'area-contract',data_revision:'d'.repeat(64),
  as_of:area.fetched_at,published_at:area.fetched_at,records:[area],places:[place]};

describe('official alerts without map geometry',()=>{
  it('retains original area text and clocks with explicitly unavailable coordinates',()=>{
    const record=parseSnapshot(body,'ka').records[0];
    expect(record.longitude).toBeNull(); expect(record.latitude).toBeNull();
    expect(record.area_text).toBe(area.area_text); expect(record.issued_at).toBe(area.issued_at);
  });
  it('keeps an area-only warning in radius and place context without inventing a point',()=>{
    const snapshot={...parseSnapshot(body,'ka'),release_hash:'c'.repeat(64)};
    expect(visibleRecords(snapshot.records,new Set(['alert']),[74,16],5)).toHaveLength(1);
    expect(buildReport(snapshot,place.place_id,place.boundary_version).records[0].longitude).toBeNull();
  });
  it('rejects half-missing coordinates, absent area text and unlocated point records',()=>{
    for (const record of [{...area,longitude:77.5},{...area,area_text:null},{...area,spatial_scope:'point'},
      {...area,source_id:'S01',kind:'weather',value:21.3,unit:'°C'}]) {
      expect(()=>parseSnapshot({...body,records:[record]},'ka')).toThrow();
    }
  });
});
