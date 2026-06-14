from django.urls import path
from . import views

urlpatterns = [
    path('', views.groups_dashboard, name='groups_dashboard'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('groups/<int:group_id>/member/add/', views.group_member_add, name='group_member_add'),
    path('groups/<int:group_id>/member/<int:membership_id>/leave/', views.group_member_leave, name='group_member_leave'),
]
