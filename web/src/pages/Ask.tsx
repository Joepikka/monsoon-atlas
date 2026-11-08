// T261 (child of T182): English text Ask page with citation cards and evidence age (D96).
import { useEffect, useState, type FormEvent } from 'react';
import { search } from '../ask-search';
import { ageDays, askWorker, loadCorpus, utcSecond, type AskResult, type CorpusView } from '../ask';

const excerpt = (text: string): string => {
  const words = text.split(/\s+/).filter(Boolean);
  return words.slice(0, 60).join(' ') + (words.length > 60 ? ' …' : '');
};

export default function Ask({ fetcher }: { fetcher?: typeof fetch }) {
  const [corpus, setCorpus] = useState<CorpusView>({ status: 'loading', message: 'Loading the project documents…' });
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
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

  return <main className="ask" aria-labelledby="ask-heading">
    <p><a href="./">Back to the map</a></p>
    <h1 id="ask-heading">Ask the project documents</h1>
    <p>Answers quote Monsoon Atlas documents only, in English, with the file and commit time of each source.
      This is not an emergency service: for warnings, use the <a href="https://sachet.ndma.gov.in/" target="_blank"
        rel="noopener noreferrer">official warnings <span aria-hidden="true">↗</span></a>.</p>
    <p className="ask-research"><strong>Research-only:</strong> this search has not passed its quality check, so a
      result can miss the most relevant section. Read the cited files.</p>
    <p role="status" className={`ask-status ${corpus.status}`}>{busy ? 'Searching…' : corpus.message}</p>
    <form className="ask-form" onSubmit={submit}>
      <label htmlFor="ask-question">Question</label>
      <textarea id="ask-question" rows={3} maxLength={500} required value={question}
        onChange={event => setQuestion(event.target.value)} />
      <button type="submit" disabled={corpus.status !== 'ready' || busy}>Ask</button>
    </form>
    {result && <section className="ask-answer" aria-labelledby="ask-answer-heading">
      <h2 id="ask-answer-heading">{result.mode === 'generated' ? 'Answer' : 'Search results'}</h2>
      {result.notice && <p className="ask-notice">{result.notice}</p>}
      <p className="ask-text">{result.answer}</p>
      {result.cited.length > 0 && <ol className="ask-citations" aria-label="Citations">
        {result.cited.map(item => {
          const days = ageDays(item.available_at, result.asOf);
          return <li key={item.chunk_id}><article>
            <h3>{item.heading}</h3>
            <p><code>{item.path}</code></p>
            <p className="ask-age">Committed {item.available_at.replace('T', ' ').replace('Z', ' UTC')}, {days} {days === 1 ? 'day' : 'days'} before
              this answer</p>
            {result.source === 'local' && <blockquote>{excerpt(item.text)}</blockquote>}
          </article></li>;
        })}
      </ol>}
    </section>}
  </main>;
}
