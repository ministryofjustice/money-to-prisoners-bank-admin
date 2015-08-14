from django.test import SimpleTestCase
from unittest import mock

import adi


class AdiFileGenerationTestCase(SimpleTestCase):

    @mock.patch('bank_admin.adi.api_client')
    def test_adi_file_generation(self, mock_api_client):
        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = []

        adi.generate_file(None)
