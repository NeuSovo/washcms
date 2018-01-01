from django.apps import AppConfig
from cms.models import CodeRecord

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
    SESSION_NOT_WORK      = 1004
    CHECK_USER_FAILED     = 1005
    LOGIN_SUCCESS         = 1006

    #order

    #push

    #
    @staticmethod
    def getMessage(errorCode):
        if errorCode in CodeMessage:
            try:
                code = CodeRecord.objects.get(code_key=errorCode)
                code.code_count += 1
                code.save()
            except Exception as e:
                pass

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
    APIServerErrorCode.SESSION_NOT_WORK      :'Session Not Work',
    APIServerErrorCode.CHECK_USER_FAILED     :'Verify User Failed',
    APIServerErrorCode.LOGIN_SUCCESS         :'Login Success',
    }