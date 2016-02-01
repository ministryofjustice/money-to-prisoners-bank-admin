import glob
import logging
import os
import socket
from urllib.parse import urlparse
import unittest

from django.conf import settings
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger('mtp')


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

    def login_and_go_to(self, link_text):
        self.login('bank-admin', 'bank-admin')
        self.driver.find_element_by_partial_link_text(link_text).click()


class LoginTests(FunctionalTestCase):
    """
    Tests for Login page
    """

    def test_title(self):
        self.driver.get(self.live_server_url)
        heading = self.driver.find_element_by_tag_name('h1')
        self.assertEquals('Bank Admin', heading.text)
        self.assertEquals('48px', heading.value_of_css_property('font-size'))

    def test_bad_login(self):
        self.login('bank-admin', 'bad-password')
        self.assertIn('There was a problem submitting the form',
                      self.driver.page_source)

    def test_good_login(self):
        self.login('bank-admin', 'bank-admin')
        self.assertEquals(self.driver.current_url, self.live_server_url + '/')
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
        self.login('bank-admin', 'bank-admin')

    def test_checking_download_page(self):
        self.assertIn('Download files', self.driver.page_source)

    def test_checking_help_popup(self):
        help_box_contents = self.driver.find_element_by_css_selector('.help-box-contents')
        help_box_button = self.driver.find_element_by_css_selector('.help-box h3')
        self.assertEquals('none', help_box_contents.value_of_css_property('display'))
        help_box_button.click()
        self.assertEquals('block', help_box_contents.value_of_css_property('display'))
        help_box_button.click()
        self.assertEquals('none', help_box_contents.value_of_css_property('display'))
