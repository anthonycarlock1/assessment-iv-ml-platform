// Optional live browser verification. Requires Playwright and an installed browser.
// Loads browser automation, assertions, and screenshot support.
const {chromium} = require('playwright')
const fs = require('node:fs')
const assert = require('node:assert/strict')
;(async () => {
  // Opens an isolated headless browser, optionally using the configured Chrome executable.
  const browser = await chromium.launch({headless:true, ...(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {})})
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}})
    const counts = {}
    const metadata = {}
    // Counts actual status polls and captures real service metadata.
    page.on('response', async response => {
      const match = response.url().match(/\/api\/([^/]+)\/(health|ready|metadata)$/)
      if (match) {
        const key = `${match[1]}/${match[2]}`
        counts[key] = (counts[key] || 0) + 1
        if (match[2] === 'metadata' && response.ok()) {
          const body = await response.json().catch(() => null)
          if (body) metadata[match[1]] = body
        }
      }
    })
    await page.goto(process.env.DASHBOARD_URL || 'http://127.0.0.1:8080')
    // Checks owning team, separate health/readiness, model version, and endpoint text for every
    // card.
    for (const service of ['fraud','forecasting','recommendations']) {
      const name = {fraud:'Fraud detection',forecasting:'Forecasting',recommendations:'Recommendations'}[service]
      const card = page.getByRole('article',{name:`${name} operations`})
      await card.getByText(`Owning team: ${service}-team`,{exact:true}).waitFor()
      await card.getByText('healthy',{exact:true}).waitFor()
      await card.getByText('ready',{exact:true}).waitFor()
      await card.getByText(`Model: ${service}-model-v1 · Version: v1`,{exact:true}).waitFor()
      assert.ok(await card.getByText(/Endpoint:/).isVisible())
    }
    // Waits through a polling cycle and proves every check was called at least twice.
    await page.waitForTimeout(17000)
    for (const service of ['fraud','forecasting','recommendations']) {
      for (const kind of ['health','ready','metadata']) assert.ok(counts[`${service}/${kind}`] >= 2)
    }
    // Induce a failure only in this browser; do not alter a deployed service.
    // Returns 503 only to this browser for forecasting checks. It does not change the actual
    // deployed service.
    await page.route('**/api/forecasting/health', route => route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Browser-test simulated service failure'})}))
    await page.route('**/api/forecasting/ready', route => route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Browser-test simulated service failure'})}))
    await page.getByRole('button',{name:'Refresh status',exact:true}).click()
    const failed = page.getByRole('article',{name:'Forecasting operations'})
    await failed.getByText('Unavailable',{exact:true}).first().waitFor()
    const fraud = page.getByRole('article',{name:'Fraud detection operations'})
    await fraud.getByText('healthy',{exact:true}).waitFor()
    await fraud.getByText('ready',{exact:true}).waitFor()
    // Enters a known fraud sample and checks a real SageMaker fraud result while the simulated
    // outage remains visible.
    const form = page.locator('article').filter({has:page.getByRole('heading',{name:'Fraud detection',level:2})})
    await form.getByLabel('amount',{exact:true}).fill('1800')
    await form.getByLabel('transaction count',{exact:true}).fill('35')
    await form.getByLabel('account age days',{exact:true}).fill('12')
    await form.getByRole('button',{name:'Run prediction',exact:true}).click()
    await form.locator('pre').waitFor({timeout:95000})
    const prediction = JSON.parse(await form.locator('pre').innerText())
    assert.equal(prediction.provider,'sagemaker')
    assert.equal(prediction.prediction,'fraud')
    assert.ok(prediction.risk_score > 0.5)
    // Removes the simulated failures and verifies forecasting becomes healthy/ready again.
    await page.unroute('**/api/forecasting/health')
    await page.unroute('**/api/forecasting/ready')
    await page.getByRole('button',{name:'Refresh status',exact:true}).click()
    await failed.getByText('healthy',{exact:true}).waitFor()
    await failed.getByText('ready',{exact:true}).waitFor()
    // Optionally saves a screenshot and prints a JSON verification report.
    if (process.env.DASHBOARD_SCREENSHOT) await page.screenshot({path:process.env.DASHBOARD_SCREENSHOT,fullPage:true})
    console.log(JSON.stringify({verified_at:new Date().toISOString(),metadata,poll_counts:counts,partial_failure_isolated:true,live_prediction_during_partial_failure:prediction,recovery_verified:true},null,2))
  // Closes the temporary browser even if an assertion fails.
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode=1 })
