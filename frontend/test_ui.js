const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => console.log(`BROWSER CONSOLE: ${msg.text()}`));

  await page.goto('http://localhost:3000/sign-in');
  await page.fill('input[type="email"]', 'user_a_1234@gmail.com');
  await page.fill('input[type="password"]', 'password123!');
  await page.click('button[type="submit"]');

  await page.waitForURL('http://localhost:3000/spaces');
  
  await page.click('text=User A Space');
  await page.click('h3.text-lg.font-semibold');
  
  await page.waitForSelector('h2:has-text("Materials")');

  await page.setInputFiles('input[type="file"]', path.resolve('test_real.pdf'));
  await page.click('button[type="submit"]:has-text("Upload Material")');

  await page.waitForTimeout(10000);

  await browser.close();
})();
