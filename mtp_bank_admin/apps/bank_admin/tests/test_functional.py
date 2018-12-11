from mtp_common.test_utils.functional_tests import FunctionalTestCase


class BankAdminTestCase(FunctionalTestCase):
    """
    Base class for all bank-admin functional tests
    """
    accessibility_scope_selector = '#content'

    def login(self, *args, **kwargs):
        kwargs['url'] = self.live_server_url + '/en-gb/'
        super().login(*args, **kwargs)


class LoginTests(BankAdminTestCase):
    """
    Tests for Login page
    """

    def test_title(self):
        self.driver.get(self.live_server_url + '/en-gb/')
        heading = self.driver.find_element_by_tag_name('h1')
        self.assertEqual('Bank admin\nSign in', heading.text)

    def test_bad_login(self):
        self.login('bank-admin', 'bad-password')
        self.assertInSource('There was a problem')

    def test_good_login(self):
        self.login('bank-admin', 'bank-admin')
        self.assertCurrentUrl('/en-gb/')
        self.assertInSource('Download files')

    def test_good_refund_login(self):
        self.login('refund-bank-admin', 'refund-bank-admin')
        self.assertCurrentUrl('/en-gb/')
        self.assertInSource('Download files')

    def test_good_login_without_case_sensitivity(self):
        self.login('Bank-Admin', 'bank-admin')
        self.assertCurrentUrl('/en-gb/')
        self.assertInSource('Download files')

    def test_logout(self):
        self.login('bank-admin', 'bank-admin')
        self.driver.find_element_by_class_name('mtp-user-menu__toggle').click()
        self.driver.find_element_by_link_text('Sign out').click()
        self.assertCurrentUrl('/en-gb/login/')


class DownloadPageTests(BankAdminTestCase):
    """
    Tests for Download page
    """

    def setUp(self):
        super().setUp()
        self.login('refund-bank-admin', 'refund-bank-admin')

    def test_checking_download_page(self):
        self.assertInSource('Access Pay file – refunds')
        self.assertInSource('Download file')
        self.assertInSource('ADI Journal')
        self.assertInSource('Download transactions')
        self.assertInSource('Previous ADI Journals')
        self.assertInSource('Bank statement')
        self.assertInSource('Download transactions')
        self.assertInSource('Previous bank statements')

    def test_open_foldout(self):
        expand_button = self.driver.find_element_by_link_text('Previous ADI Journals')
        expand_box = self.get_element('previous-adi-journals')
        self.assertEqual('none', expand_box.value_of_css_property('display'))
        self.assertEqual('false', expand_button.get_attribute('aria-expanded'))
        expand_button.click()
        self.assertEqual('block', expand_box.value_of_css_property('display'))
        self.assertEqual('true', expand_button.get_attribute('aria-expanded'))
