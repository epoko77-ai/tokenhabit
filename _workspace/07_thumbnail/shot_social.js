// Renders the social share images. Square (1:1) for feed posts, wide (1.91:1)
// for link previews — Facebook crops a wide image hard in the feed, so the
// square one is what you attach to a post.
const { chromium } = require('playwright-core');
const path = require('path');

const TARGETS = [
  { file: 'social_ko.html',      out: 'social_ko_square.png', w: 1200, h: 1200 },
  { file: 'social_ko_wide.html', out: 'social_ko_wide.png',   w: 1200, h: 630  },
];

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  for (const t of TARGETS) {
    const src = path.resolve(__dirname, t.file);
    if (!require('fs').existsSync(src)) { console.log('skip', t.file); continue; }
    const page = await browser.newPage({
      viewport: { width: t.w, height: t.h },
      deviceScaleFactor: 2,
    });
    await page.goto('file://' + src, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500); // let web fonts settle
    const out = path.resolve(__dirname, `../../assets/${t.out}`);
    await page.screenshot({ path: out });
    await page.close();
    console.log('shot', t.out, '→', out);
  }
  await browser.close();
})();
