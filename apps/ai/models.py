from django.db import models
from django.utils import timezone


# Create your models here.
class PredictionLog(models.Model):
    date = models.DateField()
    ticker = models.CharField(max_length=20)
    predicted_price = models.FloatField()
    actual_price = models.FloatField()
    error = models.FloatField()
    sector = models.CharField(max_length=100, null=True, blank=True)
    model_version = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("date", "ticker", "model_version")


class InfoSuccessRate(models.Model):
    field_name = models.CharField(max_length=128, primary_key=True)  # 項目名
    total_success_rate = models.FloatField(default=0.0)  # 累積成功率
    count = models.IntegerField(default=0)              # 測定回数
    source = models.CharField(max_length=64, default="info")
    date_measured = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feature_success_rate'

    @property
    def average_success_rate(self):
        return self.total_success_rate / self.count if self.count else 0
