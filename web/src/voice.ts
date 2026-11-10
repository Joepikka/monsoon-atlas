// T182: opt-in browser speech (D148). Nothing here runs until the user presses a button; the audio
// stays with the browser, and only the final text is handed back. No direct media capture, no auto-speech.
import type { Key } from './i18n';

interface Recognition {
  lang: string; interimResults: boolean; maxAlternatives: number;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void; stop(): void;
}
interface Synth {
  getVoices(): { lang: string }[]; speak(utterance: unknown): void; cancel(): void;
}
export interface SpeechHost {
  SpeechRecognition?: new () => Recognition;
  webkitSpeechRecognition?: new () => Recognition;
  speechSynthesis?: Synth;
  SpeechSynthesisUtterance?: new (text: string) => { lang: string };
}

const REASONS: Record<string, Key> = {
  'not-allowed': 'voice.denied', 'service-not-allowed': 'voice.denied',
  'language-not-supported': 'voice.no_language', 'no-speech': 'voice.no_speech',
};

const recognition = (host: SpeechHost) => host.SpeechRecognition ?? host.webkitSpeechRecognition;
export const voiceInputSupported = (host: SpeechHost): boolean => Boolean(recognition(host));
/** Reading aloud needs an installed English voice; the list can be empty until the browser loads it. */
export const voiceOutputSupported = (host: SpeechHost): boolean =>
  Boolean(host.SpeechSynthesisUtterance && host.speechSynthesis?.getVoices().some(voice => voice.lang.toLowerCase().startsWith('en')));

export interface ListenHandlers { onText(text: string): void; onFail(reason: Key): void; onEnd(): void }

/** Starts one recognition. Call it only from a user action. Returns a function that stops it. */
export function listen(host: SpeechHost, lang: string, handlers: ListenHandlers): () => void {
  const Ctor = recognition(host);
  if (!Ctor) { handlers.onFail('voice.unsupported'); handlers.onEnd(); return () => {}; }
  const session = new Ctor();
  session.lang = lang; session.interimResults = false; session.maxAlternatives = 1;
  session.onresult = event => { const text = event.results[0]?.[0]?.transcript.trim(); if (text) handlers.onText(text); };
  session.onerror = event => handlers.onFail(REASONS[event.error] ?? 'voice.failed');
  session.onend = handlers.onEnd;
  try { session.start(); } catch { handlers.onFail('voice.failed'); handlers.onEnd(); }
  return () => session.stop();
}

/** Speaks text the user asked to hear; never called on its own. */
export function speak(host: SpeechHost, text: string, lang: string): void {
  if (!voiceOutputSupported(host)) return;
  const utterance = new host.SpeechSynthesisUtterance!(text);
  utterance.lang = lang;
  host.speechSynthesis!.cancel();
  host.speechSynthesis!.speak(utterance);
}
