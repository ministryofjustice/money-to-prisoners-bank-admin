from openpyxl import styles

ADI_JOURNAL_SHEET = 'TEMPLATE'

# general info
ADI_DATE_FIELD = 'J9'

# journal table
ADI_JOURNAL_START_ROW = 16

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
        'style': dict(
            border={
                'left': styles.Side(style='medium', color='000000'),
                'right': styles.Side(style='medium', color='000000')
            },
            **_white_style
        )
    },
    'company': {'column': 'C', 'style': _white_style},
    'business_unit': {'column': 'D', 'style': _white_style},
    'responsibility_code': {'column': 'E', 'style': _white_style},
    'activity': {'column': 'F', 'style': _white_style},
    'account': {'column': 'G', 'style': _white_style},
    'funding_source': {'column': 'H', 'style': _white_style},
    'analysis': {'column': 'I', 'style': _white_style},
    'spare': {
        'column': 'J',
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
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='000000'),
                'right': styles.Side(style='medium', color='000000')
            },
            **_white_style
        )
    },
    'line_dff_1': {'column': 'N', 'style': _tan_style},
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

ADI_FIELD_VALUES = {
    'upload': {
        'payment': {'debit': 'O', 'credit': 'O'},
        'refund': {'debit': 'O', 'credit': 'O'},
    },
    'company': {
        'payment': {'debit': '1', 'credit': '1'},
        'refund': {'debit': '1', 'credit': '1'},
    },
    'business_unit': {
        'payment': {'debit': '535'},
    },
    'responsibility_code': {
        'payment': {'debit': '9500', 'credit': '9500'},
    },
    'activity': {
        'payment': {'debit': '950', 'credit': '950'},
    },
    'account': {
        'payment': {'debit': '8890', 'credit': '9400'},
    },
    'funding_source': {
        'payment': {'debit': '95', 'credit': '95'},
    },
    'analysis': {
        'payment': {'debit': '000000', 'credit': '000000'},
        'refund': {'debit': '000000', 'credit': '000000'},
    },
    'spare': {
        'payment': {'debit': '000000', 'credit': '000000'},
        'refund': {'debit': '000000', 'credit': '000000'},
    },
    'description': {
        'payment': {'debit': 'MTP Payment', 'credit': 'MTP Payment'},
        'refund': {'debit': 'MTP Refund', 'credit': 'MTP Refund'},
    },
}
