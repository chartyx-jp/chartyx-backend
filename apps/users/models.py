from django.db import models

class Member(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'
    
    class Plan(models.TextChoices):
        FREE = 'F', 'Free'
        BASIC = 'B', 'Basic'
        PREMIUM = 'P', 'Premium'

    # userId = models.PositiveIntegerField(unique=True)  # INT UNSIGNED
    firstName = models.CharField(max_length=50, null=True, blank=True)
    lastName = models.CharField(max_length=50 , null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    emailAddress = models.EmailField(unique=True, max_length=254)  # ユニークなメールアドレス
    phoneNumber = models.CharField(max_length=15, blank=True, null=True)
    password = models.CharField(max_length=64)
    address = models.TextField(blank=True, null=True)
    plan = models.CharField(max_length=1, choices=Plan.choices, default=Plan.FREE, null=True) #プラン情報
    userRegistrationDate = models.DateTimeField(auto_now_add=True)
    subscriptionRegistrationDate = models.DateTimeField(blank=True, null=True)
    status = models.BooleanField(default=True)  # ステータス（アクティブ/非アクティブ）

    def __str__(self):
        return f"{self.firstName} {self.lastName}"
    
class Favorite(models.Model):
    userId = models.ForeignKey(Member, on_delete=models.CASCADE) # 外部キー
    brand = models.CharField(max_length=50)
    favoriteDate = models.DateTimeField(auto_now_add=True)

class GraphData(models.Model):
    GraphId = models.PositiveIntegerField(unique=True)  # INT UNSIGNED
    # グラフの情報たち
    oresengurahu = models.CharField(max_length=50)  # グラフの種類

class GraphDisplay(models.Model):
    userId = models.ForeignKey(Member, on_delete=models.CASCADE)
    graphId = models.ForeignKey(GraphData, on_delete=models.CASCADE)
    graphRegistrationDate = models.DateTimeField(auto_now_add=True)