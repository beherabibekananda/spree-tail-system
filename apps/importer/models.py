from django.db import models

from django.contrib.auth.models import User

class ImportSession(models.Model):
    filename = models.CharField(max_length=255)
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.IntegerField(default=0)
    clean_rows = models.IntegerField(default=0)
    anomaly_rows = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending') # 'pending', 'approved', 'committed'

    def __str__(self):
        return f"Session {self.id} ({self.filename}) - {self.status}"

class ImportAnomaly(models.Model):
    session = models.ForeignKey(ImportSession, on_delete=models.CASCADE, related_name='anomalies')
    row_number = models.IntegerField()
    raw_data = models.TextField() # stores JSON string of the CSV row
    issue_type = models.CharField(max_length=100)
    issue_description = models.TextField()
    proposed_action = models.CharField(max_length=100)
    action_taken = models.CharField(max_length=100, blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_anomalies')
    status = models.CharField(max_length=20, default='pending') # 'pending', 'approved', 'rejected', 'applied'

    def __str__(self):
        return f"Row {self.row_number} in Session {self.session.id}: {self.issue_type}"

