DISBURSEMENTS_JOURNAL_SHEET = 'Data'
DISBURSEMENTS_JOURNAL_START_ROW = 3


BANK_DETAILS_FIELDS = [
    'sort_code', 'account_number', 'name_of_bank', 'account_name', 'roll_number'
]


DISBURSEMENT_FIELDS = {
    'operating_unit': {
        'column': 'A',
        'value': 'NMS'
    },
    'supplier_number': {
        'column': 'B',
        'value': ''
    },
    'site_name': {
        'column': 'C',
        'value': ''
    },
    'payee_type': {
        'column': 'D',
        'value': 'Client'
    },
    'unique_payee_reference': {
        'column': 'E',
        'value': '{id}'
    },
    'payee_forname': {
        'column': 'F',
        'value': '{recipient_first_name}'
    },
    'payee_surname': {
        'column': 'G',
        'value': '{recipient_last_name}'
    },
    'payee_address_line1': {
        'column': 'H',
        'value': '{address_line1}'
    },
    'payee_address_line2': {
        'column': 'I',
        'value': '{address_line2}'
    },
    'payee_address_city': {
        'column': 'J',
        'value': '{city}'
    },
    'payee_postcode': {
        'column': 'K',
        'value': '{postcode}'
    },
    'remittance_email_address': {
        'column': 'L',
        'value': '{recipient_email}'
    },
    'vat_registration_number': {
        'column': 'M',
        'value': ''
    },
    'payment_method': {
        'column': 'N',
        'value': '{payment_method}'
    },
    'sort_code': {
        'column': 'O',
        'value': '{sort_code}'
    },
    'account_number': {
        'column': 'P',
        'value': '{account_number}'
    },
    'name_of_bank': {
        'column': 'Q',
        'value': 'Unknown Bank'
    },
    'account_name': {
        'column': 'R',
        'value': '{recipient_first_name} {recipient_last_name}'
    },
    'roll_number': {
        'column': 'S',
        'value': '{roll_number}'
    },
    'invoice_date': {
        'column': 'T',
        'value': '{date}'
    },
    'invoice_number': {
        'column': 'U',
        'value': '{invoice_number}'
    },
    'description': {
        'column': 'V',
        'value': '{description}'
    },
    'entity': {
        'column': 'W',
        'value': '0210'
    },
    'cost_centre': {
        'column': 'X',
        'value': '{prison_ledger_code}'
    },
    'account': {
        'column': 'Y',
        'value': '2617902085'  # MTP SOP account code
    },
    'objective': {
        'column': 'Z',
        'value': '0000000'
    },
    'analysis': {
        'column': 'AA',
        'value': '00000000'
    },
    'vat_rate': {
        'column': 'AB',
        'value': 'UK OUT OF SCOPE'
    },
    'line_description': {
        'column': 'AC',
        'value': ''
    },
    'net_amount': {
        'column': 'AD',
        'value': '{amount_pounds}'
    },
    'vat_amount': {
        'column': 'AE',
        'value': '0'
    },
    'total_amount': {
        'column': 'AF',
        'value': '{amount_pounds}'
    },
    'completer_id': {
        'column': 'AG',
        'value': '{creator}'
    },
    'approver_id': {
        'column': 'AH',
        'value': '{confirmer}'
    },
}
