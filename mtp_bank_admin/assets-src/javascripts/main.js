'use strict';

// design systems
import {initAll} from 'govuk-frontend';
initAll();

// mtp-common
import {Analytics} from 'mtp/components/analytics';
import {Banner} from 'mtp/components/banner';
import {Disclosure} from 'mtp/components/disclosure';
import {MailcheckWarning} from 'mtp/components/mailcheck-warning';

Analytics.init();
Banner.init();
Disclosure.init();
MailcheckWarning.init(
  '.mtp-account-management input[type=email]',
  ['gov.sscl.com', 'justice.gov.uk'],
  ['gov.sscl.com', 'gov.uk']
);
