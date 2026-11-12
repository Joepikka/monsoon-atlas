// T261 (child of T182): browser lexical search over the public Ask corpus (D96).
// Same filters, per-document cap and near-duplicate rule as src/atlas/rag/retrieve.py;
// no imports, so the recall check can run this file under plain Node.

export interface CorpusChunk {
  chunk_id: string; doc_id: string; path: string; heading: string; text: string;
  available_at: string; expires_at: string | null; states: string; sha256: string;
}

const STOPWORDS = new Set(('a an and are as at be by can could do does for from how i if in is it its my of on or ' +
  'the this that to was what when where which who why will with').split(' '));
const words = (text: string): string[] => text.toLowerCase().match(/[\p{L}\p{N}_]+/gu) ?? [];
// shortcut: a plural/verb suffix trim stands in for FTS5's Porter stemmer; use a real stemmer if recall drops.
const stem = (word: string): string => word.length > 4 ? word.replace(/(?:ies|es|s|ing|ed)$/, '') : word;
const shingles = (text: string): Set<string> => {
  const list = words(text);
  return new Set(Array.from({ length: Math.max(1, list.length - 2) }, (_, i) => list.slice(i, i + 3).join(' ')));
};

export function terms(question: string): string[] {
  return [...new Set(words(question).filter(word => !STOPWORDS.has(word)).map(stem))];
}

/** Top `limit` chunks known at `asOf` (UTC "YYYY-MM-DDTHH:MM:SSZ") for `state`, BM25 with heading weight 2. */
export function search(chunks: CorpusChunk[], question: string, options: { asOf: string; state: string; limit?: number }): CorpusChunk[] {
  const wanted = terms(question);
  if (!wanted.length) return [];
  const { asOf, state, limit = 5 } = options;
  const live = chunks.filter(item => item.available_at <= asOf && (item.expires_at === null || item.expires_at > asOf) &&
    (item.states.includes(`,${state},`) || item.states.includes(',all,')));
  // FTS5 bm25(): weighted term frequency over heading (x2) and text, length over both, corpus-wide statistics.
  const fields = chunks.map(item => [words(item.heading).map(stem), words(item.text).map(stem)]);
  const average = fields.reduce((sum, [heading, text]) => sum + heading.length + text.length, 0) / Math.max(1, chunks.length);
  const documentFrequency = new Map(wanted.map(term => [term, fields.filter(item => item.some(field => field.includes(term))).length]));
  const position = new Map(chunks.map((item, index) => [item.chunk_id, index]));
  const score = (item: CorpusChunk): number => {
    const [heading, text] = fields[position.get(item.chunk_id)!];
    const length = heading.length + text.length;
    let total = 0;
    for (const term of wanted) {
      const n = documentFrequency.get(term)!;
      const frequency = 2 * heading.filter(word => word === term).length + text.filter(word => word === term).length;
      if (!frequency) continue;
      const idf = Math.max(1e-6, Math.log((chunks.length - n + 0.5) / (n + 0.5)));
      total += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / Math.max(1, average)));
    }
    return total;
  };
  const ranked = live.map(item => ({ item, value: score(item) })).filter(entry => entry.value > 0)
    .sort((a, b) => b.value - a.value || (a.item.chunk_id < b.item.chunk_id ? -1 : 1)).slice(0, 50);
  const selected: CorpusChunk[] = []; const seen: Set<string>[] = [];
  for (const { item } of ranked) {
    const current = shingles(item.text);
    const duplicate = seen.some(other => {
      const shared = [...current].filter(value => other.has(value)).length;
      return shared / Math.max(1, new Set([...current, ...other]).size) > 0.5;
    });
    // Chunks are at most 300 tokens, so five never reach the 3000-token context cap.
    if (selected.filter(other => other.doc_id === item.doc_id).length >= 2 || duplicate) continue;
    selected.push(item); seen.push(current);
    if (selected.length === limit) break;
  }
  return selected;
}
