(function () {
  'use strict';

  // common
  require('analytics').Analytics.init();
  require('disclosure').Disclosure.init();
  require('notifications').Notifications.init();
  require('mailcheck-warning').MailcheckWarning.init(
    '.mtp-account-management input[type=email]',
    ['sscl.gse.gov.uk', 'justice.gov.uk'],
    ['gse.gov.uk', 'gov.uk']
  );
}());
