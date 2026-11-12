import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { filterWarnings, parseArchive } from './Warnings';

const cap = JSON.parse(readFileSync(new URL('../../tests/fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
const warning = { ...cap, first_seen: cap.fetched_at, last_seen: cap.fetched_at };
const archive = { schema_version: 1, state: 'ka', archive_since: cap.fetched_at, built_at: cap.fetched_at, count: 1, warnings: [warning] };

describe('warning archive (D189)', () => {
  it('parses a real archived CAP warning and filters by text and severity', () => {
    const parsed = parseArchive(archive);
    expect(parsed.count).toBe(1);
    expect(filterWarnings(parsed.warnings, 'bengaluru', '')).toHaveLength(1);
    expect(filterWarnings(parsed.warnings, 'kodagu', '')).toHaveLength(0);
    expect(filterWarnings(parsed.warnings, '', 'Moderate')).toHaveLength(1);
    expect(filterWarnings(parsed.warnings, '', 'Severe')).toHaveLength(0);
  });
  it('refuses another state, missing fields and non-https source links', () => {
    expect(() => parseArchive({ ...archive, state: 'kl' })).toThrow('Invalid warning archive.');
    expect(() => parseArchive({ ...archive, warnings: [{ ...warning, title: undefined }] })).toThrow('Invalid archived warning.');
    expect(() => parseArchive({ ...archive, warnings: [{ ...warning, source_url: 'http://x' }] })).toThrow('Invalid archived warning.');
  });
});
