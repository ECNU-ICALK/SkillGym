const { test, expect } = require('@playwright/test');

test.describe('Airport Ops Console visual stability', () => {
  test('loads the dashboard shell', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Airport Ops Console' })).toBeVisible();
    await expect(page.getByTestId('airport-count')).toContainText('12 airports');
  });

  test('coverage is incomplete and must be expanded', async () => {
    throw new Error(
      'Add browser coverage for saved-theme first paint, layout stability, and one core airport flow.'
    );
  });
});
