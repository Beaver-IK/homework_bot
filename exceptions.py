from requests import RequestException


class DebugInfo(Exception):
    pass

class ErrorInfo(RequestException, KeyError, TypeError, Exception):
    pass

class EnvVariableIsMissing(Exception):
    pass


class ErrorStatusCode(ErrorInfo):
    pass


class NoListHomeworks(ErrorInfo):
    pass


class ListIsEmpty(DebugInfo):
    pass


class NotNewStutus(DebugInfo):
    pass


class StatusDoesNotExist(ErrorInfo):
    pass


class ErrorSendMessage(ErrorInfo):
    pass
