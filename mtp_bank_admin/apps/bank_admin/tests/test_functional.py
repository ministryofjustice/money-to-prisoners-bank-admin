import glob
import logging
import os
import socket
from urllib.parse import urlparse
import unittest
import threading

from django.conf import settings
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger('mtp')
thread_local = threading.local()
thread_local.reloaded_data = False

@unittest.skipUnless('RUN_FUNCTIONAL_TESTS' in os.environ, 'functional tests are disabled')
class FunctionalTestCase(LiveServerTestCase):
    """
    Base class to define common methods to test subclasses below
    """

    @classmethod
    def _databases_names(cls, include_mirrors=True):
        # this app has no databases
        return []

    def setUp(self):
        if not thread_local.reloaded_data:
            self.load_test_data()
            thread_local.reloaded_data = True
        web_driver = os.environ.get('WEBDRIVER', 'phantomjs')
        if web_driver == 'firefox':
            fp = webdriver.FirefoxProfile()
            fp.set_preference('browser.startup.homepage', 'about:blank')
            fp.set_preference('startup.homepage_welcome_url', 'about:blank')
            fp.set_preference('startup.homepage_welcome_url.additional', 'about:blank')
            self.driver = webdriver.Firefox(firefox_profile=fp)
        elif web_driver == 'chrome':
            paths = glob.glob('node_modules/selenium-standalone/.selenium/chromedriver/*-chromedriver')
            paths = filter(lambda path: os.path.isfile(path) and os.access(path, os.X_OK),
                           paths)
            try:
                self.driver = webdriver.Chrome(executable_path=next(paths))
            except StopIteration:
                self.fail('Cannot find Chrome driver')
        else:
            path = './node_modules/phantomjs/lib/phantom/bin/phantomjs'
            self.driver = webdriver.PhantomJS(executable_path=path)

        self.driver.set_window_size(1000, 1000)
        self.driver.set_window_position(0, 0)

    def tearDown(self):
        self.driver.quit()

    def load_test_data(self):
        logger.info('Reloading test data')
        try:
            with socket.socket() as sock:
                sock.connect((
                    urlparse(settings.API_URL).netloc.split(':')[0],
                    os.environ.get('CONTROLLER_PORT', 8800))
                )
                sock.sendall(b'load_test_data')
                response = sock.recv(1024).strip()
                if response != b'done':
                    logger.error('Test data not reloaded!')
        except OSError:
            logger.exception('Error communicating with test server controller socket')

    def login(self, username, password):
        self.driver.get(self.live_server_url)
        login_field = self.driver.find_element_by_id('id_username')
        login_field.send_keys(username)
        password_field = self.driver.find_element_by_id('id_password')
        password_field.send_keys(password + Keys.RETURN)


class LoginTests(FunctionalTestCase):
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
        self.assertIn('There was a problem submitting the form',
                      self.driver.page_source)

    def test_good_login(self):
        self.login('bank-admin', 'bank-admin')
        self.assertEqual(self.driver.current_url, self.live_server_url + '/')
        self.assertIn('Download files', self.driver.page_source)

    def test_good_refund_login(self):
        self.login('refund-bank-admin', 'refund-bank-admin')
        self.assertEqual(self.driver.current_url, self.live_server_url + '/')
        self.assertIn('Download files', self.driver.page_source)

    def test_logout(self):
        self.login('bank-admin', 'bank-admin')
        self.driver.find_element_by_link_text('Sign out').click()
        self.assertEqual(self.driver.current_url.split('?')[0], self.live_server_url + '/login/')


class DownloadPageTests(FunctionalTestCase):
    """
    Tests for Download page
    """

    def setUp(self):
        super().setUp()
        self.login('refund-bank-admin', 'refund-bank-admin')

    def test_checking_download_page(self):
        self.driver.save_screenshot('screenshot.png')

        self.assertIn('Access Pay file – refunds', self.driver.page_source)
        self.assertIn('Download file', self.driver.page_source)
        self.assertIn('Previous files', self.driver.page_source)
        self.assertIn('ADI Journal – refunds', self.driver.page_source)
        self.assertIn('Download transactions', self.driver.page_source)
        self.assertIn('Previous ADI Journal – refunds', self.driver.page_source)
        self.assertIn('ADI Journal – payments', self.driver.page_source)
        self.assertIn('Bank statement', self.driver.page_source)
        self.assertIn('Download transactions', self.driver.page_source)
        self.assertIn('Previous bank statements', self.driver.page_source)

    def test_open_foldout(self):
        label = "Previous ADI Journal – refunds"
        expand_button = self.driver.find_element_by_xpath('//*[text() = "' + label + '"]')
        expand_box = self.driver.find_element_by_xpath(
            '//*[text() = "' + label + '"]/following::div[contains(@class, "help-box-contents")]'
        )
        self.assertEqual('block', expand_box.value_of_css_property('display'))

    def test_checking_help_popup(self):
        help_label = "Help with downloads"
        help_box_button = self.driver.find_element_by_xpath('//*[text() = "' + help_label + '"]')
        help_box_contents = self.driver.find_element_by_xpath(
            '//*[text() = "' + help_label + '"]/following::div[contains(@class, "help-box-contents")]'
        )
        self.assertEqual('none', help_box_contents.value_of_css_property('display'))
        help_box_button.click()
        self.assertEqual('block', help_box_contents.value_of_css_property('display'))
        help_box_button.click()
        self.assertEqual('none', help_box_contents.value_of_css_property('display'))
