const assert=require('node:assert/strict')
const {chromium}=require('playwright')
async function run(){
  const browser=await chromium.launch({channel:process.platform==='win32'?'msedge':undefined,headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']})
  try{
    const page=await browser.newPage({viewport:{width:390,height:844},geolocation:{latitude:51.9428,longitude:4.3553},permissions:['geolocation']})
    const errors=[], claims=[];page.on('pageerror',e=>errors.push(e.message))
    let admin=false,loaded=false,removed=false,moved=false
    const duck=()=>({id:'duck3',type:'PHYSICAL_DUCK',name:'Eend 3 · De Kok',duck_number:3,latitude:51.9428,longitude:4.3553,activation_radius_meters:20,reward_points:50})
    const user=()=>({id:'user',name:admin?'admin':'Team',role:admin?'ADMIN':'TEAM_LEADER',team_id:admin?null:'team',team_name:'Team',game_id:'game'})
    const game=()=>({id:'game',code:'RONDE-A',name:'Ronde A',status:admin?'READY':'RUNNING'})
    await page.route('https://**/*',route=>route.request().url().includes('openfreemap.org/styles')?route.fulfill({json:{version:8,sources:{},layers:[{id:'bg',type:'background',paint:{'background-color':'#10283b'}}]}}):route.abort())
    await page.route('**/api/**',async route=>{
      const req=route.request(),endpoint=new URL(req.url()).pathname;let result={}
      if(endpoint==='/api/auth/me')result=user()
      if(endpoint==='/api/admin/games')result=[game()]
      if(endpoint==='/api/game')result=game()
      if(endpoint==='/api/game-objects')result=removed?[]:[duck()]
      if(endpoint==='/api/locations')result=[]
      if(endpoint==='/api/scores'||endpoint==='/api/news')result=[]
      if(endpoint==='/api/admin/ducks')result=Array.from({length:20},(_,i)=>({number:i+1,name:`Eend ${i+1}`,object_id:i===2&&!removed?'duck3':null}))
      if(endpoint==='/api/ducks/scan'){claims.push(req.postDataJSON());result={name:'Eend 3',points:50}}
      if(endpoint==='/api/admin/games/game/load-locations'){assert.equal(req.postDataJSON().layout,'A');loaded=true;result={objects:46,ducks:20}}
      if(endpoint==='/api/admin/game-objects/duck3/duck'){assert.equal(req.postDataJSON().duck_number,3);moved=true;result=duck()}
      await route.fulfill({json:result})
    })
    await page.addInitScript(()=>localStorage.setItem('cyberjoti-token','test'))
    await page.goto('http://127.0.0.1:5173');await page.getByRole('button',{name:/Dashboard/}).click()
    await page.getByRole('button',{name:'NFC SCANNER STARTEN'}).click()
    const dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:'SCAN NFC',exact:true}).click()
    await dialog.getByText('Deze browser ondersteunt geen NFC-scanner.',{exact:false}).waitFor()
    await dialog.getByLabel('Nummer op het eendje (1–20)').fill('3')
    await dialog.getByRole('button',{name:'Eendnummer controleren'}).click()
    await dialog.getByText('Eend 3 gevonden! +50 volgers').waitFor()
    assert.deepEqual(claims.pop(),{duck_number:3})
    await dialog.getByRole('button',{name:'Sluiten',exact:true}).click()
    // Fake only the device boundary; exercise real browser UI and submission.
    await page.evaluate(()=>{window.nfcAborted=false;window.NDEFReader=class{async scan({signal}){window.nfcReader=this;signal.addEventListener('abort',()=>window.nfcAborted=true)}}})
    await page.getByRole('button',{name:'NFC SCANNER STARTEN'}).click();await dialog.getByRole('button',{name:'SCAN NFC',exact:true}).click()
    await dialog.getByText('Houd je telefoon tegen de NFC-tag in het eendje.').waitFor()
    await page.evaluate(()=>window.nfcReader.onreading({serialNumber:'04:81:64:1c:46:02:89'}))
    await dialog.getByText('Eend 3 gevonden! +50 volgers').waitFor();assert.deepEqual(claims.pop(),{serial_number:'04:81:64:1c:46:02:89'})
    assert.equal(await page.evaluate(()=>window.nfcAborted),true)
    await dialog.getByRole('button',{name:'Sluiten',exact:true}).click()
    await page.getByRole('button',{name:'NFC SCANNER STARTEN'}).click();await dialog.getByRole('button',{name:'SCAN NFC',exact:true}).click();await page.keyboard.press('Escape')
    assert.equal(await page.evaluate(()=>window.nfcAborted),true)
    await page.evaluate(()=>{window.NDEFReader=class{async scan(){throw Object.assign(new Error('Denied'),{name:'NotAllowedError'})}}})
    await page.getByRole('button',{name:'NFC SCANNER STARTEN'}).click();await dialog.getByRole('button',{name:'SCAN NFC',exact:true}).click()
    await dialog.getByText('NFC-toestemming geweigerd.',{exact:false}).waitFor()
    await dialog.getByRole('button',{name:'Terug',exact:true}).click()
    admin=true;await page.reload();await page.getByRole('button',{name:/Beheer/}).click();await page.getByRole('button',{name:'OBJECTEN',exact:true}).click()
    await page.getByRole('button',{name:'Load locations · Ronde A',exact:true}).click()
    await page.getByText('46 standaardlocaties geladen, waaronder 20 eendjes.',{exact:false}).waitFor();assert.equal(loaded,true)
    const form=page.locator('#object-builder');await form.locator('select').first().selectOption('PHYSICAL_DUCK')
    assert.equal(await form.locator('option').filter({hasText:/^Eend 3$/}).count(),0)
    await page.getByRole('button',{name:'Aanpassen',exact:true}).click()
    assert.equal(await form.locator('select').nth(1).inputValue(),'3')
    assert.equal(await form.locator('option').filter({hasText:/^Eend 3$/}).count(),1)
    await form.getByLabel('LATITUDE',{exact:true}).fill('51.943')
    await form.getByRole('button',{name:'EENDLOCATIE OPSLAAN'}).click()
    await page.getByText('Eend 3 · De Kok is aangepast.',{exact:true}).waitFor();assert.equal(moved,true)
    assert.deepEqual(errors,[])
    console.log('Mobile duck UI passed: number-only backup, permission denial, UID scan, NFC abort, load locations, unused dropdown and move.')
  }finally{await browser.close()}
}
run().catch(e=>{console.error(e);process.exitCode=1})
