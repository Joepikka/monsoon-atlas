// The public map draws no international border (D168): the OpenFreeMap basemap's country
// boundary layers are hidden at style load. Layers are found by what they draw (OpenMapTiles
// `boundary` source layer, admin_level 1 or 2), not by id. Our own geoBoundaries lines have no
// `source-layer`, so they are never selected.

export interface StyleLayer { id: string; 'source-layer'?: string; filter?: unknown }
export interface StyleHost {
  getStyle(): { layers: StyleLayer[] };
  setLayoutProperty(id: string, name: 'visibility', value: 'none'): unknown;
}

type Props = Record<string, number>;
type Tri = boolean | null; // null: the filter cannot be evaluated, so the feature may be drawn
const UNKNOWN = Symbol('unknown');

// Every combination of the OpenMapTiles boundary fields that a style filter can test.
const PROBES: Props[] = [1, 2].flatMap(admin_level =>
  [0, 1].flatMap(disputed => [0, 1].map(maritime => ({ admin_level, disputed, maritime }))));

function operand(node: unknown, props: Props, legacyKey: boolean): unknown {
  if (Array.isArray(node)) {
    if (node[0] === 'literal') return node[1];
    return node[0] === 'get' && typeof node[1] === 'string' && node[1] in props ? props[node[1]] : UNKNOWN;
  }
  if (legacyKey && typeof node === 'string') return node in props ? props[node] : UNKNOWN;
  return node;
}

const and = (a: Tri, b: Tri): Tri => (a === false || b === false ? false : a === null || b === null ? null : true);
const or = (a: Tri, b: Tri): Tri => (a === true || b === true ? true : a === null || b === null ? null : false);
const not = (a: Tri): Tri => (a === null ? null : !a);

/** Evaluates a legacy or expression layer filter for one feature; anything unsupported is null. */
function test(filter: unknown, props: Props): Tri {
  if (typeof filter === 'boolean') return filter;
  if (!Array.isArray(filter)) return null;
  const [op, ...args] = filter;
  const any = () => args.reduce<Tri>((acc, arg) => or(acc, test(arg, props)), false);
  switch (op) {
    case 'all': return args.reduce<Tri>((acc, arg) => and(acc, test(arg, props)), true);
    case 'any': return any();
    case 'none': return not(any());
    case '!': return not(test(args[0], props));
    case 'has': return typeof args[0] === 'string' && args[0] in props ? true : null;
    case '!has': return typeof args[0] === 'string' && args[0] in props ? false : null;
    case '==': case '!=': case '<': case '<=': case '>': case '>=': {
      const legacy = filter.length === 3 && !Array.isArray(args[0]) && !Array.isArray(args[1]);
      const a = operand(args[0], props, legacy);
      const b = operand(args[1], props, false);
      if (a === UNKNOWN || b === UNKNOWN) return null;
      if (op === '==') return a === b;
      if (op === '!=') return a !== b;
      if (typeof a !== 'number' || typeof b !== 'number') return null;
      return op === '<' ? a < b : op === '<=' ? a <= b : op === '>' ? a > b : a >= b;
    }
    case 'in': case '!in': {
      const expression = Array.isArray(args[1]) && args[1][0] === 'literal';
      const needle = operand(args[0], props, !expression);
      const list = expression ? args[1][1] : args.slice(1);
      if (needle === UNKNOWN || !Array.isArray(list)) return null;
      return op === 'in' ? list.includes(needle) : !list.includes(needle);
    }
    default: return null;
  }
}

/** Ids of basemap layers that can draw a country boundary (admin_level 2 or less, disputed lines included). */
export function internationalBorderLayerIds(layers: StyleLayer[]): string[] {
  return layers
    .filter(layer => layer['source-layer'] === 'boundary' && PROBES.some(props => test(layer.filter ?? true, props) !== false))
    .map(layer => layer.id);
}

export function hideInternationalBorders(map: StyleHost): void {
  for (const id of internationalBorderLayerIds(map.getStyle().layers)) map.setLayoutProperty(id, 'visibility', 'none');
}
