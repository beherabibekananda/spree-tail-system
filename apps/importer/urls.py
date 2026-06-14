from django.urls import path
from . import views

urlpatterns = [
    path('import/', views.import_csv, name='import_csv'),
    path('import/session/<int:session_id>/', views.import_review, name='import_review'),
    path('import/anomaly/<int:anomaly_id>/action/', views.import_anomaly_action, name='import_anomaly_action'),
    path('import/session/<int:session_id>/commit/', views.import_commit, name='import_commit'),
    path('import/session/<int:session_id>/report/', views.import_report, name='import_report'),
]
