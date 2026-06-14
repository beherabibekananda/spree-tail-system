from django.urls import path
from . import views

urlpatterns = [
    path('expenses/', views.expenses_list, name='expenses_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:expense_id>/delete/', views.expense_delete, name='expense_delete'),
    path('settlements/create/', views.settlement_create, name='settlement_create'),
]
