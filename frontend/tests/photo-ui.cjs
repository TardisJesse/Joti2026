const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const photo = 'data:image/png;base64,' + fs.readFileSync(path.join(__dirname, 'team-photo.png')).toString('base64')
async function run() {
  const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined, headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, geolocation: { latitude: 51.9, longitude: 4.3 }, permissions: ['geolocation'] })
    const errors = [], calls = []
    page.on('pageerror', error => errors.push(error.message))
    let portrait = null, submitted = false, admin = false
    const user = () => ({ id: 'user', name: 'team-internal-id', team_id: 'one', team_name: 'Valken', game_id: 'game', role: 'TEAM_LEADER', profile_image: portrait })
    const objects = [{ id: 'photo', name: 'Teamfoto bij HQ', type: 'PHOTO_POINT', latitude: 51.9, longitude: 4.3, activation_radius_meters: 40 }, { id: 'tower', name: 'Radiopost', type: 'CAPTURE_POINT', latitude: 51.901, longitude: 4.3, activation_radius_meters: 40, points_per_minute: 1 }]
    await page.route('https://**/*', route => route.request().url().includes('openfreemap.org/styles') ? route.fulfill({ json: { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#10283b' } }] } }) : route.abort())
    await page.route('**/api/**', async route => {
      const request = route.request(), endpoint = new URL(request.url()).pathname
      calls.push([endpoint, request.method()])
      let result = {}
      if (endpoint === '/api/games/join') result = { access_token: 'test', user: user() }
      if (endpoint === '/api/auth/login') { admin = true; result = { access_token: 'admin-test', user: { id: 'admin', name: 'admin', role: 'ADMIN', team_id: null } } }
      if (endpoint === '/api/admin/games') result = [{ id: 'game', code: 'RONDE-A', name: 'Round', status: 'RUNNING' }]
      if (endpoint === '/api/game') result = { id: 'game', code: 'RONDE-A', name: 'Round', status: 'RUNNING', ends_at: null, timer_remaining_seconds: null, server_now: new Date().toISOString() }
      if (endpoint === '/api/auth/me') result = user()
      if (endpoint === '/api/game-objects') result = objects
      if (endpoint === '/api/scores') result = [
        { team_id: 'two', name: 'Arenden', score: 40, color: '#ffcf6a', profile_image: photo },
        { team_id: 'one', name: 'Valken', score: 30, color: '#00dff2', profile_image: portrait },
        { team_id: 'three', name: 'Sperwers', score: 20, color: '#bb99ff', profile_image: photo },
        { team_id: 'four', name: 'Uilen', score: 10, color: '#66ff99', profile_image: photo },
        { team_id: 'five', name: 'Merels', score: 0, color: '#ff6688' },
      ]
      if (endpoint === '/api/locations') result = admin ? [
        { player_id: 'user', name: 'team-internal-id', team_id: 'one', team_name: 'Valken', profile_image: portrait, location: { lat: 51.9428, lng: 4.3553 } },
        { player_id: 'other', name: 'team-other-id', team_id: 'two', team_name: 'Arenden', profile_image: photo, location: { lat: 51.9435, lng: 4.3558 } },
      ] : [{ player_id: 'user', team_id: 'one', team_name: 'Valken', profile_image: portrait, location: { lat: 51.9, lng: 4.3 } }]
      if (endpoint === '/api/profile/image') { portrait = request.postDataJSON().image; result = user() }
      if (endpoint === '/api/photos/photo') {
        if (request.method() === 'POST') { assert.ok(request.postDataJSON().image.startsWith('data:image/jpeg;base64,')); submitted = true; result = { points: 50 } }
        else result = { submitted, photos: submitted ? [{ id: 'submission', team_name: 'Valken', image: photo }] : [], reward_points: 50 }
      }
      await route.fulfill({ json: result })
    })
    await page.goto('http://127.0.0.1:5179')
    await page.getByLabel('TEAMNAAM', { exact: true }).fill('Valken')
    await page.getByRole('button', { name: 'DOE MEE MET SPEL' }).click()
    await page.locator('.field-radar').waitFor()
    assert.equal(await page.locator('.profile-editor').count(), 0, 'No photo editor above the map')
    await page.locator('nav button').filter({ hasText: 'Scoreboard' }).click()
    await page.locator('.profile-plus').waitFor()
    assert.equal(await page.locator('.profile-plus').textContent(), '+', 'Empty profile photo uses a plus')
    await page.screenshot({ path: path.join(__dirname, 'scoreboard-empty-profile-mobile.png'), fullPage: true })
    await page.locator('.profile-editor input').setInputFiles(path.join(__dirname, 'team-photo.png'))
    await page.locator('.profile-editor img').waitFor()
    await page.locator('.podium-place').first().waitFor()
    assert.equal(await page.locator('.podium-place').count(), 3)
    assert.equal(await page.locator('.place-1 h2').textContent(), 'Arenden')
    assert.equal(await page.locator('.place-2 h2').textContent(), 'Valken')
    assert.equal(await page.locator('.rank-list li').count(), 2)
    assert.ok((await page.locator('.rank-list li').first().textContent()).includes('#4'))
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Mobile page must not overflow')
    await page.screenshot({ path: path.join(__dirname, 'scoreboard-mobile.png'), fullPage: true })
    await page.getByRole('button', { name: 'Radar kaart' }).click()
    await page.locator('.is-current-player img').waitFor()
    assert.equal(await page.locator('.profile-editor').count(), 0, 'Editor stays exclusive to scoreboard')
    assert.equal(await page.locator('.is-current-player').getAttribute('aria-label'), 'Valken')
    await page.getByRole('button', { name: /2 spelpunten/ }).click()
    await page.locator('.point-row').filter({ hasText: 'Teamfoto bij HQ' }).click()
    await page.getByRole('button', { name: 'Open fotopunt' }).click()
    await page.locator('.game-dialog input[type=file]').setInputFiles(path.join(__dirname, 'team-photo.png'))
    await page.locator('.photo-preview').waitFor()
    await page.getByRole('button', { name: 'Teamfoto insturen' }).click()
    await page.locator('.photo-gallery figure').waitFor()
    assert.ok((await page.locator('.dialog-result').textContent()).includes('+50'))
    await page.screenshot({ path: path.join(__dirname, 'photo-dialog-mobile.png'), fullPage: true })
    await page.getByRole('button', { name: 'Sluiten', exact: true }).click()
    await page.locator('nav button').filter({ hasText: 'Scoreboard' }).click()
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.screenshot({ path: path.join(__dirname, 'scoreboard-desktop.png'), fullPage: true })
    await page.getByRole('button', { name: 'Uitloggen', exact: true }).click()
    await page.getByRole('button', { name: 'ADMIN LOGIN', exact: true }).click()
    await page.getByLabel('WACHTWOORD').fill('admin-test')
    await page.getByRole('button', { name: 'INLOGGEN ALS ADMIN', exact: true }).click()
    await page.getByRole('button', { name: 'Radar kaart' }).click()
    await page.locator('.player-pin img').first().waitFor()
    assert.equal(await page.locator('.player-pin img').count(), 2, 'Admins see all player photos')
    await page.locator('.player-pin[title="Arenden"]').click()
    const popupText = await page.locator('.maplibregl-popup-content').textContent()
    assert.ok(popupText.includes('Arenden') && !popupText.includes('team-other-id'), 'Marker popup shows team name')
    assert.deepEqual(errors, [])
    console.log('Browser checks passed: joining, profile upload, photo marker, podium, ranking, photo submit/gallery, mobile width, admin portraits/popups, and no JavaScript errors.')
  } finally { await browser.close() }
}
run().catch(error => { console.error(error); process.exitCode = 1 })
