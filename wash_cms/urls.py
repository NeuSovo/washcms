"""wash_cms URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import url,include
from django.urls import path
from cms.views import *
urlpatterns = [
    path('',index),
    # url(r'^jet/', include('jet.urls', 'jet')),  # Django JET URLS
    # url(r'^jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    path('admin/', admin.site.urls),
    # path('auth/rreg',re_register_view),# Drop

    path('auth/reg', register_view),
    path('auth/login', login_view),

    path('tools/qrcode/<str:data>', qrcode_view),

    path('boss/area', change_deliveryarea_view),
    path('boss/store', change_store_view),
    path('boss/employee', change_employee_view),
    path('boss/goods', change_goods_view),

    path('user/bind', bind_user_view),
    path('user/order', order_view),
    path('user/getgoods', get_user_goods_view),
    path('user/profile', change_profile_view),

    path('user/order/<str:action>',order_2_view),
    path('user/order/<str:action>/<int:status>',order_2_view),

    # # path('staff/kuguan/'),
    path('staff/peisong/profile/<str:action>', staff_profile_view),# get,update
    path('staff/peisong/order/<str:action>', staff_order_view), # get,receive,pay
    # path('staff/peisong/',)

]
