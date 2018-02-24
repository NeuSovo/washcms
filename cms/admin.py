from django.contrib import admin
from cms.models import CodeRecord, User, CustomerProfile
# Register your models here.


class CodeRecordAdmin(admin.ModelAdmin):
    '''
        Admin View for CodeRecord
    '''
    list_display = ('code_key', 'code_name', 'code_count',)
    list_filter = ('code_name',)
    # raw_id_fields = ('',)
    # readonly_fields = ('',)
    # search_fields = ('',)


class UserProfileAdmin(admin.StackedInline):
    model = CustomerProfile
    verbose_name = '商家用户信息'
    can_delete = True


class UserTypeFilter(admin.SimpleListFilter):
    title = (u'用户身份')
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return (
            (0, u'管理员'),
            (1, u'配送员'),
            (2, u'库管'),
            (3, u'顾客'),
            (4, u'未注册')
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value():
            if int(self.value()) == 0:
                return queryset.filter(user_type = 0)
            if int(self.value()) == 1:
                return queryset.filter(user_type = 1)
            if int(self.value()) == 2:
                return queryset.filter(user_type = 2)
            if int(self.value()) == 3:
                return queryset.filter(user_type = 3)
            if int(self.value()) == 4:
                return queryset.filter(user_type = 4)

class UserAdmin(admin.ModelAdmin):
    '''
        Admin View for User
        edit profile return default
    '''

    def get_user_type(self, user):
        if user.user_type == 0:
            return u'%s' % (u"管理员",)
        elif user.user_type == 1:
            return u'%s' % (u"配送员",)
        elif user.user_type == 2:
            return u'%s' % (u"顾客",)
        elif user.user_type == 3:
            return u'%s' % (u"库管",)
        elif user.user_type == 4:
            return u'%s' % (u"未注册",)

    get_user_type.short_description = u'用户类型'

    get_user_type.allow_tags = True

    def get_readonly_fields(self,*args, **kwargs):
        return ['wk']

    list_display = ('wk', 'get_user_type')

    list_filter = (UserTypeFilter,)
    inlines = (UserProfileAdmin,)


admin.site.register(User, UserAdmin)
admin.site.register(CodeRecord, CodeRecordAdmin)
