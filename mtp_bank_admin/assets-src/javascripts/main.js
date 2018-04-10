(function () {
  'use strict';
  require('polyfills').Polyfills.init();

  require('proposition-user-menu').PropositionUserMenu.init();
  require('analytics').Analytics.init();
  require('disclosure').Disclosure.init();
  require('mailcheck-warning').MailcheckWarning.init(
    '.mtp-account-management input[type=email]',
    ['sscl.gse.gov.uk', 'hmps.gsi.gov.uk', 'noms.gsi.gov.uk', 'justice.gsi.gov.uk'],
    ['gse.gov.uk', 'gsi.gov.uk', 'gov.uk']
  );
}());
