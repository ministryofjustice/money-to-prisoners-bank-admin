from mtp_common.test_utils.functional_tests import FunctionalTestCase


class BankAdminTestCase(FunctionalTestCase):
    """
    Base class for all bank-admin functional tests
    """
    accessibility_scope_selector = '#content'


class LoginTests(BankAdminTestCase):
    """
    Tests for Login page
    """

    def test_title(self):
        self.driver.get(self.live_server_url)
        heading = self.driver.find_element_by_tag_name('h1')
        self.assertEqual('Bank Admin', heading.text)
        self.assertEqual('48px', heading.value_of_css_property('font-size'))

    def test_bad_login(self):
        self.login('bank-admin', 'bad-password')
        self.assertInSource('There was a problem submitting the form')

    def test_good_login(self):
        self.login('bank-admin', 'bank-admin')
        self.assertCurrentUrl('/')
        self.assertInSource('Download files')

    def test_good_refund_login(self):
        self.login('refund-bank-admin', 'refund-bank-admin')
        self.assertCurrentUrl('/')
        self.assertInSource('Download files')

    def test_logout(self):
        self.login('bank-admin', 'bank-admin')
        self.driver.find_element_by_link_text('Sign out').click()
        self.assertCurrentUrl('/login/')


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
        self.assertInSource('ADI Journal – refunds')
        self.assertInSource('Download transactions')
        self.assertInSource('<a href="#">Previous ADI Journals – refunds</a>')
        self.assertInSource('ADI Journal – credits')
        self.assertInSource('Bank statement')
        self.assertInSource('Download transactions')
        self.assertInSource('<a href="#">Previous bank statements</a>')
        first_section = self.driver.find_element_by_xpath('//section')
        self.assertEqual('inline-block', first_section.value_of_css_property('display'))
        page_heading_1 = self.driver.find_element_by_xpath('//h1')
        self.assertEqual('28px', page_heading_1.value_of_css_property('font-size'))
        page_heading_2 = self.driver.find_element_by_xpath('//h2')
        self.assertEqual('19px', page_heading_2.value_of_css_property('font-size'))
        file_link = self.driver.find_element_by_css_selector('div.mtp-filelink')
        self.assertEqual('22px', file_link.value_of_css_property('margin-top'))

    def test_open_foldout(self):
        label = "Previous ADI Journals – refunds"
        expand_button = self.driver.find_element_by_xpath('//div[a[contains(text(),"' + label + '")]]')
        expand_button_link = expand_button.find_element_by_tag_name('a')
        expand_box = self.driver.find_element_by_xpath(
            '//*[text() = "' + label + '"]/following::div[contains(@class, "help-box-contents")]'
        )
        self.assertEqual('none', expand_box.value_of_css_property('display'))
        self.assertEqual('false', expand_button.get_attribute('aria-expanded'))
        expand_button_link.click()
        self.assertEqual('block', expand_box.value_of_css_property('display'))
        self.assertEqual('true', expand_button.get_attribute('aria-expanded'))
