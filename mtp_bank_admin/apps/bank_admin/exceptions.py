class EmptyFileError(Exception):
    pass


class UnrecognisedFieldError(BaseException):
    pass


class EarlyReconciliationError(BaseException):
    pass


class UpstreamServiceUnavailable(BaseException):
    pass
