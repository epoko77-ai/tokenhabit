const { chromium } = require('playwright-core');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  for (const lang of ['en', 'ko']) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 640 }, deviceScaleFactor: 2 });
    await page.goto('file://' + path.resolve(__dirname, `thumb_${lang}.html`), { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500); // ensure web fonts settle
    const out = path.resolve(__dirname, `../../assets/thumbnail_${lang}.png`);
    await page.screenshot({ path: out });
    await page.close();
    console.log('shot', lang, '→', out);
  }
  await browser.close();
})();
