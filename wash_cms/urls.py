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
    path('boss/clear/<str:action>',clear_account_view),

    path('boss/report/order/<str:action>', boos_report_order_view),
    path('boss/report/order/day/<int:day>', boos_report_order_view),
    path('boss/report/order/month/<int:month>', boos_report_order_view),

    path('boss/report/stock/<str:action>', boos_report_stock_view),
    path('boss/report/stock/day/<int:day>', boos_report_stock_view),
    path('boss/report/stock/month/<int:month>', boos_report_stock_view),

    path('boss/report/store/month', boos_report_store_view),
    path('boss/report/store/month/<int:month>', boos_report_store_view),

    path('user/bind', bind_user_view),
    path('user/order', order_view),
    path('user/getgoods', get_user_goods_view),
    path('user/profile', change_profile_view),

    path('user/order/<str:action>', order_2_view),
    path('user/order/<str:action>/<int:status>', order_2_view),
    path('user/recover/<str:action>', recover_view),

    path('user/report', user_report_view),
    path('user/report/<int:month>', user_report_view), # now, month

    path('staff/goods/<str:action>', staff_goods_view), # get,
    path('staff/kuguan/pick/<str:action>', staff_kuguan_pick_view), # get confirm
    path('staff/kuguan/goods/<str:action>', staff_kuguan_goods_view), # new addstock


    path('staff/peisong/profile/<str:action>', staff_profile_view),# get,update
    path('staff/peisong/order/<str:status>/<str:action>', staff_peisong_order_view), # ,receive,pay,get,set
    path('staff/peisong/stock/<str:action>', staff_peisong_stock_view),       # car,ps
    path('staff/peisong/pick/<str:action>', staff_peisong_pick_view), # new,get
    
    path('staff/peisong/report/<str:action>', staff_peisong_report_view), #today
    path('staff/peisong/report/month/<int:month>', staff_peisong_report_view), #month 
    path('staff/peisong/report/day/<int:day>', staff_peisong_report_view), #day 

    path('test',test_test_view)

]
