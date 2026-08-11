from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
 
 
class UserManager(BaseUserManager):
    def create_user(self, email, name, user_type, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        user = self.model(
            email=self.normalize_email(email),
            name=name,
            user_type=user_type,
            **extra_fields,
        )
        if password:
            user.set_password(password)
        else:
            # 소셜로그인 유저는 비밀번호 없이 생성
            user.set_unusable_password()
        user.save(using=self._db)
        return user
 
    def create_superuser(self, email, name, user_type=None, password=None, **extra_fields):
      extra_fields.setdefault("is_staff", True)
      extra_fields.setdefault("is_superuser", True)
      user_type = user_type or self.model.UserType.MOTHER
      return self.create_user(email, name, user_type, password=password, **extra_fields)
 
class User(AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        MOTHER = "mother", "산모"
        GUARDIAN = "guardian", "보호자"
 
    user_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=255, unique=True)
    # ERD상 NOT NULL이지만 소셜로그인 계정은 unusable password로 대체
    password = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, null=True, blank=True)
    user_type = models.CharField(max_length=10, choices=UserType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
 
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
 
    objects = UserManager()
 
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "user_type"]
 
    class Meta:
        db_table = "user"
 
    def __str__(self):
        return f"{self.name}({self.user_type})"
 
 
class SocialAccount(models.Model):
    """
    소셜로그인 연동 정보. ERD엔 없지만 카카오/네이버 등
    provider별 고유 id를 저장해두지 않으면 재로그인 매칭이 어려움.
    """
    class Provider(models.TextChoices):
        KAKAO = "kakao", "카카오"
        NAVER = "naver", "네이버"
 
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = "social_account"
        unique_together = ("provider", "provider_user_id")