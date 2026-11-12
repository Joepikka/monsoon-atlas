// T261 (child of T182): Ask page with citation cards, evidence age and opt-in voice (D96, D148).
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { search } from '../ask-search';
import { ageDays, askWorker, loadCorpus, SOURCE_BASE, utcSecond, type AskResult, type CorpusView } from '../ask';
import { t, type Key } from '../i18n';
import { listen, speak, voiceInputSupported, voiceOutputSupported, type SpeechHost } from '../voice';

const excerpt = (text: string): string => {
  const words = text.split(/\s+/).filter(Boolean);
  return words.slice(0, 60).join(' ') + (words.length > 60 ? ' …' : '');
};
const speech = (): SpeechHost => window as unknown as SpeechHost;

export default function Ask({ fetcher }: { fetcher?: typeof fetch }) {
  const [corpus, setCorpus] = useState<CorpusView>({ status: 'loading', message: t('corpus.loading') });
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
  const [listening, setListening] = useState(false);
  const [voiceNote, setVoiceNote] = useState<Key>(voiceInputSupported(speech()) ? 'voice.note' : 'voice.unsupported');
  const stop = useRef<() => void>(() => {});
  useEffect(() => { loadCorpus(fetcher).then(setCorpus); }, [fetcher]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (corpus.status !== 'ready' || !question.trim() || busy) return;
    setBusy(true);
    const asOf = utcSecond(new Date());
    const found = search(corpus.chunks, question, { asOf, state: 'ka' });
    setResult(await askWorker(question, found, corpus.release, asOf, fetcher));
    setBusy(false);
  }

  // The only place that starts the microphone: a button press. A failure leaves the text box as it was.
  function toggleVoice() {
    if (listening) { stop.current(); return; }
    setListening(true);
    setVoiceNote('voice.note');
    stop.current = listen(speech(), 'en-IN', {
      onText: text => setQuestion(text.slice(0, 500)),
      onFail: setVoiceNote,
      onEnd: () => setListening(false),
    });
  }

  // The only place that speaks: a button press.
  function readAloud() { if (result) speak(speech(), result.answer, 'en-IN'); }

  return <main className="ask" aria-labelledby="ask-heading">
    <p><a href="./">{t('ask.back')}</a></p>
    <h1 id="ask-heading">{t('ask.heading')}</h1>
    <p>{t('ask.intro')} <a href="https://sachet.ndma.gov.in/" target="_blank"
      rel="noopener noreferrer">{t('ask.official')} <span aria-hidden="true">↗</span></a>.</p>
    <p className="ask-research"><strong>{t('ask.research_label')}</strong> {t('ask.research_body')}</p>
    <p role="status" className={`ask-status ${corpus.status}`}>{busy ? t('ask.searching') : corpus.message}</p>
    <form className="ask-form" onSubmit={submit}>
      <label htmlFor="ask-question">{t('ask.question')}</label>
      <textarea id="ask-question" rows={3} maxLength={500} required value={question}
        onChange={event => setQuestion(event.target.value)} />
      <button type="submit" disabled={corpus.status !== 'ready' || busy}>{t('ask.submit')}</button>
      <button type="button" onClick={toggleVoice} disabled={!voiceInputSupported(speech())}
        aria-describedby="ask-voice-note">{t(listening ? 'voice.stop' : 'voice.start')}</button>
      <p id="ask-voice-note" className="ask-notice">{t(voiceNote)}</p>
    </form>
    {result && <section className="ask-answer" aria-labelledby="ask-answer-heading">
      <h2 id="ask-answer-heading">{t(result.mode === 'generated' ? 'ask.answer' : 'ask.results')}</h2>
      {result.notice && <p className="ask-notice">{result.notice}</p>}
      <p className="ask-text">{result.answer}</p>
      {voiceOutputSupported(speech()) && <button type="button" onClick={readAloud}>{t('read.start')}</button>}
      {result.cited.length > 0 && <ol className="ask-citations" aria-label={t('ask.citations')}>
        {result.cited.map(item => {
          const days = ageDays(item.available_at, result.asOf);
          return <li key={item.chunk_id}><article>
            <h3>{item.heading}</h3>
            <p><a href={SOURCE_BASE + item.path} target="_blank" rel="noopener noreferrer"><code>{item.path}</code>
              {' '}<span aria-hidden="true">↗</span></a></p>
            <p className="ask-age">{t(days === 1 ? 'ask.age_one' : 'ask.age_other',
              { when: item.available_at.replace('T', ' ').replace('Z', ' UTC'), days })}</p>
            {result.source === 'local' && <blockquote>{excerpt(item.text)}</blockquote>}
          </article></li>;
        })}
      </ol>}
    </section>}
  </main>;
}
