from django.apps import AppConfig


class CmsConfig(AppConfig):
    name = 'cms'

class APIServerErrorCode(object):
    # global
    ERROR_PARAME          = 9999
    WRONG_PARAME          = 9998

    #auth
    REG_SUCCESS           = 1000
    ALERADY_REG           = 1001
    FLUSH_SESSION_SUCCESS = 1002
    SESSION_EXPIRED       = 1003
    LOGIN_SUCCESS         = 1004
    SESSION_NOT_WORK      = 1005

    #order

    #push

    #
    @staticmethod
    def getMessage(errorCode):
        if errorCode in CodeMessage:
            return CodeMessage[errorCode]
        else:
            return  "error code not defined"

CodeMessage = {
    APIServerErrorCode.ERROR_PARAME          :'Request Error',
    APIServerErrorCode.WRONG_PARAME          :'Request Paramer Wrong',
    APIServerErrorCode.REG_SUCCESS           :'Register Success',
    APIServerErrorCode.ALERADY_REG           :'User Alerady Register',
    APIServerErrorCode.FLUSH_SESSION_SUCCESS :'Flush Session Success',
    APIServerErrorCode.SESSION_EXPIRED       :'Session Expired',
    APIServerErrorCode.LOGIN_SUCCESS         :'Login Success',
    APIServerErrorCode.SESSION_NOT_WORK      :'Session Not Work'
    }