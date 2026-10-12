const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

async function run() {
 const browser=await chromium.launch({channel:process.platform==='win32'?'msedge':undefined,headless:true,args:['--use-angle=swiftshader']})
 try {
  const context=await browser.newContext({viewport:{width:390,height:844},geolocation:{latitude:52,longitude:4,accuracy:10},permissions:['geolocation']})
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message))
  let socket, scannerCalls=0, paused=false, delayed=false, failScan=false, finishResponse
  const row={id:'news1',game_id:'game',created_at:new Date().toISOString(),kind:'CAPTURE_COMPLETED',team_name:'Valken',message:'Team Valken heeft de Noordmast veroverd!'}
  await page.addInitScript(()=>localStorage.setItem('cyberjoti-token','test'))
  await page.routeWebSocket('**/ws/game**',ws=>socket=ws)
  await page.route('https://**/*',r=>r.request().url().includes('openfreemap.org/styles')?r.fulfill({json:{version:8,sources:{},layers:[]}}):r.abort())
  await page.route('**/api/**',async r=>{
   const endpoint=new URL(r.request().url()).pathname
   let result={}
   if(endpoint==='/api/auth/me') result={id:'player',team_id:'own',game_id:'game',team_name:'Own',role:'TEAM_LEADER'}
   if(endpoint==='/api/game') result={id:'game',status:paused?'PAUSED':'RUNNING',server_now:new Date().toISOString()}
   if(endpoint==='/api/game-objects') result=[{id:'radar',name:'Geheime scanner',type:'SCANNER_POINT',latitude:52,longitude:4,activation_radius_meters:40,reward_points:null}]
   if(endpoint==='/api/locations') result=[]
   if(endpoint==='/api/scores') result=[{team_id:'own',name:'Own',color:'#00dff2',score:17}]
   if(endpoint==='/api/news') result=[row]
   if(endpoint==='/api/scanners/radar/locations') {
    scannerCalls++
    if(failScan) { await r.fulfill({status:403,json:{detail:'Buiten bereik'}});return }
    if(delayed) await new Promise(resolve=>finishResponse=resolve)
    result={server_now:new Date().toISOString(),locations:[{player_id:'other',team_id:'other',team_name:'Arenden',profile_image:'',location:{lat:52.0005,lng:4.001,accuracy:10,updated_at:new Date().toISOString()}}]}
   }
   await r.fulfill({json:result}).catch(()=>{})
  })
  await page.goto('http://127.0.0.1:5179');await page.locator('.map-pin.scanner_point').waitFor()
  await page.locator('.sheet-toggle').click(); await page.locator('.point-row').filter({hasText:'Geheime scanner'}).click()
  await page.getByRole('button',{name:'Scanner openen',exact:true}).click()
  await page.locator('.player-pin[aria-label="Arenden"]').waitFor()
  await page.getByRole('button',{name:'Scanner sluiten',exact:true}).click()
  assert.equal(await page.locator('.player-pin[aria-label="Arenden"]').count(),0)
  await page.getByRole('button',{name:'Scanner openen',exact:true}).click()
  await page.locator('.player-pin[aria-label="Arenden"]').waitFor()
  await page.waitForTimeout(5200);assert.ok(scannerCalls>=2,'Poll every five seconds')
  await page.screenshot({path:path.join(__dirname,'scanner-mobile.png'),fullPage:true})
  await context.setGeolocation({latitude:53,longitude:4,accuracy:10})
  await page.locator('.player-pin[aria-label="Arenden"]').waitFor({state:'detached'})
  assert.equal(await page.locator('.scanner-banner').count(),0)
  await context.setGeolocation({latitude:52,longitude:4,accuracy:10})
  await page.getByRole('button',{name:'Scanner openen',exact:true}).click();await page.locator('.scanner-banner').waitFor()
  paused=true;socket.send(JSON.stringify({type:'GAME_UPDATED',data:{id:'game',status:'PAUSED'}}))
  await page.locator('.scanner-banner').waitFor({state:'detached'})
  assert.equal(await page.locator('.player-pin[aria-label="Arenden"]').count(),0)
  paused=false;socket.send(JSON.stringify({type:'GAME_UPDATED',data:{id:'game',status:'RUNNING'}}))
  delayed=true;await page.getByRole('button',{name:'Scanner openen',exact:true}).click()
  await page.waitForFunction(()=>document.querySelector('.scanner-banner'))
  await page.waitForTimeout(100)
  await context.setGeolocation({latitude:53,longitude:4,accuracy:10})
  await page.locator('.scanner-banner').waitFor({state:'detached'})
  finishResponse?.();delayed=false;await page.waitForTimeout(150)
  assert.equal(await page.locator('.player-pin[aria-label="Arenden"]').count(),0,'Late responses cannot restore locations')
  await context.setGeolocation({latitude:52,longitude:4,accuracy:10})
  failScan=true;await page.getByRole('button',{name:'Scanner openen',exact:true}).click()
  await page.getByText('Buiten bereik',{exact:true}).waitFor()
  assert.equal(await page.locator('.player-pin[aria-label="Arenden"]').count(),0)
  failScan=false
  await page.locator('nav button').filter({hasText:'Dashboard'}).click()
  socket.send(JSON.stringify({type:'NEWS_EVENT',data:row}));socket.send(JSON.stringify({type:'NEWS_EVENT',data:row}))
  await page.locator('.news-feed li').waitFor();assert.equal(await page.locator('.news-feed li').count(),1)
  await page.getByRole('button',{name:'Speluitleg',exact:false}).click()
  const video=page.locator('.intro-dialog video')
  assert.equal(await video.getAttribute('autoplay'),null)
  await video.evaluate(e=>e.load())
  await page.waitForFunction(()=>document.querySelector('video').readyState>=1)
  assert.ok(Math.abs(await video.evaluate(e=>e.duration)-135)<.1)
  assert.equal(await video.locator('track').getAttribute('srclang'),'nl')
  await video.evaluate(e=>e.play());await page.waitForTimeout(300)
  await page.getByRole('button',{name:'Speluitleg sluiten'}).click();assert.equal(await video.evaluate(e=>e.paused),true)
  await page.getByRole('button',{name:'Speluitleg',exact:false}).click();await page.getByText('Speluitleg lezen',{exact:true}).click()
  await page.screenshot({path:path.join(__dirname,'intro-mobile.png'),fullPage:true})
  await page.getByRole('button',{name:'Speluitleg sluiten'}).click()
  await page.locator('nav button').filter({hasText:'Scoreboard'}).click()
  assert.match(await page.locator('.podium').innerText(),/VOLGERS/)
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
  assert.deepEqual(errors,[])
  console.log('News/scanner/video checks passed: scoped reveal, five-second polling, exit/pause clearing, deduplication, playable 135-second video, captions and mobile layout.')
 }finally{await browser.close()}
}
run().catch(error=>{console.error(error);process.exitCode=1})
