from django.db import models

# Create your models here.

class Sector(models.Model):
    """
    株式市場における業種（セクター）を定義するモデル。
    例: テクノロジー、金融、ヘルスケアなど
    """
    name: str = models.CharField(max_length=100, unique=True)
    description: str = models.TextField(blank=True, help_text="このセクターの説明")

    def __str__(self) -> str:
        return self.name

class SectorTrendScore(models.Model):
    """
    各セクターの日次トレンドスコアを格納するモデル。
    トレンドとは、注目度・感情・出来高・変動率などを指す。
    """
    sector: Sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    date: models.DateField = models.DateField()
    sentiment_score: float = models.FloatField(help_text="感情スコア（-1〜+1）")
    mention_count: int = models.IntegerField(help_text="SNS・ニュース等での出現回数")
    volume_change_pct: float = models.FloatField(help_text="前日比での出来高変化率（%）")
    volatility: float = models.FloatField(help_text="価格のボラティリティ（標準偏差や変動幅など）")
    news_keywords: dict = models.JSONField(blank=True, default=list, help_text="関連ニュースキーワードリスト")

    class Meta:
        unique_together = ("sector", "date")
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.sector.name} @ {self.date}"

class SectorFactor(models.Model):
    """
    セクターのファンダメンタルズ指標を保存するモデル。
    主にPER、EPS成長率、時価総額、地政学リスクなど。
    """
    sector: Sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    date: models.DateField = models.DateField()
    avg_per: float = models.FloatField(help_text="平均PER（株価収益率）")
    avg_eps_growth: float = models.FloatField(help_text="平均EPS成長率（%）")
    avg_market_cap: int = models.BigIntegerField(help_text="平均時価総額（円 or ドル単位）")
    geopolitical_risk_score: float = models.FloatField(help_text="地政学的リスクスコア（0〜1）")

    class Meta:
        unique_together = ("sector", "date")
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"Factors for {self.sector.name} on {self.date}"
