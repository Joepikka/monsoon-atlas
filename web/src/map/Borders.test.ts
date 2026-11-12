import { describe, expect, it } from 'vitest';
import { hideInternationalBorders, internationalBorderLayerIds, type StyleLayer } from './Borders';

// TEST INPUT, hand-built (the live OpenFreeMap style cannot be fetched offline): one layer per
// filter shape that an OpenMapTiles `boundary` layer can be styled with, plus layers to keep.
const layers: StyleLayer[] = [
  { id: 'country-expression', 'source-layer': 'boundary', filter: ['all', ['==', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]] },
  { id: 'country-legacy', 'source-layer': 'boundary', filter: ['all', ['==', 'admin_level', 2], ['==', 'disputed', 1]] },
  { id: 'country-le', 'source-layer': 'boundary', filter: ['<=', ['get', 'admin_level'], 2] },
  { id: 'country-in', 'source-layer': 'boundary', filter: ['in', ['get', 'admin_level'], ['literal', [1, 2]]] },
  { id: 'country-legacy-in', 'source-layer': 'boundary', filter: ['in', 'admin_level', 1, 2] },
  { id: 'country-negated', 'source-layer': 'boundary', filter: ['!', ['>', ['get', 'admin_level'], 2]] },
  { id: 'country-unfiltered', 'source-layer': 'boundary' },
  { id: 'country-unknown-expression', 'source-layer': 'boundary', filter: ['match', ['get', 'admin_level'], [2], true, false] },
  { id: 'country-unmodelled-property', 'source-layer': 'boundary', filter: ['all', ['==', ['get', 'admin_level'], 2], ['==', ['get', 'claimed_by'], 'IN']] },
  { id: 'state-expression', 'source-layer': 'boundary', filter: ['==', ['get', 'admin_level'], 4] },
  { id: 'state-legacy', 'source-layer': 'boundary', filter: ['all', ['>=', 'admin_level', 3], ['<=', 'admin_level', 4]] },
  { id: 'state-in', 'source-layer': 'boundary', filter: ['in', 'admin_level', 3, 4] },
  { id: 'state-any', 'source-layer': 'boundary', filter: ['any', ['==', 'admin_level', 4], ['==', 'admin_level', 5]] },
  { id: 'state-not-country', 'source-layer': 'boundary', filter: ['!', ['<=', ['get', 'admin_level'], 2]] },
  { id: 'water', 'source-layer': 'water' },
  { id: 'our-district-lines' }, // a geoBoundaries layer has no source-layer
];
const COUNTRY = layers.filter(layer => layer.id.startsWith('country-')).map(layer => layer.id);

describe('basemap international borders', () => {
  it('selects every layer that can draw a country border and none that cannot', () => {
    expect(internationalBorderLayerIds(layers)).toEqual(COUNTRY);
  });
  it('hides the selected layers through the style host and touches nothing else', () => {
    const calls: unknown[][] = [];
    hideInternationalBorders({ getStyle: () => ({ layers }), setLayoutProperty: (...args) => calls.push(args) });
    expect(calls).toEqual(COUNTRY.map(id => [id, 'visibility', 'none']));
  });
});
