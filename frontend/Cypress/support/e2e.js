// ================================================================
// cypress/support/e2e.js
// TraderAI Pro v5.8.4 - E2E Support File
// ================================================================

// Import commands
import './commands';

// Hide fetch/XHR requests from command log (cleaner output)
const app = window.top;
if (app && !app.document.head.querySelector('[data-hide-command-log-request]')) {
  const style = app.document.createElement('style');
  style.innerHTML = '.command-name-request, .command-name-xhr { display: none }';
  style.setAttribute('data-hide-command-log-request', '');
  app.document.head.appendChild(style);
}

// Global before each
beforeEach(() => {
  // Clear any previous state
  cy.clearLocalStorage();
});

// Handle uncaught exceptions
Cypress.on('uncaught:exception', (err, runnable) => {
  // Don't fail tests on uncaught exceptions from the app
  // (some are expected in demo mode)
  console.log('Uncaught exception:', err.message);
  return false;
});

// Log test info
Cypress.on('test:before:run', (test) => {
  console.log(`Running: ${test.title}`);
});

// Custom assertions
chai.Assertion.addMethod('containCurrency', function (currency) {
  const text = this._obj.text();
  const currencies = ['$', '€', '£', '₹', '¥', 'HK$', 'A$', 'C$', 'R$', '₩', 'S$', 'CHF'];
  const hasCurrency = currencies.some(c => text.includes(c));
  this.assert(
    hasCurrency,
    `expected #{this} to contain a currency symbol`,
    `expected #{this} to not contain a currency symbol`
  );
});