#!/usr/bin/env node
// Fetch Lo Times articles by logging in via Substack's login flow
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const CREDS_PATH = path.join(__dirname, '..', 'credentials.json');

async function fetchArticle(url) {
  const creds = JSON.parse(fs.readFileSync(CREDS_PATH, 'utf-8'));
  const email = creds.lotimes?.email;
  const password = creds.lotimes?.password;
  
  if (!email || !password) {
    console.error('Need lotimes.email and lotimes.password in credentials.json');
    process.exit(1);
  }

  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
  });

  const page = await context.newPage();
  
  try {
    // Go to Substack login
    await page.goto('https://substack.com/sign-in', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    
    // Enter email
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.click('button:has-text("Continue"), button[type="submit"]');
    await page.waitForTimeout(2000);
    
    // Enter password
    await page.fill('input[type="password"]', password);
    await page.click('button:has-text("Sign in"), button:has-text("Log in"), button[type="submit"]');
    await page.waitForTimeout(5000);
    
    // Now navigate to the article
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    
    // Extract content
    const content = await page.evaluate(() => {
      const body = document.querySelector('.body.markup') || 
                   document.querySelector('.post-content') ||
                   document.querySelector('[class*="body"]');
      if (body) return body.innerText;
      const paras = document.querySelectorAll('p');
      return Array.from(paras).map(p => p.innerText).join('\n\n');
    });
    
    const hasPaywall = await page.evaluate(() => {
      return !!document.querySelector('.paywall') || 
             !!document.querySelector('[class*="paywall"]');
    });
    
    if (hasPaywall) console.error('WARNING: Still paywalled after login');
    else console.error('SUCCESS: Full content accessed');
    
    console.log(content);
  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await browser.close();
  }
}

const url = process.argv[2] || 'https://www.thelotimes.com/p/best-dishes-nyc-restaurants-2025-ryan-sutton';
fetchArticle(url);
