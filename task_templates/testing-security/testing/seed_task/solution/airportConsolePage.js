class AirportConsolePage {
  constructor(page) {
    this.page = page;
    this.searchInput = page.getByTestId('search-input');
    this.countrySelect = page.getByTestId('country-select');
    this.minRunwayInput = page.getByTestId('min-runway-input');
    this.applyButton = page.getByTestId('apply-filters');
    this.exportButton = page.getByTestId('export-button');
    this.compareButton = page.getByTestId('show-compare');
    this.count = page.getByTestId('airport-count');
    this.rows = page.getByTestId('airport-row');
    this.detailPanel = page.getByTestId('detail-panel');
    this.comparePanel = page.getByTestId('compare-panel');
    this.insightsPanel = page.getByTestId('insights-panel');
    this.insightsBody = page.getByTestId('insights-body');
    this.insightsSkeleton = page.getByTestId('insights-skeleton');
  }

  async goto() {
    await this.page.goto('/');
    await this.page.getByRole('heading', { name: 'Airport Ops Console' }).waitFor();
    await this.count.waitFor();
  }

  async waitForRows(count) {
    await this.page.waitForFunction(
      ([selector, expected]) => document.querySelectorAll(selector).length === expected,
      ['[data-testid="airport-row"]', count]
    );
  }

  rowFor(ident) {
    return this.page.locator(`[data-testid="airport-row"][data-ident="${ident}"]`);
  }

  async search(query) {
    await this.searchInput.fill(query);
    await this.applyButton.click();
  }

  async applyCountryAndRunway(countryCode, runwayLength) {
    await this.countrySelect.selectOption(countryCode);
    await this.minRunwayInput.fill(String(runwayLength));
    await this.applyButton.click();
  }

  async clearFilters() {
    await this.page.getByTestId('clear-filters').click();
  }

  async openDetails(ident) {
    await this.rowFor(ident).getByRole('button', { name: 'Details' }).click();
    await this.detailPanel.waitFor();
  }

  async toggleCompare(ident) {
    await this.rowFor(ident).locator('[data-action="compare"]').click();
  }
}

module.exports = { AirportConsolePage };
