// Requires temporary Playwright tooling and an installed browser; touches only this browser.
const {chromium} = require('playwright')
const assert = require('node:assert/strict')

;(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})})
  try {
    const page = await browser.newPage()
    const historyCalls = []
    page.on('request', request => {
      if (request.url().includes('/history?')) historyCalls.push(request.url())
    })
    await page.goto(process.env.DASHBOARD_URL || 'http://127.0.0.1:8080')
    await page.getByRole('article', {name: 'Fraud detection operations'})
      .getByText('healthy', {exact: true}).waitFor()
    assert.equal(historyCalls.length, 0, 'History must not poll automatically')
    const services = {fraud: 'Fraud detection', forecasting: 'Forecasting', recommendations: 'Recommendations'}
    const checks = []
    for (const [key, name] of Object.entries(services)) {
      const form = page.locator('article').filter({has: page.getByRole('heading', {name, level: 2})})
      await form.getByText('Recent prediction history', {exact: true}).click()
      const pending = page.waitForResponse(response => response.url().includes(`/api/${key}/history?`))
      await form.getByRole('button', {name: 'Load recent predictions', exact: true}).click()
      const response = await pending
      assert.equal(response.status(), 200)
      const history = await response.json()
      assert.ok(history.enabled && history.items.length > 0)
      await form.getByText(new RegExp(`Request: ${history.items[0].request_id}`)).waitFor()
      checks.push({service: key, history_displayed: true})
    }
    await page.route('**/api/fraud/history?*', route => route.fulfill({status: 503,
      contentType: 'application/json', body: JSON.stringify({detail: 'Prediction history unavailable'})}))
    const fraud = page.locator('article').filter({has: page.getByRole('heading', {name: 'Fraud detection', level: 2})})
    await fraud.getByRole('button', {name: 'Load recent predictions', exact: true}).click()
    await fraud.getByRole('alert').getByText('Prediction history unavailable').waitFor()
    const predictionResponse = page.waitForResponse(response => response.url().endsWith('/api/fraud/predict'), {timeout: 95000})
    await fraud.getByRole('button', {name: 'Run prediction', exact: true}).click()
    const response = await predictionResponse
    assert.equal(response.status(), 200)
    assert.equal((await response.json()).provider, 'sagemaker')
    await fraud.getByText(/Live response/).waitFor()
    console.log(JSON.stringify({checks, no_automatic_history_polling: true,
      prediction_succeeds_during_browser_history_outage: true}, null, 2))
  } finally {
    await browser.close()
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
