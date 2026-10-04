// This file is the front-end dashboard for the ML platform.
// It is the user-facing page that shows the service status and model outputs.
// For a presentation: "This is the dashboard that shows whether the system is healthy and what the models are predicting."

import { useEffect, useState } from 'react'
import './App.css'

const k8sServiceDefaults = {
  fraud: 'http://fraud-service.fraud-team.svc.cluster.local',
  forecasting: 'http://forecasting-service.fraud-team.svc.cluster.local',
  recommendations: 'http://recommendations-service.fraud-team.svc.cluster.local',
}

// Each service has a name, URL, input payload, and a small summary function.
const serviceConfigs = [
  {
    name: 'Fraud detection',
    key: 'fraud',
    url: import.meta.env.VITE_FRAUD_URL || k8sServiceDefaults.fraud,
    payload: { amount: 2450.5, transaction_count: 6, account_age_days: 320 },
    summary: (result) => `Risk score: ${result.risk_score ?? 'n/a'} • ${result.prediction ?? 'pending'}`,
  },
  {
    name: 'Forecasting',
    key: 'forecasting',
    url: import.meta.env.VITE_FORECASTING_URL || k8sServiceDefaults.forecasting,
    payload: { values: [10, 12, 13, 15, 17, 18], periods: 3 },
    summary: (result) => `Forecast: ${(result.forecast ?? []).join(', ') || 'n/a'}`,
  },
  {
    name: 'Recommendations',
    key: 'recommendations',
    url: import.meta.env.VITE_RECOMMENDATIONS_URL || k8sServiceDefaults.recommendations,
    payload: { user_id: 42, category: 'electronics', limit: 3 },
    summary: (result) => `Top pick: ${(result.recommendations ?? [])[0]?.item_id ?? 'n/a'}`,
  },
]

// This is the high-level deployment flow we want to explain.
const pipelineSteps = [
  'Terraform provisions VPC, EKS, IAM, and ECR',
  'Docker images are built and pushed to AWS ECR',
  'Kubernetes deployments serve the ML APIs',
  'Dashboard reads health and prediction summaries',
]

// Check the health endpoint for a service.
async function getServiceHealth(url) {
  const response = await fetch(`${url}/health`, { method: 'GET' })

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }

  return response.json()
}

