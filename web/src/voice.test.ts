import { describe, expect, it } from 'vitest';
import { LOCALES, SELECTABLE, t } from './i18n';
import { listen, speak, voiceInputSupported, voiceOutputSupported, type SpeechHost } from './voice';

// Hand-built fake browser (test inputs): records every call so "nothing before consent" is checkable.
function fakeHost(error?: string, transcript = ' groundwater ') {
  const calls: string[] = [];
  class Fake {
    lang = ''; interimResults = true; maxAlternatives = 9;
    onresult: ((e: { results: { transcript: string }[][] }) => void) | null = null;
    onerror: ((e: { error: string }) => void) | null = null;
    onend: (() => void) | null = null;
    constructor() { calls.push('construct'); }
    start() {
      calls.push('start');
      if (error) this.onerror?.({ error }); else this.onresult?.({ results: [[{ transcript }]] });
      this.onend?.();
    }
    stop() { calls.push('stop'); }
  }
  const synth = { getVoices: () => [{ lang: 'hi-IN' }, { lang: 'en-IN' }], cancel: () => calls.push('cancel'),
    speak: () => calls.push('speak') };
  const host = { webkitSpeechRecognition: Fake, speechSynthesis: synth, SpeechSynthesisUtterance: class { constructor(public text: string) {} lang = '' } };
  return { host: host as unknown as SpeechHost, calls };
}

describe('i18n lookup', () => {
  it('fills values, throws on a missing key or value, and offers only English', () => {
    expect(t('corpus.ready', { count: 10 })).toBe('10 document sections loaded.');
    expect(() => t('nope' as never)).toThrow('Missing UI string');
    expect(() => t('corpus.ready')).toThrow('Missing value count');
    expect(SELECTABLE).toEqual(['en']);
    const keys = Object.keys(LOCALES.en).sort();
    for (const locale of ['kn', 'ml', 'hi'] as const) expect(Object.keys(LOCALES[locale]).sort()).toEqual(keys);
    expect(t('ask.submit', {}, 'kn')).not.toBe(t('ask.submit'));
  });
});

describe('opt-in voice', () => {
  it('touches the microphone only when listen is called', () => {
    const { host, calls } = fakeHost();
    expect(voiceInputSupported(host)).toBe(true);
    expect(voiceOutputSupported(host)).toBe(true);
    expect(calls).toEqual([]);
    const heard: string[] = [];
    listen(host, 'en-IN', { onText: text => heard.push(text), onFail: () => {}, onEnd: () => {} });
    expect(calls).toEqual(['construct', 'start']);
    expect(heard).toEqual(['groundwater']);
  });

  it('keeps text input usable: unsupported and failures give a reason', () => {
    const reasons: string[] = [];
    const record = { onText: () => {}, onFail: (reason: string) => reasons.push(reason), onEnd: () => {} };
    expect(voiceInputSupported({})).toBe(false);
    listen({}, 'en-IN', record);
    for (const error of ['not-allowed', 'language-not-supported', 'no-speech', 'audio-capture']) {
      listen(fakeHost(error).host, 'en-IN', record);
    }
    expect(reasons).toEqual(['voice.unsupported', 'voice.denied', 'voice.no_language', 'voice.no_speech', 'voice.failed']);
  });

  it('speaks only on request and only with an installed English voice', () => {
    const { host, calls } = fakeHost();
    speak(host, 'text', 'en-IN');
    expect(calls).toEqual(['cancel', 'speak']);
    const none = { ...host, speechSynthesis: { getVoices: () => [{ lang: 'hi-IN' }], cancel: () => {}, speak: () => { throw new Error('spoke'); } } } as SpeechHost;
    expect(voiceOutputSupported(none)).toBe(false);
    speak(none, 'text', 'en-IN');
  });
});
