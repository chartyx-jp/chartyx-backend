# apps/common/db_operator.py などに

from apps.common.app_initializer import DjangoAppInitializer
from django.db import transaction
from django.utils import timezone
import logging

class DBOperator(DjangoAppInitializer):
    def __init__(self,*args,**kwargs):
        super().__init__(*args, **kwargs)

    def bulk_insert(self, model_class, objects, batch_size=100, ignore_conflicts=False):
        if not objects:
            return
        model_class.objects.bulk_create(self, objects, batch_size=batch_size, ignore_conflicts=ignore_conflicts)
        self.log.info(f" {model_class.__name__}のバルクインサート完了: {len(objects)}件")

    def bulk_update(self, model_class, objects, fields, batch_size=100):
        if not objects:
            return
        model_class.objects.bulk_update(objects, fields=fields, batch_size=batch_size)
        self.log.info(f" {model_class.__name__}のバルクアップデート完了: {len(objects)}件")

    def delete_all(self, model_class):
        model_class.objects.all().delete()
        self.log.info(f" {model_class.__name__}の全データ削除完了")

    def upsert(self, model_class, defaults, **lookup_fields):
        obj, created = model_class.objects.update_or_create(defaults=defaults, **lookup_fields)

        self.log.info(f" {model_class.__name__}のUPSERT完了: {'作成' if created else '更新'}")
        return obj, created


    def safe_transaction(self, func, *args, **kwargs):
        with transaction.atomic():
            self.log.info("トランザクション開始")
            return func(*args, **kwargs)
    
    def save_success_rate_to_db(self, success_rate_series, source="info"):
        from apps.ai.models import InfoSuccessRate
        now = timezone.now()
        objects = []

        for field, rate in success_rate_series.items():
            obj = InfoSuccessRate(
                field_name=field,
                success_rate=rate,
                source=source,
                date_measured=now,
            )
            objects.append(obj)

        self.bulk_insert(InfoSuccessRate, objects)
        self.log.info("✅ Success rate saved to DB!")

    def upsert_success_rate(self, success_rate_series, source="info"):
        from apps.ai.models import InfoSuccessRate
        from django.db.models import F
        from django.utils import timezone

        now = timezone.now()

        for field, new_rate in success_rate_series.items():
            obj, created = InfoSuccessRate.objects.get_or_create(
                field_name=field,
                defaults={
                    "total_success_rate": new_rate,
                    "count": 1,
                    "source": source,
                    "date_measured": now,
                }
            )
            if not created:
                # 更新：累積加算 & カウントアップ
                InfoSuccessRate.objects.filter(field_name=field).update(
                    total_success_rate=F('total_success_rate') + new_rate,
                    count=F('count') + 1,
                    source=source,
                    date_measured=now
                )

        self.log.info("✅ Success rates UPSERT (insert or update) 完了！")



    def get_usable_features(self,success_rate_threshold=90.0, min_trials=5):
        from django.db.models import F
        from apps.ai.models import InfoSuccessRate

        # DB側で average_success_rate を計算しながらフィルタ
        queryset = InfoSuccessRate.objects.annotate(
            avg_success=F('total_success_rate') / F('count')
        ).filter(
            count__gte=min_trials,
            avg_success__gte=success_rate_threshold
        )

        # field_nameと計算した成功率を取得
        results = queryset.values('field_name', 'avg_success')

        # 「項目名：成功率%」の形式に整形
        formatted_results = [
            f"{item['field_name']}：{item['avg_success']:.1f}％"
            for item in results
        ]

        self.log.info(f" 取得成功率フィルタリング完了！: {len(formatted_results)}項目")
        return formatted_results
