(function () {
  'use strict';

  // common
  require('analytics').Analytics.init();
  require('disclosure').Disclosure.init();
  require('notifications').Notifications.init();
  require('mailcheck-warning').MailcheckWarning.init(
    '.mtp-account-management input[type=email]',
    ['gov.sscl.com', 'justice.gov.uk'],
    ['gov.sscl.com', 'gov.uk']
  );
}());
