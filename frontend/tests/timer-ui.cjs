const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

async function run() {
  const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined, headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
  const sockets = [], errors = []
  let deadline = null, state = 'RUNNING', timerCalls = 0, pausedRemaining = null
  const game = () => {
    if (deadline && Date.now() >= Date.parse(deadline)) state = 'FINISHED'
    return { id: 'round', code: 'RONDE-A', name: 'Spelronde', status: state, ends_at: deadline, timer_remaining_seconds: pausedRemaining, server_now: new Date().toISOString() }
  }
  try {
    async function open(role) {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 }, geolocation: { latitude: 51.94, longitude: 4.35 }, permissions: ['geolocation'] })
      await context.addInitScript(role => localStorage.setItem('cyberjoti-token', role), role)
      const page = await context.newPage()
      page.on('pageerror', error => errors.push(error.message))
      await page.routeWebSocket('**/ws/game**', socket => { sockets.push(socket) })
      await page.route('https://**/*', route => route.request().url().includes('openfreemap.org/styles') ? route.fulfill({ json: { version: 8, sources: {}, layers: [] } }) : route.abort())
      await page.route('**/api/**', async route => {
        const request = route.request(), endpoint = new URL(request.url()).pathname
        let result = {}
        if (endpoint === '/api/auth/me') result = { id: role, name: role, role: role === 'admin' ? 'ADMIN' : 'TEAM_LEADER', team_id: role === 'admin' ? null : 'team', team_name: 'Valken', game_id: 'round' }
        if (endpoint === '/api/admin/games') result = [game()]
        if (endpoint === '/api/game') result = game()
        if (endpoint === '/api/scores') result = [{ team_id: 'team', name: 'Valken', color: '#00dff2', score: 0 }]
        if (endpoint === '/api/game-objects' || endpoint === '/api/locations') result = []
        if (endpoint === '/api/admin/games/round/timer') {
          assert.equal(role, 'admin')
          assert.equal(request.postDataJSON().duration_seconds, 60)
          // A short mocked deadline exercises zero without waiting a real minute.
          timerCalls++
          deadline = new Date(Date.now() + 3500).toISOString(); result = game()
          sockets.forEach(socket => socket.send(JSON.stringify({ type: 'GAME_UPDATED', data: result })))
        }
        await route.fulfill({ json: result })
      })
      await page.goto('http://127.0.0.1:5179')
      await page.locator('.app').waitFor()
      return page
    }
    const player = await open('player'), admin = await open('admin')
    assert.equal(await player.locator('nav button').filter({ hasText: 'Timer' }).count(), 0)
    assert.equal(await player.locator('.profile-editor').count(), 0)
    await admin.locator('nav button').filter({ hasText: 'Timer' }).click()
    await admin.getByLabel('Speeltijd in minuten').fill('1')
    await admin.getByRole('button', { name: 'Timer starten', exact: true }).click()
    await player.locator('.round-timer').waitFor()
    await admin.locator('.round-timer').waitFor()
    assert.equal(timerCalls, 1)
    assert.equal(await player.locator('.online-dot').count(), 0)
    const color = await player.locator('.round-timer').evaluate(element => getComputedStyle(element).color)
    assert.equal(color, 'rgb(255, 126, 135)', 'Timer is red')
    await admin.screenshot({ path: path.join(__dirname, 'timer-admin-mobile.png'), fullPage: true })
    await player.locator('.round-finished').waitFor({ timeout: 10000 })
    await admin.locator('.round-finished').waitFor({ timeout: 10000 })
    assert.equal(await player.locator('.round-timer').textContent(), '00:00')
    assert.equal(await admin.locator('.round-timer').textContent(), '00:00')
    assert.equal(await player.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    assert.equal(await admin.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    assert.ok((await admin.locator('nav').boundingBox()).height < 100, 'Admin tabs fit in one row')
    await player.screenshot({ path: path.join(__dirname, 'timer-finished-mobile.png'), fullPage: true })
    state = 'PAUSED'; deadline = null; pausedRemaining = 86400
    const paused = game()
    sockets.forEach(socket => socket.send(JSON.stringify({ type: 'GAME_UPDATED', data: paused })))
    await player.setViewportSize({ width: 320, height: 844 })
    await player.getByRole('timer').filter({ hasText: 'PAUZE' }).waitFor()
    assert.equal(await player.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Long paused timer fits small phones')
    assert.deepEqual(errors, [])
    console.log('Timer browser checks passed: admin tab, player visibility, shared red countdown, zero, finished state, and mobile layout.')
  } finally { await browser.close() }
}
run().catch(error => { console.error(error); process.exitCode = 1 })
