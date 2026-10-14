const { chromium } = require('/opt/homeops/games/web/node_modules/playwright-core');
const { spawn } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

(async () => {
  const root = path.resolve(__dirname, '..');
  const output = path.join(root, 'results/prototype');
  fs.mkdirSync(output, {recursive:true});
  const save = '/tmp/city-prototype-browser.sqlite';
  for(const suffix of ['', '-wal', '-shm']) {try{fs.unlinkSync(save+suffix)}catch{}}
  const bridge = spawn('python3', [path.join(__dirname, 'prototype_bridge.py'), save], {stdio:['pipe','pipe','pipe']});
  const pending=[];
  const lines=readline.createInterface({input:bridge.stdout});
  lines.on('line', line => {const callback=pending.shift();if(callback) callback(JSON.parse(line));});
  bridge.stderr.on('data', d=>process.stderr.write(d));
  const send = data => new Promise(resolve=>{pending.push(resolve);bridge.stdin.write(JSON.stringify(data)+'\n');});
  let browser;
  try {
    browser = await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
    const context = await browser.newContext({viewport:{width:1360,height:950},reducedMotion:'reduce'});
    const errors=[];
    const page=await context.newPage();
    page.on('pageerror', error=>errors.push(error.message));
    await context.route('http://localhost:8092/**', async route => {
      const request=route.request();
      const data={path:new URL(request.url()).pathname,method:request.method(),headers:request.headers()};
      if(request.postData())data.payload=JSON.parse(request.postData());
      const result=await send(data);
      if(result.error)throw new Error(result.error);
      await route.fulfill({status:result.status,headers:result.headers,body:result.body});
    });
    await page.goto('http://localhost:8092/');
    await page.getByRole('button',{name:'M’installer',exact:true}).waitFor();
    await page.screenshot({path:path.join(output,'welcome-desktop.png'),fullPage:true});
    await page.getByRole('button',{name:'M’installer',exact:true}).click();
    await page.locator('[data-home="home_garden"]').click();
    await page.locator('[data-job="gardener"]').click();
    await page.getByText('Mon budget prévu',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Lendemain',exact:true}).click();
    await page.locator('#budget-details summary').click();
    await page.getByText('Dernière journée',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    await page.locator('[data-goal="garden"]').click();
    await page.getByRole('button',{name:'Rejoindre le lieu',exact:true}).click();
    await page.getByRole('button',{name:'Réaliser cet aménagement',exact:true}).waitFor({timeout:20000});
    await page.getByRole('button',{name:'Réaliser cet aménagement',exact:true}).click();
    await page.getByText('1 aménagement réalisé.',{exact:true}).waitFor();
    await page.screenshot({path:path.join(output,'play-desktop.png'),fullPage:true});
    const before = await page.evaluate(async()=>await(await fetch('/api/me')).json());
    await page.reload();
    await page.getByText('1 aménagement réalisé.',{exact:true}).waitFor();
    const after = await page.evaluate(async()=>await(await fetch('/api/me')).json());
    if(before.player.cash_cents!==after.player.cash_cents)throw new Error('Wallet changed during reload');
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(output,'play-mobile.png'),fullPage:true});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
    if(overflow)throw new Error('Horizontal overflow on mobile');
    if(errors.length)throw new Error(errors.join('\n'));
    fs.writeFileSync(path.join(output,'browser-qa.json'),JSON.stringify({transport:'real HTTP handler over byte streams; TCP bind unavailable',javascript_errors:errors,initial_required_choices:2,home:after.player.home,job:after.player.job,day:after.world.day,completed_goals:after.player.completed_goals,reload_preserved_wallet:true,mobile_horizontal_overflow:false},null,2));
    console.log('Browser QA passed');
  } finally {if(browser)await browser.close();bridge.stdin.end();}
})().catch(error=>{console.error(error);process.exitCode=1;});
