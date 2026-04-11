#!/usr/bin/env node
// Fetch full Lo Times articles using headless browser + Substack auth cookie
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const CREDS_PATH = path.join(__dirname, '..', 'credentials.json');

async function fetchArticle(url) {
  const creds = JSON.parse(fs.readFileSync(CREDS_PATH, 'utf-8'));
  const cookie = creds.lotimes?.cookies || '';
  
  // Parse substack.sid from cookie string
  const sidMatch = cookie.match(/substack\.sid=([^\s;]+)/);
  if (!sidMatch) {
    console.error('No substack.sid found in credentials.json');
    process.exit(1);
  }

  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
  });

  // Set the auth cookie
  await context.addCookies([
    {
      name: 'substack.sid',
      value: sidMatch[1],
      domain: '.substack.com',
      path: '/',
    },
    {
      name: 'substack.sid', 
      value: sidMatch[1],
      domain: '.thelotimes.com',
      path: '/',
    }
  ]);

  const page = await context.newPage();
  
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    
    // Wait for content to load
    await page.waitForTimeout(3000);
    
    // Extract the article body text
    const content = await page.evaluate(() => {
      const body = document.querySelector('.body.markup') || 
                   document.querySelector('.post-content') ||
                   document.querySelector('[class*="body"]');
      if (body) return body.innerText;
      
      // Fallback: get all paragraph text
      const paras = document.querySelectorAll('p');
      return Array.from(paras).map(p => p.innerText).join('\n\n');
    });
    
    // Check for paywall
    const hasPaywall = await page.evaluate(() => {
      return !!document.querySelector('.paywall') || 
             !!document.querySelector('[class*="paywall"]');
    });
    
    if (hasPaywall) {
      console.error('WARNING: Paywall detected — content may be truncated');
    }
    
    console.log(content);
  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await browser.close();
  }
}

const url = process.argv[2] || 'https://www.thelotimes.com/p/best-dishes-nyc-restaurants-2025-ryan-sutton';
fetchArticle(url);
