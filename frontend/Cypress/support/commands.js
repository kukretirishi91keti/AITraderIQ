// ================================================================
// cypress/support/commands.js
// TraderAI Pro v5.8.4 - Custom Cypress Commands
// ================================================================

// ============================================================
// NAVIGATION COMMANDS
// ============================================================

Cypress.Commands.add('visitDashboard', () => {
  cy.visit('/');
  cy.get('body', { timeout: 15000 }).should('be.visible');
  cy.contains('TraderAI Pro', { timeout: 10000 }).should('be.visible');
});

Cypress.Commands.add('selectMarket', (marketName) => {
  cy.contains('button', marketName).click();
  cy.wait(500);
});

Cypress.Commands.add('searchSymbol', (symbol) => {
  cy.get('input[placeholder*="Search"]').clear().type(symbol);
  cy.wait(300);
});

Cypress.Commands.add('selectSymbol', (symbol) => {
  cy.searchSymbol(symbol);
  cy.get('input[placeholder*="Search"]').type('{enter}');
  cy.wait(500);
});

Cypress.Commands.add('selectFromWatchlist', (symbol) => {
  cy.contains('WATCHLIST').parent().contains(symbol).click();
  cy.wait(500);
});

// ============================================================
// INTERVAL COMMANDS (v5.8.4)
// ============================================================

Cypress.Commands.add('selectInterval', (interval) => {
  const intervalMap = {
    '1m': '1M',
    '5m': '5M', 
    '15m': '15M',
    '1h': '1H',
    '1d': '1D',
    '1wk': '1WK'
  };
  const btn = intervalMap[interval.toLowerCase()] || interval.toUpperCase();
  cy.contains('button', btn).click();
  cy.wait(500);
});

Cypress.Commands.add('verifyChartLoaded', () => {
  cy.get('svg polyline', { timeout: 5000 }).should('exist');
});

// ============================================================
// MODAL COMMANDS
// ============================================================

Cypress.Commands.add('openScreener', () => {
  cy.contains('button', 'Screener').click();
  cy.wait(500);
});

Cypress.Commands.add('openPortfolio', () => {
  cy.contains('button', 'Portfolio').click();
  cy.wait(300);
});

Cypress.Commands.add('openAlerts', () => {
  cy.contains('button', 'Alerts').click();
  cy.wait(300);
});

Cypress.Commands.add('openGuide', () => {
  cy.contains('button', 'Guide').click();
  cy.wait(300);
});

Cypress.Commands.add('openWhatsNext', () => {
  cy.contains("What's Next").click();
  cy.wait(300);
});

Cypress.Commands.add('closeModal', () => {
  cy.get('body').type('{esc}');
  cy.wait(200);
});

// ============================================================
// WATCHLIST COMMANDS
// ============================================================

Cypress.Commands.add('openWatchlistEdit', () => {
  cy.contains('Edit').click();
  cy.contains('Edit Watchlist').should('be.visible');
});

Cypress.Commands.add('addToWatchlist', (symbol) => {
  cy.openWatchlistEdit();
  cy.get('input[placeholder*="Add symbol"]').type(symbol);
  cy.contains('button', 'Add').click();
  cy.contains('button', 'Done').click();
});

Cypress.Commands.add('toggleWatch', () => {
  cy.get('button').contains(/Watch|Watching/).click();
});

// ============================================================
// TAB COMMANDS
// ============================================================

Cypress.Commands.add('switchTab', (tabName) => {
  cy.contains('button', tabName.toLowerCase()).click();
  cy.wait(300);
});

// ============================================================
// AI ASSISTANT COMMANDS
// ============================================================

Cypress.Commands.add('askAI', (question) => {
  cy.get('input[placeholder*="Ask about"]').type(question);
  cy.contains('button', 'Send').click();
  cy.wait(1000);
});

Cypress.Commands.add('clickQuickQuestion', (index = 0) => {
  cy.get('button').contains(/entry point|support|Risk/).eq(index).click();
  cy.wait(1000);
});

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================

Cypress.Commands.add('pressKey', (key) => {
  cy.get('body').type(key);
});

Cypress.Commands.add('pressEscape', () => {
  cy.get('body').type('{esc}');
});

// ============================================================
// VERIFICATION COMMANDS
// ============================================================

Cypress.Commands.add('verifySymbolLoaded', (symbol) => {
  cy.contains(symbol).should('be.visible');
});

Cypress.Commands.add('verifyCurrency', (currency) => {
  cy.contains(currency).should('be.visible');
});

Cypress.Commands.add('verifyTopMoversLoaded', () => {
  cy.contains('TOP MOVERS').should('be.visible');
  cy.get('aside').should('contain.text', '%');
});

Cypress.Commands.add('verifyVersion', (version) => {
  cy.contains(`v${version}`).should('be.visible');
});

// ============================================================
// SCREENER COMMANDS
// ============================================================

Cypress.Commands.add('filterScreener', (filter) => {
  const filters = {
    'all': 'All',
    'oversold': 'RSI < 30',
    'overbought': 'RSI > 70',
    'buy': 'Buy Signal'
  };
  cy.contains('button', filters[filter] || filter).click();
  cy.wait(300);
});

Cypress.Commands.add('selectScreenerCategory', (category) => {
  cy.get('select').select(category);
  cy.wait(300);
});

// ============================================================
// UTILITY COMMANDS
// ============================================================

Cypress.Commands.add('waitForDataLoad', () => {
  cy.get('svg polyline', { timeout: 10000 }).should('exist');
  cy.contains(/Last:/).should('be.visible');
});

Cypress.Commands.add('getLastFetchTime', () => {
  return cy.contains(/Last:/).invoke('text');
});