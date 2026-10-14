import { useEffect, useRef, useState } from 'react'
import './App.css'
import { createPoller } from './polling.js'

// Lists friendly service names and sample form inputs. These are request examples, not saved model
// results.
const services = [
  {key: 'fraud', name: 'Fraud detection', fields: {amount: '2450.5', transaction_count: '6', account_age_days: '320'}},
  {key: 'forecasting', name: 'Forecasting', fields: {values: '10,12,13,15,17,18', periods: '3'}},
  {key: 'recommendations', name: 'Recommendations', fields: {user_id: '42', category: 'electronics', limit: '3'}},
]
// Uses a configured API base or same-origin /api.
const api = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
// Fetches JSON with a timeout/cancellation, reads request IDs, and turns API errors into visible
// messages.
async function request(path, options = {}, timeout = 90000) {
  const response = await fetch(`${api}${path}`, {...options, signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(timeout)]) : AbortSignal.timeout(timeout)})
  const body = await response.json()
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body))
  return {body, requestId: response.headers.get('x-request-id')}
}
// Keeps editable inputs, results, errors, elapsed time, and busy state separate for each service.
function ModelForm({service}) {
  const [fields, setFields] = useState(service.fields)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState(null)
  const [history, setHistory] = useState(null)
  const [historyError, setHistoryError] = useState('')
  const [historyBusy, setHistoryBusy] = useState(false)
  async function loadHistory() {
    setHistoryBusy(true); setHistoryError('')
    try {
      const response = await request(`/${service.key}/history?limit=10`, {}, 10000)
      setHistory(response.body)
    } catch (err) {setHistoryError(err.message)}
    finally {setHistoryBusy(false)}
  }
  // Converts text inputs into the business payload, rejects empty forecast values, and sends the
  // correct prediction request.
  async function submit(event) {
    event.preventDefault()
    setBusy(true); setError(''); setResult(null); setElapsed(null)
    const start = performance.now()
    try {
      const payload = Object.fromEntries(Object.entries(fields).map(([key, value]) => [key,
        key === 'category' ? value.trim() : key === 'values' ? value.split(',').map(v => Number(v.trim())) : Number(value)]))
      if (service.key === 'forecasting' && fields.values.split(',').some(v => !v.trim())) throw new Error('Enter comma-separated numbers without empty values.')
      const response = await request(`/${service.key}/predict`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)})
      setResult(response)
    } catch (err) {setError(err.message)}
    finally {setElapsed(Math.round(performance.now() - start)); setBusy(false)}
  }
  // Builds labeled inputs and a submit button, then shows the actual response, elapsed time,
  // provider, and request ID.
  return <article className="panel">
    <h2>{service.name}</h2>
    <form onSubmit={submit}>
      {Object.entries(fields).map(([key, value]) => <label key={key}>{key.replaceAll('_', ' ')}
        <input required type={['category', 'values'].includes(key) ? 'text' : 'number'} step={key === 'amount' ? 'any' : '1'}
          min={['user_id', 'limit', 'periods'].includes(key) ? 1 : 0} value={value}
          onChange={e => setFields({...fields, [key]: e.target.value})}/>
      </label>)}
      {service.key === 'recommendations' && <p className="muted">Categories: books, electronics, fashion, home, sports.</p>}
      <button className="action-button" disabled={busy}>{busy ? 'Predicting…' : 'Run prediction'}</button>
    </form>
    <div aria-live="polite">
      {error && <p role="alert" className="result-block--empty">{error}</p>}
      {result && <><p>Live response · {elapsed} ms · {result.body.provider} inference</p>
        <pre>{JSON.stringify(result.body, null, 2)}</pre><small>Request: {result.requestId}</small></>}
    </div>
    <details>
      <summary>Recent prediction history</summary>
      <button type="button" disabled={historyBusy} onClick={loadHistory}>
        {historyBusy ? 'Loading history…' : 'Load recent predictions'}
      </button>
      <div aria-live="polite">
        {historyError && <p role="alert">{historyError}</p>}
        {history && !history.enabled && <p>Prediction history is disabled.</p>}
        {history?.enabled && history.items.length === 0 && <p>No saved predictions yet.</p>}
        {history?.enabled && history.items.map(item => <div key={`${item.created_at}-${item.request_id}`}>
          <p>{new Date(item.created_at).toLocaleString()} · Request: {item.request_id}</p>
          <pre>{JSON.stringify({input: item.payload, result: item.result}, null, 2)}</pre>
        </div>)}
      </div>
    </details>
  </article>
}
// Displays API-supplied team, health, readiness, model/release versions, provider, endpoint, and
// region. Missing data and errors stay visible.
function ServiceStatus({service, status = {}}) {
  const metadata = status.metadata?.body
  return <article className="panel" aria-label={`${service.name} operations`}>
    <h3>{service.name}</h3>
    <p>Service: {metadata?.service || service.key}</p>
    <p>Owning team: {metadata?.team || 'Unavailable'}</p>
    {['health', 'ready'].map(kind => {
      const check = status[kind]
      // Renders the header, manual refresh button, service operations cards, and three independent
      // prediction forms.
      return <div key={kind} className="operation-status">
        <strong>{kind === 'health' ? 'Health' : 'Readiness'}: </strong>
        <span>{check?.state === 'error' ? 'Unavailable' : check?.body?.status || 'Checking…'}</span>
        {check?.state === 'loading' && check.body && <small> Updating…</small>}
        {check?.state === 'error' && <small role="alert"> {check.error}</small>}
        {check?.checkedAt && <small> Last checked: {new Date(check.checkedAt).toLocaleTimeString()}</small>}
      </div>
    })}
    <p>Model: {metadata?.model || 'Unavailable'} · Version: {metadata?.model_version || 'Unavailable'}</p>
    <p>Service version: {metadata?.service_version || 'Unavailable'}</p>
    <p>Inference: {metadata?.provider || 'Unavailable'}</p>
    {metadata?.endpoint && <p className="endpoint">Endpoint: {metadata.endpoint} ({metadata.region || 'Region unavailable'})</p>}
    {status.metadata?.state === 'loading' && <small>Loading metadata…</small>}
    {status.metadata?.state === 'error' && <small role="alert">Metadata unavailable: {status.metadata.error}</small>}
  </article>
}
// Stores each service/check separately and keeps a reference to the active poller.
export default function App() {
  const [status, setStatus] = useState({})
  const poller = useRef(null)
  // Starts independent background checks, merges each response immediately, and stops/aborts
  // checks when the component unmounts.
  useEffect(() => {
    const instance = createPoller(services, request, (service, kind, check) => {
      setStatus(previous => ({...previous, [service]: {...previous[service], [kind]:
        check.state === 'loading' ? {...previous[service]?.[kind], ...check} : check}}))
    })
    poller.current = instance
    return () => { instance.stop(); poller.current = null }
  }, [])
  return <div className="platform-shell">
    <header className="topbar"><div><p className="eyebrow">Assessment IV</p><h1>ML Platform Operations</h1></div>
      <button className="action-button" onClick={() => poller.current?.refresh()}>Refresh status</button></header>
    <main className="content">
      <section className="hero-panel"><div className="hero-copy">
        <h2>Service operations</h2><p>Health, readiness, and model metadata come from the deployed APIs. Status checks refresh automatically every 15 seconds after each response.</p>
        <p className="muted">Readiness validates configuration; a ready service can still encounter an inference runtime failure.</p>
      </div></section>
      <section className="prediction-grid" aria-label="Live service status" aria-live="polite">
        {services.map(service => <ServiceStatus key={service.key} service={service} status={status[service.key]}/>)}</section>
      <section><h2>Test model requests</h2><p>Enter data to execute a live prediction.</p>
        <div className="prediction-grid">{services.map(service => <ModelForm key={service.key} service={service}/>)}</div></section>
    </main>
  </div>
}
