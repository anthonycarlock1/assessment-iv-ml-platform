import test from 'node:test'
import assert from 'node:assert/strict'
import { createPoller } from './polling.js'
// Gives pending promises/timers time to settle and fails if the expected state never arrives.
const tick = () => new Promise(resolve => setTimeout(resolve, 5))
async function until(predicate) {
  for (let i = 0; i < 100; i++) { if (predicate()) return; await tick() }
  assert.fail('Polling did not reach the expected state')
}
// Leaves one service hanging and another failed, and verifies healthy service checks still finish.
test('healthy services update while another service hangs or fails', async () => {
  const updates = []
  const request = async path => {
    if (path.startsWith('/slow/')) return new Promise(() => {})
    if (path.startsWith('/failed/')) throw new Error('Downstream unavailable')
    return {body: {status: 'ready', team: 'healthy-team'}}
  }
  const poller = createPoller(['slow','failed','healthy'].map(key => ({key})), request,
    (service, kind, check) => updates.push({service,kind,...check}), 10000)
  try {
    await until(() => updates.some(u => u.service === 'healthy' && u.kind === 'metadata' && u.state === 'success'))
    assert.equal(updates.filter(u => u.service === 'healthy' && u.state === 'success').length, 3)
    assert.equal(updates.filter(u => u.service === 'failed' && u.state === 'error').length, 3)
    assert.equal(updates.filter(u => u.service === 'slow' && u.state === 'success').length, 0)
  } finally { poller.stop() }
})
// Makes readiness fail once, then proves the next automatic poll succeeds.
test('automatic polling recovers a failed endpoint', async () => {
  const updates = []
  let attempts = 0
  const poller = createPoller([{key:'fraud'}], async path => {
    if (path.endsWith('/ready') && ++attempts === 1) throw new Error('Temporarily unavailable')
    return {body:{status:'ready'}}
  }, (service,kind,check) => updates.push({service,kind,...check}), 5)
  try {
    await until(() => updates.some(u => u.kind === 'ready' && u.state === 'success'))
    assert.ok(updates.some(u => u.kind === 'ready' && u.state === 'error'))
    assert.ok(attempts >= 2)
  } finally { poller.stop() }
})
// Proves manual refresh does not duplicate pending checks and stop prevents later UI updates.
test('refresh does not overlap checks and stop aborts pending work', async () => {
  const updates=[]; const signals=[]; const resolve=[]
  const poller=createPoller([{key:'fraud'}], (path,options) => {
    signals.push(options.signal)
    return new Promise(done => resolve.push(done))
  }, (...update) => updates.push(update))
  poller.refresh()
  assert.equal(signals.length,3)
  poller.stop()
  assert.ok(signals.every(signal => signal.aborted))
  const count=updates.length
  resolve.forEach(done => done({body:{status:'ready'}}))
  await tick()
  assert.equal(updates.length,count)
})
