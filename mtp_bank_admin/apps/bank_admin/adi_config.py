from openpyxl import styles

ADI_JOURNAL_SHEET = 'TEMPLATE'

# journal table
ADI_JOURNAL_START_ROW = 4

_white_style = {
    'fill': {
        'start_color': 'FFFFFF',
        'end_color': 'FFFFFF'
    }
}

_tan_style = {
    'fill': {
        'start_color': 'FFCC99',
        'end_color': 'FFCC99'
    }
}

ADI_FINAL_ROW_STYLE = {
    'border': {
        'top': styles.Side(style='thin', color='000000'),
        'bottom': styles.Side(style='thin', color='000000')
    }
}

ADI_JOURNAL_FIELDS = {
    'upload': {
        'column': 'B',
        'value': {
            'payment': {'debit': 'o', 'credit': 'o'},
            'refund': {'debit': 'o', 'credit': 'o'},
            'reject': {'debit': 'o', 'credit': 'o'},
        },
        'style': dict(
            border={
                'left': styles.Side(style='medium', color='000000'),
                'right': styles.Side(style='medium', color='000000')
            },
            **_white_style
        )
    },
    'company': {
        'column': 'C',
        'value': {
            'payment': {'debit': '1', 'credit': '1'},
            'refund': {'debit': '1', 'credit': '1'},
            'reject': {'debit': '1', 'credit': '1'},
        },
        'style': _white_style
    },
    'business_unit': {
        'column': 'D',
        'value': {
            'payment': {'debit': '535', 'credit': '{prison_ledger_code}'},
            'refund': {'debit': '535', 'credit': '535'},
            'reject': {'debit': '535', 'credit': '535'},
        },
        'style': _white_style
    },
    'responsibility_code': {
        'column': 'E',
        'value': {
            'payment': {'debit': '9500', 'credit': '9500'},
            'refund': {'debit': '9500', 'credit': '9500'},
            'reject': {'debit': '9500', 'credit': '9500'},
        },
        'style': _white_style
    },
    'activity': {
        'column': 'F',
        'value': {
            'payment': {'debit': '950', 'credit': '950'},
            'refund': {'debit': '950', 'credit': '950'},
            'reject': {'debit': '950', 'credit': '950'},
        },
        'style': _white_style
    },
    'account': {
        'column': 'G',
        'value': {
            'payment': {'debit': '08870', 'credit': '09400'},
            'refund': {'debit': '08870', 'credit': '08870'},
            'reject': {'debit': '08870', 'credit': '08826'},
        },
        'style': _white_style
    },
    'funding_source': {
        'column': 'H',
        'value': {
            'payment': {'debit': '95', 'credit': '95'},
            'refund': {'debit': '95', 'credit': '95'},
            'reject': {'debit': '95', 'credit': '95'},
        },
        'style': _white_style
    },
    'analysis': {
        'column': 'I',
        'value': {
            'payment': {'debit': '00000', 'credit': '00000'},
            'refund': {'debit': '00000', 'credit': '00000'},
            'reject': {'debit': '00000', 'credit': '17059'},
        },
        'style': _white_style
    },
    'spare': {
        'column': 'J',
        'value': {
            'payment': {'debit': '000000', 'credit': '000000'},
            'refund': {'debit': '000000', 'credit': '000000'},
            'reject': {'debit': '000000', 'credit': '000000'},
        },
        'style': dict(
            border={
                'right': styles.Side(style='medium', color='000000')
            },
            **_white_style
        )
    },
    'debit': {
        'column': 'K',
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='000000'),
                'right': styles.Side(style='thin', color='000000')
            },
            **_white_style
        )
    },
    'credit': {
        'column': 'L',
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='000000'),
                'right': styles.Side(style='thin', color='000000')
            },
            **_white_style
        )
    },
    'description': {
        'column': 'M',
        'value': {
            'payment': {'debit': '{unique_id}', 'credit': '{prison_name} MTP Total {date}'},
            'refund': {'debit': '{unique_id}', 'credit': 'MTP Refund File {date}'},
            'reject': {'debit': '{unique_id}', 'credit': '{date} - {reference}'},
        },
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='000000'),
                'right': styles.Side(style='medium', color='000000')
            },
            alignment={
                'horizontal': 'center'
            },
            **_white_style
        )
    },
    'line_dff_1': {
        'column': 'N',
        'style': _tan_style
    },
    'messages': {
        'column': 'O',
        'style': dict(
            border={
                'right': styles.Side(style='medium', color='000000')
            },
            **_tan_style
        )
    },
}