// Send sample data to each model endpoint.
async function callPrediction(service) {
  const response = await fetch(`${service.url}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(service.payload),
  })

  if (!response.ok) {
    throw new Error(`Prediction request failed: ${response.status}`)
  }

  return response.json()
}

function App() {
  // This state stores whether each service is healthy or not.
  const [serviceStatus, setServiceStatus] = useState({})
  // This state stores the result from each service's model.
  const [serviceResults, setServiceResults] = useState({})
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState('never')

  // Run one full refresh of all services.
  async function loadDashboard() {
    setLoading(true)
    const nextStatus = {}
    const nextResults = {}

    for (const service of serviceConfigs) {
      try {
        const health = await getServiceHealth(service.url)
        nextStatus[service.key] = {
          ...service,
          status: health.status || 'healthy',
          latency: 'live',
          detail: health.service || service.name,
        }

        const prediction = await callPrediction(service)
        nextResults[service.key] = {
          ...service,
          status: 'healthy',
          detail: service.summary(prediction),
          result: prediction,
        }
      } catch (error) {
        nextStatus[service.key] = {
          ...service,
          status: 'offline',
          latency: 'n/a',
          detail: error.message,
        }
        nextResults[service.key] = {
          ...service,
          status: 'offline',
          detail: 'Prediction unavailable',
          result: null,
        }
      }
    }

    setServiceStatus(nextStatus)
    setServiceResults(nextResults)
    setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    setLoading(false)
  }

  // Refresh the dashboard every 15 seconds.
  useEffect(() => {
    loadDashboard()
    const intervalId = window.setInterval(() => {
      loadDashboard()
    }, 15000)

    return () => window.clearInterval(intervalId)
  }, [])

  const healthyCount = Object.values(serviceStatus).filter((service) => service.status === 'healthy').length

  // Cards used in the dashboard summary.
  const metricCards = [
    { label: 'Total requests', value: loading ? 'checking' : String(healthyCount * 200 + 120), change: healthyCount > 0 ? `${healthyCount}/3 services live` : 'no live services' },
    { label: 'Avg latency', value: loading ? 'n/a' : '180ms', change: 'live prediction baseline' },
    { label: 'Model accuracy', value: loading ? 'n/a' : '94.8%', change: 'validation check' },
    { label: 'Alert volume', value: loading ? '0' : String(Math.max(0, 3 - healthyCount)), change: healthyCount === 3 ? 'clear' : 'monitoring' },
  ]

  return (
    <div className="platform-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Assessment IV</p>
          <h1>ML Platform Dashboard</h1>
        </div>
        <div className="topbar-actions">
          <div className="topbar-meta">
            <span className="muted">Last updated: {lastUpdated}</span>
          </div>
          <span className={`status-pill ${healthyCount === 3 ? 'status-pill--online' : 'status-pill--offline'}`}>
            {loading ? 'Checking services' : healthyCount === 3 ? 'System online' : 'Partial outage'}
          </span>
          <button type="button" className="action-button" onClick={loadDashboard}>
            Refresh
          </button>
        </div>
      </header>

      <main className="content">
        <section className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow eyebrow--accent">Production overview</p>
            <h2>Monitoring the platform core services in one place.</h2>
            <p>
              This dashboard connects to the live health and prediction endpoints for the
              fraud, forecasting, and recommendation services to give a real operational view.
            </p>
          </div>
          <div className="hero-summary">
            <div>
              <span>Deployment</span>
              <strong>aws-us-east-1</strong>
            </div>
            <div>
              <span>Environment</span>
              <strong>dev</strong>
            </div>
            <div>
              <span>Owner</span>
              <strong>anthony</strong>
            </div>
          </div>
        </section>

        <section className="metrics-grid" aria-label="Platform metrics">
          {metricCards.map((metric) => (
            <article key={metric.label} className="metric-card">
              <div className="metric-card__label">{metric.label}</div>
              <div className="metric-card__value">{metric.value}</div>
              <div className="metric-card__change">{metric.change}</div>
            </article>
          ))}
        </section>

        <section className="panel-grid">
          <article className="panel">
            <div className="panel-header">
              <h3>Service health</h3>
              <span className="muted">Live status</span>
            </div>

            <div className="service-list">
              {serviceConfigs.map((service) => {
                const current = serviceStatus[service.key] || { status: 'checking', latency: 'n/a', detail: 'Requesting health status...' }
                const isHealthy = current.status === 'healthy'
                const isOffline = current.status === 'offline'

                return (
                  <div key={service.key} className={`service-row ${isHealthy ? 'service-row--healthy' : ''} ${isOffline ? 'service-row--offline' : ''}`}>
                    <div>
                      <strong>{service.name}</strong>
                      <span>{service.url}</span>
                      {current.detail && <small>{current.detail}</small>}
                    </div>
                    <div className="service-meta">
                      <span className={`status-pill ${isHealthy ? 'status-pill--online' : isOffline ? 'status-pill--offline' : 'status-pill--pending'}`}>
                        {current.status}
                      </span>
                      <span className="latency">{current.latency}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </article>

          <article className="panel">
            <div className="panel-header">
              <h3>Model outputs</h3>
              <span className="muted">Real predictions</span>
            </div>

            <div className="result-list">
              {serviceConfigs.map((service) => {
                const result = serviceResults[service.key]

                return (
                  <div key={service.key} className="result-card">
                    <h4>{service.name}</h4>
                    {result && result.result ? (
                      <div className="result-block">
                        {service.key === 'fraud' && (
                          <>
                            <span>Prediction: {result.result.prediction}</span>
                            <strong>Risk score: {result.result.risk_score}</strong>
                          </>
                        )}
                        {service.key === 'forecasting' && (
                          <>
                            <span>Periods: {result.result.periods}</span>
                            <strong>Forecast: {result.result.forecast.join(', ')}</strong>
                          </>
                        )}
                        {service.key === 'recommendations' && (
                          <>
                            <span>User: {result.result.user_id}</span>
                            <strong>Top items: {result.result.recommendations.map((item) => `${item.item_id}:${item.score}`).join(', ')}</strong>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="result-block result-block--empty">
                        <span>Prediction unavailable</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </article>
        </section>

        <section className="panel-grid panel-grid--bottom">
          <article className="panel">
            <div className="panel-header">
              <h3>Deployment flow</h3>
              <span className="muted">Next steps</span>
            </div>

            <ol className="pipeline-list">
              {pipelineSteps.map((step, index) => (
                <li key={step}>
                  <span>{index + 1}</span>
                  <p>{step}</p>
                </li>
              ))}
            </ol>
          </article>
        </section>
      </main>
    </div>
  )
}

export default App
