from requests import RequestException
from telebot.apihelper import ApiException


class DebugInfo(Exception):
    pass


class ErrorInfo(RequestException, ApiException, KeyError, TypeError):
    pass


class EnvVariableIsMissing(Exception):
    pass


class ErrorStatusCode(ErrorInfo):
    pass


class NoListHomeworks(ErrorInfo):
    pass


class ListIsEmpty(DebugInfo):
    pass


class KeyDoesNotExist(ErrorInfo):
    pass


class ErrorSendMessage(Exception):
    pass
