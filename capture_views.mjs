import puppeteer from 'puppeteer';
import path from 'path';
import fs from 'fs';

const BASE_URL = 'http://127.0.0.1:8080';
const OUT_DIR = '/root/LojistikGirisimleri/ramparandevu/screenshots';
const ARTIFACT_DIR = '/root/.gemini/antigravity-cli/brain/6fbd61d9-b701-402c-8edc-34e4710e9e9a/screenshots';

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

async function saveAndCopy(page, filename) {
  const filePath = path.join(OUT_DIR, filename);
  const artifactPath = path.join(ARTIFACT_DIR, filename);
  await page.screenshot({ path: filePath, fullPage: false });
  fs.copyFileSync(filePath, artifactPath);
  console.log(`Saved screenshot: ${filename}`);
}

async function run() {
  console.log('Starting Puppeteer Capture Suite...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  try {
    const page = await browser.newPage();

    // 1. Desktop 1920x1080 - Cockpit Cards View
    console.log('1. Capturing Cockpit Cards View...');
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));
    await saveAndCopy(page, '01_cockpit_cards.png');

    // 2. Desktop 1920x1080 - Cockpit Gantt Timeline View
    console.log('2. Capturing Cockpit Gantt View...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const ganttBtn = btns.find(b => b.textContent && b.textContent.trim().includes('Gantt'));
      if (ganttBtn) ganttBtn.click();
    });
    await new Promise(r => setTimeout(r, 1500));
    await saveAndCopy(page, '02_cockpit_gantt.png');

    // 3. Desktop 1920x1080 - Cockpit Table View
    console.log('3. Capturing Cockpit Table View...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const tableBtn = btns.find(b => b.textContent && b.textContent.trim().includes('Tablo'));
      if (tableBtn) tableBtn.click();
    });
    await new Promise(r => setTimeout(r, 1500));
    await saveAndCopy(page, '03_cockpit_table.png');

    // 4. Desktop 1920x1080 - Booking Wizard Modal
    console.log('4. Capturing Booking Wizard Modal...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const bookBtn = btns.find(b => b.textContent && b.textContent.trim().includes('Randevu Al'));
      if (bookBtn) bookBtn.click();
    });
    await new Promise(r => setTimeout(r, 1500));
    await saveAndCopy(page, '04_booking_wizard.png');

    // Close Booking Modal
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const closeBtn = btns.find(b => (b.textContent && (b.textContent.includes('Vazgeç') || b.textContent.includes('İptal'))) || b.textContent === '✕');
      if (closeBtn) closeBtn.click();
    });
    await new Promise(r => setTimeout(r, 1000));

    // 5. Tablet 1280x800 - Nizamiye Gate View
    console.log('5. Capturing Nizamiye Gate Tablet View...');
    await page.setViewport({ width: 1280, height: 800, deviceScaleFactor: 1 });
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('header button'));
      const gateBtn = btns.find(b => b.textContent && b.textContent.includes('Nizamiye'));
      if (gateBtn) gateBtn.click();
    });
    await new Promise(r => setTimeout(r, 2000));
    await saveAndCopy(page, '05_gate_tablet.png');

    // 6. Mobile 412x915 - Driver Mobile View
    console.log('6. Capturing Driver Mobile View...');
    await page.setViewport({ width: 412, height: 915, isMobile: true, hasTouch: true });
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('header button'));
      const driverBtn = btns.find(b => b.textContent && b.textContent.includes('Şoför Ekranı'));
      if (driverBtn) driverBtn.click();
    });
    await new Promise(r => setTimeout(r, 2000));
    await saveAndCopy(page, '06_driver_mobile.png');

    // 7. Desktop 1920x1080 - DocuLog Split-Screen Goods Receipt Modal
    console.log('7. Capturing DocuLog Acceptance Modal...');
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('header button'));
      const cockpitBtn = btns.find(b => b.textContent && b.textContent.includes('Rampa Kokpiti'));
      if (cockpitBtn) cockpitBtn.click();
    });
    await new Promise(r => setTimeout(r, 1500));
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const cardsBtn = btns.find(b => b.textContent && b.textContent.trim().includes('Kartlar'));
      if (cardsBtn) cardsBtn.click();
    });
    await new Promise(r => setTimeout(r, 1000));

    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const doculogBtn = btns.find(b => b.textContent && b.textContent.includes('DocuLog Mal Kabul İncele'));
      if (doculogBtn) doculogBtn.click();
    });
    await new Promise(r => setTimeout(r, 2500));
    await saveAndCopy(page, '07_doculog_split_screen.png');

    console.log('Successfully captured all views!');
  } catch (err) {
    console.error('Error occurred in capture:', err);
  } finally {
    await browser.close();
  }
}

run();
