#!/usr/bin/env node
/**
 * screenshot-site.js — headless screenshot via Playwright
 * Requires: LD_LIBRARY_PATH=/home/linuxbrew/.linuxbrew/lib (set automatically when run via npm)
 *
 * Usage:
 *   node screenshot-site.js [url] [output.png] [--wait 5000] [--width 1440] [--height 900]
 *   node screenshot-site.js http://localhost:3421 /tmp/preview.png --wait 5000
 */

process.env.LD_LIBRARY_PATH = [
  '/home/linuxbrew/.linuxbrew/lib',
  process.env.LD_LIBRARY_PATH || '',
].filter(Boolean).join(':');

const { chromium } = require('playwright');

const args   = process.argv.slice(2);
const url    = args.find(a => a.startsWith('http')) || 'http://localhost:3421';
const out    = args.find(a => a.endsWith('.png'))   || '/home/claw/.openclaw/workspace/jim-wtf-preview.png';
const width  = parseInt(args[args.indexOf('--width')  + 1] || '1440');
const height = parseInt(args[args.indexOf('--height') + 1] || '900');
const wait   = parseInt(args[args.indexOf('--wait')   + 1] || '5000');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page    = await browser.newPage();
  await page.setViewportSize({ width, height });

  console.log(`→ ${url}`);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  if (wait > 0) await page.waitForTimeout(wait);

  await page.screenshot({ path: out });
  console.log(`✓ ${out}`);
  await browser.close();
})().catch(err => { console.error('✗', err.message); process.exit(1); });
