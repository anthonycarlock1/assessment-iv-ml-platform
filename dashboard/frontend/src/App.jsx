import './App.css'

const metrics = [
  { label: 'Total requests', value: '1.4M', change: '+12.4%' },
  { label: 'Avg latency', value: '182ms', change: '-8.2%' },
  { label: 'Model accuracy', value: '94.8%', change: '+1.6%' },
  { label: 'Alert volume', value: '3', change: '-2 vs last hour' },
]

const services = [
  { name: 'Fraud detection', status: 'Healthy', latency: '170ms', endpoint: '/api/fraud/predict' },
  { name: 'Forecasting', status: 'Healthy', latency: '240ms', endpoint: '/api/forecasting/predict' },
  { name: 'Recommendations', status: 'Healthy', latency: '210ms', endpoint: '/api/recommendations/predict' },
]

const pipelineSteps = [
  'Terraform provisions VPC, EKS, IAM, and ECR',
  'Docker images are built and pushed to AWS ECR',
  'Kubernetes deployments serve the ML APIs',
  'Dashboard reads health and prediction summaries',
]

function App() {
  return (
    <div className="platform-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Assessment IV</p>
          <h1>ML Platform Dashboard</h1>
        </div>
        <div className="topbar-actions">
          <span className="status-pill status-pill--online">System online</span>
          <button type="button" className="action-button">Refresh</button>
        </div>
      </header>

      <main className="content">
        <section className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow eyebrow--accent">Production overview</p>
            <h2>Monitoring the platform core services in one place.</h2>
            <p>
              This dashboard tracks the health, traffic, and readiness of the fraud,
              forecasting, and recommendation services powering the assessment platform.
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
          {metrics.map((metric) => (
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
              {services.map((service) => (
                <div key={service.name} className="service-row">
                  <div>
                    <strong>{service.name}</strong>
                    <span>{service.endpoint}</span>
                  </div>
                  <div className="service-meta">
                    <span className="status-pill status-pill--online">{service.status}</span>
                    <span className="latency">{service.latency}</span>
                  </div>
                </div>
              ))}
            </div>
          </article>

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
