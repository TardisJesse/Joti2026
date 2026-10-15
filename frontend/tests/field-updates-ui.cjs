const assert = require('node:assert/strict')
const { chromium } = require('playwright')
;(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('https://**/*', route => route.request().url().includes('openfreemap.org/styles') ? route.fulfill({ json: { version: 8, sources: {}, layers: [] } }) : route.abort())
    await page.route('**/api/**', async route => {
      const endpoint = new URL(route.request().url()).pathname
      let json = []
      if (endpoint === '/api/games/join') json = { access_token: 'test', user: { id: 'player', name: 'Player', team_id: 'one', team_name: 'Valken', game_id: 'game', role: 'TEAM_LEADER' } }
      if (endpoint === '/api/game') json = { id: 'game', status: 'RUNNING', play_area: { type: 'Polygon', coordinates: [[[4.35,51.94],[4.36,51.94],[4.36,51.946],[4.35,51.946],[4.35,51.94]]] } }
      if (endpoint === '/api/game-objects') json = [
        ...['PUZZLE', 'PHOTO_POINT', 'PHYSICAL_DUCK'].map((type, index) => ({ id: type, type, name: ['Puzzel', 'Foto', 'Eendje'][index], completed: true, latitude: 51.943 + index * .001, longitude: 4.355, activation_radius_meters: 40 })),
        { id: 'unfinished', type: 'PUZZLE', name: 'Nog te doen', completed: false, latitude: 51.942, longitude: 4.358, activation_radius_meters: 40 },
      ]
      await route.fulfill({ json })
    })
    await page.goto('http://127.0.0.1:5179')
    const install = page.getByRole('button', { name: '＋ Installeer als app' })
    assert.equal(await install.count(), 1)
    const actions = await page.locator('.home-actions > button').first().boundingBox()
    assert.ok(actions)
    await install.click()
    await page.getByRole('dialog', { name: 'CyberJoti installeren' }).waitFor()
    assert.ok(await page.getByText(/iPhone of iPad:/).isVisible())
    await page.getByRole('button', { name: 'Sluiten', exact: true }).click()
    await page.evaluate(() => {
      window.installPromptCalls = 0
      const event = new Event('beforeinstallprompt', { cancelable: true })
      event.prompt = async () => { window.installPromptCalls++ }
      event.userChoice = Promise.resolve({ outcome: 'dismissed' })
      window.dispatchEvent(event)
    })
    await install.click()
    assert.equal(await page.evaluate(() => window.installPromptCalls), 1)
    await page.getByLabel('TEAMNAAM', { exact: true }).fill('Valken')
    await page.getByRole('button', { name: /START OF HERVAT/ }).click()
    await page.locator('.map-pin.is-completed').first().waitFor()
    assert.equal(await page.locator('.map-pin.is-completed').count(), 3)
    const fog = page.locator('.map-area-fog')
    await fog.waitFor()
    const firstMask = await fog.evaluate(el => el.style.maskImage)
    assert.match(firstMask, /radial-gradient\(circle at/)
    assert.match(await fog.evaluate(el => getComputedStyle(el).backdropFilter), /blur\(7px\)/)
    assert.equal(await fog.evaluate(el => getComputedStyle(el).pointerEvents), 'none')
    await page.locator('.maplibregl-ctrl-zoom-out').click({ clickCount: 2, delay: 400 })
    await page.waitForTimeout(700)
    assert.notEqual(await fog.evaluate(el => el.style.maskImage), firstMask)
    await page.screenshot({ path: '../.runtime/map-fog-mobile.png' })
    await page.locator('.maplibregl-ctrl-zoom-in').click({ clickCount: 2, delay: 400 })
    await page.waitForTimeout(700)
    assert.equal(await page.locator('.completion-check').count(), 3)
    assert.equal(await page.locator('.map-pin.is-completed').first().evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(89, 99, 109)')
    assert.equal(await page.locator('.map-pin:not(.is-completed)').count(), 1)
    await page.getByRole('button', { name: 'Puzzel · Voltooid door jouw team', exact: true }).click()
    await page.getByText('✓ Voltooid door jouw team', { exact: true }).waitFor()
    await page.screenshot({ path: '../.runtime/field-updates-mobile.png' })
    assert.deepEqual(errors, [])
    console.log('Field updates UI passed: native install, iPhone instructions, completed markers and selected-point status and circular fading map on mobile.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
