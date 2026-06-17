const { test, expect } = require('@playwright/test');
const fs = require('fs/promises');
const { AirportConsolePage } = require('../pages/airportConsolePage');

function metricsByName(metricRows) {
  const metrics = {};

  for (const row of metricRows) {
    metrics[row.name] = row.value;
  }

  return metrics;
}

async function topInDocument(locator) {
  return locator.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return rect.top + window.scrollY;
  });
}

async function rectFor(locator) {
  return locator.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
    };
  });
}

async function detailFields(panel) {
  return panel.evaluate((root) => {
    const values = {};

    for (const row of root.querySelectorAll('dl > div')) {
      const term = row.querySelector('dt');
      const description = row.querySelector('dd');
      values[term.textContent] = description.textContent;
    }

    return values;
  });
}

async function compareLines(panel) {
  return panel.locator('p').allInnerTexts();
}

test.describe('Airport Ops Console visual stability', () => {
  test('loads the dashboard shell and keeps the saved dark theme from first visible paint', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'dark');
      window.__themeProbe = [];

      const record = (label) => {
        const overlay = getComputedStyle(document.documentElement, '::before');
        window.__themeProbe.push({
          label,
          theme: document.documentElement.dataset.theme || '',
          overlayContent: overlay.content,
          overlayPosition: overlay.position,
        });
      };

      requestAnimationFrame(() => {
        record('raf-1');
        requestAnimationFrame(() => record('raf-2'));
      });
    });

    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => {
      return Array.isArray(window.__themeProbe) && window.__themeProbe.some((sample) => sample.label === 'raf-2');
    });
    await expect(page.getByRole('heading', { name: 'Airport Ops Console' })).toBeVisible();
    const themeSamples = await page.evaluate(() => window.__themeProbe);

    expect(themeSamples).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          label: 'raf-1',
          theme: 'dark',
          overlayContent: 'none',
          overlayPosition: 'static',
        }),
        expect.objectContaining({
          label: 'raf-2',
          theme: 'dark',
          overlayContent: 'none',
          overlayPosition: 'static',
        }),
      ])
    );
    await expect(page.getByTestId('airport-count')).toContainText('12 airports');
  });

  test('keeps cumulative layout shift under control while delayed summary and compare content load', async ({ page }) => {
    const airportConsole = new AirportConsolePage(page);
    const client = await page.context().newCDPSession(page);
    const controls = page.locator('.controls');
    const contentGrid = page.locator('.content-grid');
    const insightsPanel = page.getByTestId('insights-panel');

    await client.send('Performance.enable');
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('results-summary-skeleton')).toBeVisible();
    const controlsBeforeSummary = await topInDocument(controls);
    const contentGridBeforeLoad = await rectFor(contentGrid);
    const insightsBeforeLoad = await rectFor(insightsPanel);
    await expect(page.getByTestId('results-summary-body')).toContainText('Runway balance summary');
    const controlsAfterSummary = await topInDocument(controls);
    const summaryShift = Math.abs(controlsAfterSummary - controlsBeforeSummary);

    await airportConsole.applyCountryAndRunway('US', 12000);
    await airportConsole.waitForRows(2);
    await airportConsole.toggleCompare('KJFK');
    await airportConsole.toggleCompare('KLAX');
    await expect(airportConsole.compareButton).toBeEnabled();
    await airportConsole.compareButton.click();
    await expect(airportConsole.comparePanel).toContainText('KJFK vs KLAX');
    await expect(airportConsole.insightsBody).toContainText('Runway staging brief');
    await page.waitForTimeout(1000);
    const contentGridAfterLoad = await rectFor(contentGrid);
    const insightsAfterLoad = await rectFor(insightsPanel);

    const perfMetrics = await client.send('Performance.getMetrics');
    const metrics = metricsByName(perfMetrics.metrics);

    expect(summaryShift).toBeLessThan(20);
    expect(Math.abs(contentGridAfterLoad.x - contentGridBeforeLoad.x)).toBeLessThan(8);
    expect(Math.abs(insightsAfterLoad.x - insightsBeforeLoad.x)).toBeLessThan(8);
    expect(Math.abs(insightsAfterLoad.width - insightsBeforeLoad.width)).toBeLessThan(12);
    expect(metrics.CumulativeLayoutShift || 0).toBeLessThan(0.02);
  });

  test('still covers a core airport detail flow', async ({ page }) => {
    const airportConsole = new AirportConsolePage(page);

    await airportConsole.goto();
    await airportConsole.search('JFK');
    await airportConsole.waitForRows(1);
    await airportConsole.openDetails('KJFK');
    expect(await detailFields(airportConsole.detailPanel)).toEqual({
      Airport: 'John F. Kennedy International Airport',
      Code: 'KJFK / JFK',
      Country: 'United States',
      Region: 'New York',
      City: 'New York',
      'Runway count': '4',
      'Shortest runway': '8,400 ft',
      'Longest runway': '14,511 ft',
      'Lighted runways': '4',
      'Scheduled service': 'Yes',
    });
  });

  test('exports the filtered United States compare view with the expected rows', async ({ page }) => {
    const airportConsole = new AirportConsolePage(page);

    await airportConsole.goto();
    await airportConsole.applyCountryAndRunway('US', 12000);
    await airportConsole.waitForRows(2);
    await airportConsole.toggleCompare('KJFK');
    await airportConsole.toggleCompare('KLAX');
    await expect(airportConsole.compareButton).toBeEnabled();
    await airportConsole.compareButton.click();
    await expect(airportConsole.comparePanel).toBeVisible();
    expect(await compareLines(airportConsole.comparePanel)).toEqual([
      'Pair: KJFK vs KLAX',
      'Left airport: John F. Kennedy International Airport (KJFK)',
      'Right airport: Los Angeles International Airport (KLAX)',
      'Longest runway difference: -1,617 ft',
      'Shortest runway difference: 526 ft',
      'Elevation difference: 112 ft',
    ]);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      airportConsole.exportButton.click(),
    ]);

    expect(download.suggestedFilename()).toBe('airport-export-us-12000.csv');
    const downloadPath = await download.path();
    expect(downloadPath).toBeTruthy();

    const csvText = await fs.readFile(downloadPath, 'utf8');
    expect(csvText).toContain('KJFK,JFK,John F. Kennedy International Airport,United States,New York,New York,4,8400,14511');
    expect(csvText).toContain('KLAX,LAX,Los Angeles International Airport,United States,California,Los Angeles,4,8926,12894');
  });
});
