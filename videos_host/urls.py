# videos_host/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # 管理员登录和登出
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),

    # 管理员视频仪表盘
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # 新增/修改视频
    path('admin-dashboard/upload/', views.admin_video_edit, name='admin_video_add'),
    path('admin-dashboard/edit/<int:video_id>/', views.admin_video_edit, name='admin_video_edit'),

    # 删除视频
    path('admin-dashboard/delete/<int:video_id>/', views.admin_delete_video, name='admin_delete_video'),

    # 用户观看视频
    path('watch/<str:video_filename>/', views.watch_video, name='watch_video'),
]