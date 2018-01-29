from openpyxl import styles

ADI_JOURNAL_SHEET = 'WebADI'


ADI_DATE_CELL = 'E12'
ADI_DATE_FORMAT = '%d/%m/%y'
ADI_BATCH_NAME_CELL = 'E14'
ADI_BATCH_DATE_FORMAT = '%d%m%y'
ADI_BATCH_NAME_FORMAT = '578/MTP/%(date)s/%(initials)s'
DEFAULT_INITIALS = 'KB'

# journal table
ADI_JOURNAL_START_ROW = 19

_white_style = {
    'fill': {
        'start_color': 'FFFFFF',
        'end_color': 'FFFFFF',
        'fill_type': None,
    },
    'font': {
        'name': 'Arial',
        'size': 11,
    }
}

_light_blue_style = {
    'fill': {
        'start_color': 'F7F9FC',
        'end_color': 'F7F9FC',
        'fill_type': 'solid',
    },
    'font': {
        'name': 'Arial',
        'size': 11,
    }
}

ADI_FINAL_ROW_STYLE = {
    'border': {
        'top': styles.Side(style='thin', color='C7C7C7'),
        'bottom': styles.Side(style='thin', color='C7C7C7'),
    },
    'fill': {
        'start_color': 'F2F4F7',
        'end_color': 'F2F4F7',
        'fill_type': 'solid',
    },
    'font': {
        'name': 'Arial',
        'size': 11,
    }
}

ADI_JOURNAL_FIELDS = {
    'upload': {
        'column': 'B',
        'value': {
            'payment': {'debit': 'O', 'credit': 'O'},
            'refund': {'debit': 'O', 'credit': 'O'},
            'reject': {'debit': 'O', 'credit': 'O'},
        },
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='C7C7C7'),
                'right': styles.Side(style='thin', color='C7C7C7')
            },
            fill=_white_style['fill'],
            font={
                'name': 'Wingdings',
                'size': 11,
            }
        )
    },
    'entity': {
        'column': 'C',
        'value': {
            'payment': {'debit': '0210', 'credit': '0210'},
            'refund': {'debit': '0210', 'credit': '0210'},
            'reject': {'debit': '0210', 'credit': '0210'},
        },
        'style': _white_style
    },
    'cost_centre': {
        'column': 'D',
        'value': {
            'payment': {'debit': '99999999', 'credit': '{prison_ledger_code}'},
            'refund': {'debit': '99999999', 'credit': '99999999'},
            'reject': {'debit': '99999999', 'credit': '10209200'},
        },
        'style': _white_style
    },
    'account': {
        'column': 'E',
        'value': {
            'payment': {'debit': '1841102059', 'credit': '2617902085'},
            'refund': {'debit': '1841102059', 'credit': '1841102059'},
            'reject': {'debit': '1841102059', 'credit': '1816902028'},
        },
        'style': _white_style
    },
    'objective': {
        'column': 'F',
        'value': {
            'payment': {'debit': '0000000', 'credit': '0000000'},
            'refund': {'debit': '0000000', 'credit': '0000000'},
            'reject': {'debit': '0000000', 'credit': '0000000'},
        },
        'style': _white_style
    },
    'analysis': {
        'column': 'G',
        'value': {
            'payment': {'debit': '00000000', 'credit': '00000000'},
            'refund': {'debit': '00000000', 'credit': '00000000'},
            'reject': {'debit': '00000000', 'credit': '00000000'},
        },
        'style': _white_style
    },
    'intercompany': {
        'column': 'H',
        'value': {
            'payment': {'debit': '0000', 'credit': '0000'},
            'refund': {'debit': '0000', 'credit': '0000'},
            'reject': {'debit': '0000', 'credit': '0000'},
        },
        'style': _white_style
    },
    'spare': {
        'column': 'I',
        'value': {
            'payment': {'debit': '0000000', 'credit': '0000000'},
            'refund': {'debit': '0000000', 'credit': '0000000'},
            'reject': {'debit': '0000000', 'credit': '0000000'},
        },
        'style': dict(
            border={
                'right': styles.Side(style='thin', color='C7C7C7')
            },
            **_white_style
        )
    },
    'debit': {
        'column': 'J',
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='C7C7C7'),
                'right': styles.Side(style='thin', color='C7C7C7')
            },
            **_white_style
        )
    },
    'credit': {
        'column': 'K',
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='C7C7C7'),
                'right': styles.Side(style='thin', color='C7C7C7')
            },
            **_white_style
        )
    },
    'description': {
        'column': 'L',
        'value': {
            'payment': {'debit': '{reconciliation_code}', 'credit': '{prison_name} MTP Total {date}'},
            'refund': {'debit': '{reconciliation_code}', 'credit': 'MTP Refund File {date}'},
            'reject': {'debit': '{reconciliation_code}', 'credit': '{date} - {reference}'},
        },
        'style': dict(
            border={
                'left': styles.Side(style='thin', color='C7C7C7'),
                'right': styles.Side(style='thin', color='C7C7C7')
            },
            alignment={
                'horizontal': 'center'
            },
            **_white_style
        )
    },
    'resolution': {
        'column': 'M',
        'style': dict(
            _light_blue_style,
            font={
                'name': 'Wingdings',
                'size': 11,
            },
            border={
                'left': styles.Side(style='thin', color='C7C7C7')
            }
        )
    },
    'messages': {
        'column': 'O',
        'style': dict(
            _light_blue_style,
            border={
                'right': styles.Side(style='medium', color='C7C7C7')
            }
        )
    }
}
