'use strict';

// design systems
import {initAll} from 'govuk-frontend';
initAll();

// mtp common components
import {initDefaults} from 'mtp_common';
import {initStaffDefaults} from 'mtp_common/staff-app';
import {MailcheckWarning} from 'mtp_common/components/mailcheck-warning';
initDefaults();
initStaffDefaults();
MailcheckWarning.init(
  '.mtp-account-management input[type=email]',
  ['gov.sscl.com', 'justice.gov.uk'],
  ['gov.sscl.com', 'gov.uk'],
  []
);
MailcheckWarning.init(
  '#change-your-email #id_email',
  ['gov.sscl.com', 'justice.gov.uk'],
  ['gov.sscl.com', 'gov.uk'],
  []
);
