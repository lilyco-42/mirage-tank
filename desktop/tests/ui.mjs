import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

if (process.env.GITHUB_ACTIONS !== 'true') throw Error('Browser acceptance only in GitHub Actions');
await fs.mkdir('evidence',{recursive:true});
const browser = await chromium.launch();
const receipts=[];
try {
  for (const [name,width,height] of [['desktop',1440,1000],['phone',390,844],['compact',320,740],['tablet',768,1024]]) {
    const page = await browser.newPage({viewport:{width,height}});
    const errors=[]; page.on('pageerror',error=>errors.push(error.message));
    try {
      await page.goto('http://127.0.0.1:8043/');
      await page.locator('#hidden').setInputFiles('tests/hidden.png');
      await page.locator('#surface').setInputFiles('tests/surface.png');
      await page.locator('#render').click();
      await page.locator('#status').filter({hasText:'处理完成'}).waitFor({timeout:30000});
      await page.waitForFunction(()=>[...document.querySelectorAll('#gallery img')].length===2&&[...document.querySelectorAll('#gallery img')].every(i=>i.naturalWidth===128));
      const realPreviews=await page.evaluate(async()=>{
        const images=[...document.querySelectorAll('#gallery img')];
        const bytes=new Uint8Array(await (await fetch(images[0].src)).arrayBuffer());
        const sample=background=>{const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;const c=canvas.getContext('2d');c.fillStyle=background;c.fillRect(0,0,128,128);c.drawImage(images[0],0,0);return [...c.getImageData(64,64,1,1).data]};
        return {samePng:images[0].src===images[1].src,signature:[...bytes.slice(0,8)],black:sample('black'),white:sample('white'),backgrounds:images.map(i=>getComputedStyle(i.parentElement).backgroundColor)};
      });
      assert(realPreviews.samePng); assert.deepEqual(realPreviews.signature,[137,80,78,71,13,10,26,10]);
      assert.deepEqual(realPreviews.backgrounds,['rgb(0, 0, 0)','rgb(255, 255, 255)']);
      assert.notDeepEqual(realPreviews.black,realPreviews.white);
      const exported=await page.evaluate(async()=>{const r=await fetch(document.querySelector('#downloadZip').href);const b=new Uint8Array(await r.arrayBuffer());return {status:r.status,zip:b[0]===80&&b[1]===75,size:b.length}});
      assert.equal(exported.status,200);assert(exported.zip&&exported.size>100);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      await page.screenshot({path:`evidence/${name}-dark.png`,fullPage:true});
      await page.getByRole('button',{name:'切换浅色外观'}).click();
      await page.screenshot({path:`evidence/${name}-light.png`,fullPage:true});
      await page.locator('#hiddenMax').fill('70');
      assert.equal(await page.locator('#gallery').count(),0,'changed parameters must not leave stale results');
      await page.locator('#render').click();
      await page.locator('#status').filter({hasText:'处理完成'}).waitFor();
      const finalUrl=await page.locator('#download').getAttribute('href');
      await page.locator('#delete').click();
      await page.locator('#status').filter({hasText:'工作区已删除'}).waitFor();
      assert.equal(await page.locator('#gallery').count(),0);
      assert.equal((await page.request.get('http://127.0.0.1:8043'+finalUrl)).status(),404);
      await page.locator('#hidden').setInputFiles({name:'broken.png',mimeType:'image/png',buffer:Buffer.from('invalid image')});
      await page.locator('#surface').setInputFiles('tests/surface.png');
      await page.locator('#render').click();
      await page.waitForFunction(()=>document.querySelector('#status').classList.contains('text-destructive'));
      await page.locator('#hidden').setInputFiles('tests/hidden.png');
      await page.locator('#render').click();
      await page.locator('#status').filter({hasText:'处理完成'}).waitFor();
      assert.deepEqual(errors,[]);
      receipts.push({name,width,height,realPreviews,realExport:true,adjustment:true,delete:true,invalidRetry:true,noOverflow:true});
    } catch(error) { await page.screenshot({path:`evidence/${name}-failure.png`,fullPage:true}).catch(()=>{});throw error; }
    finally { await page.close(); }
  }
  await fs.writeFile('evidence/browser.json',JSON.stringify({commit:process.env.GITHUB_SHA,receipts},null,2));
} finally { await browser.close(); }
