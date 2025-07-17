from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class MemberManager(BaseUserManager):
    def create_user(self, emailAddress, password=None, **extra_fields):
        if not emailAddress:
            raise ValueError('メールアドレスは必須です')
        emailAddress = self.normalize_email(emailAddress)
        user = self.model(emailAddress=emailAddress, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, emailAddress, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(emailAddress, password, **extra_fields)

class Member(AbstractBaseUser, PermissionsMixin):
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'

    class Plan(models.TextChoices):
        FREE = 'F', 'Free'
        BASIC = 'B', 'Basic'
        PREMIUM = 'P', 'Premium'

    firstName = models.CharField(max_length=50, null=True, blank=True)
    lastName = models.CharField(max_length=50, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    emailAddress = models.EmailField(unique=True, max_length=254)
    phoneNumber = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    plan = models.CharField(max_length=1, choices=Plan.choices, default=Plan.FREE, null=True)
    userRegistrationDate = models.DateTimeField(auto_now_add=True)
    subscriptionRegistrationDate = models.DateTimeField(blank=True, null=True)
    status = models.BooleanField(default=True)

    # 追加（管理フラグ）
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Djangoのユーザー管理設定
    USERNAME_FIELD = 'emailAddress'       # ログインIDにするフィールド名
    REQUIRED_FIELDS = []                  # createsuperuser時の追加入力フィールド
    objects = MemberManager()

    def __str__(self):
        return f"{self.firstName} {self.lastName}"

    def get_full_name(self):
        return f"{self.firstName} {self.lastName}".strip()

    def get_short_name(self):
        return self.firstName or self.emailAddress

    
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