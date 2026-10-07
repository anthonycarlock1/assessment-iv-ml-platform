// Each endpoint owns its timer: a slow or failed service cannot hold up another.
// Creates separate tasks for health, readiness, and metadata for each service.
export function createPoller(services, request, update, interval = 15000) {
  let stopped = false
  const tasks = services.flatMap(service => ['health', 'ready', 'metadata'].map(kind => ({service: service.key, kind})))
  // Skips overlapping requests, starts a cancellable five-second check, and immediately reports
  // loading, success, or error.
  async function run(task) {
    if (stopped || task.running) return
    clearTimeout(task.timer)
    task.running = true
    task.controller = new AbortController()
    update(task.service, task.kind, {state: 'loading'})
    try {
      const {body} = await request(`/${task.service}/${task.kind}`, {signal: task.controller.signal}, 5000)
      if (!stopped) update(task.service, task.kind, {state: 'success', body, checkedAt: new Date().toISOString()})
    } catch (error) {
      if (!stopped) update(task.service, task.kind, {state: 'error', error: error.message, checkedAt: new Date().toISOString()})
    // After the check completes, schedules that same check again; the default pause is 15 seconds.
    } finally {
      task.running = false
      if (!stopped) task.timer = setTimeout(() => run(task), interval)
    }
  }
  // Starts idle checks without duplicating checks already running.
  function refresh() { tasks.forEach(task => { void run(task) }) }
  refresh()
  // Stops future timers and aborts pending checks.
  return {refresh, stop() {
    stopped = true
    tasks.forEach(task => { clearTimeout(task.timer); task.controller?.abort() })
  }}
}
