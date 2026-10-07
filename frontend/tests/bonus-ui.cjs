const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

async function run() {
  const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined, headless: true, args: ['--use-angle=swiftshader'] })
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'no-preference' })
    const errors = []; page.on('pageerror', error => errors.push(error.message))
    const user = { id: 'existing-player', name: 'team-internal', role: 'TEAM_LEADER', team_id: 'team', team_name: 'Valken', game_id: 'round' }
    const object = { id: 'tower', type: 'CAPTURE_POINT', name: 'Regenboogpost', latitude: 51.94, longitude: 4.35, activation_radius_meters: 40, points_per_minute: 1, bonus_active: true, bonus_multiplier: 2, bonus_cycle: 1, bonus_ends_at: new Date(Date.now() + 300000).toISOString() }
    let joins = 0
    await page.routeWebSocket('**/ws/game**', () => {})
    await page.route('https://**/*', route => route.request().url().includes('openfreemap.org/styles') ? route.fulfill({ json: { version: 8, sources: {}, layers: [] } }) : route.abort())
    await page.route('**/api/**', async route => {
      const endpoint = new URL(route.request().url()).pathname
      let result = {}
      if (endpoint === '/api/games/join') {
        assert.equal(route.request().postDataJSON().team_name, 'Valken'); joins++
        result = { access_token: 'same-account-token', user }
      }
      if (endpoint === '/api/auth/me') result = user
      if (endpoint === '/api/game') result = { id: 'round', status: 'RUNNING', server_now: new Date().toISOString() }
      if (endpoint === '/api/game-objects') result = [object]
      if (endpoint === '/api/locations') result = []
      if (endpoint === '/api/scores') result = [{ team_id: 'team', name: 'Valken', score: 42 }]
      await route.fulfill({ json: result })
    })
    await page.goto('http://127.0.0.1:5179')
    await page.getByLabel('TEAMNAAM', { exact: true }).fill('Valken')
    await page.getByRole('button', { name: 'START OF HERVAT JE TEAM' }).click()
    await page.locator('.bonus-location').waitFor()
    const ring = page.locator('.bonus-ring')
    assert.equal(await ring.evaluate(element => getComputedStyle(element).animationName), 'bonus-orbit')
    const before = await ring.evaluate(element => getComputedStyle(element).transform)
    await page.waitForTimeout(250)
    assert.notEqual(await ring.evaluate(element => getComputedStyle(element).transform), before, 'Rainbow border actually moves')
    await page.locator('.bonus-banner').click()
    await page.getByText('+2 punt(en) per minuut', { exact: false }).waitFor()
    await page.screenshot({ path: path.join(__dirname, 'bonus-mobile.png'), fullPage: true })
    await page.emulateMedia({ reducedMotion: 'reduce' })
    assert.equal(await ring.evaluate(element => getComputedStyle(element).animationName), 'none')
    await page.getByRole('button', { name: 'Uitloggen', exact: true }).click()
    await page.getByLabel('TEAMNAAM', { exact: true }).fill('Valken')
    await page.getByRole('button', { name: 'START OF HERVAT JE TEAM' }).click()
    await page.locator('.app').waitFor()
    await page.locator('nav button').filter({ hasText: 'Scoreboard' }).click()
    assert.equal(joins, 2)
    await page.getByText(/^42\s*PTS$/).waitFor()
    assert.deepEqual(errors, [])
    console.log('Bonus UI passed: moving rainbow, double-income details, reduced motion, logout and rejoin.')
  } finally { await browser.close() }
}
run().catch(error => { console.error(error); process.exitCode = 1 })
