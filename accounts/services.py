from datetime import timedelta
 
from django.db import transaction
from django.utils import timezone
 
from .models import User, SocialAccount
from .oauth_clients import OAUTH_CLIENTS
from groups.models import Group, Membership
 
 
class SignupRequiredError(Exception):
    """신규 유저인데 user_type이 없어서 가입 진행 불가"""
 
 
class InvalidInviteCodeError(Exception):
    """보호자 가입 시 초대코드 문제"""
 
 
def create_group_membership_for_signup(user, invite_code=None):
    """
    유저 생성 '직후' user_type에 따라 Group/Membership을 만든다.
    반드시 유저 생성과 같은 transaction.atomic() 블록 안에서 호출할 것
    (일반 회원가입 / 소셜로그인 신규가입 양쪽에서 공용으로 사용).
    """
    if user.user_type == User.UserType.MOTHER:
        group = Group.objects.create(
            owner_user=user,
            invite_code_expired_at=timezone.now() + timedelta(hours=72),
        )
        Membership.objects.create(
            group=group,
            user=user,
            role=Membership.Role.OWNER,
            data_scope=Membership.DataScope.FULL,
            is_primary=False,
        )
    else:  # GUARDIAN
        if not invite_code:
            raise InvalidInviteCodeError("보호자 가입에는 초대코드가 필요합니다.")
 
        group = Group.objects.select_for_update().filter(invite_code=invite_code).first()
        if not group:
            raise InvalidInviteCodeError("존재하지 않는 초대코드입니다.")
        if not group.is_invite_code_valid():
            raise InvalidInviteCodeError("만료된 초대코드입니다.")
        if Membership.objects.filter(group=group, user=user).exists():
            raise InvalidInviteCodeError("이미 가입된 그룹입니다.")
 
        Membership.objects.create(
            group=group,
            user=user,
            role=Membership.Role.MEMBER,
            data_scope=Membership.DataScope.FULL,
        )
 
 
class SocialLoginService:
    def __init__(self, provider: str):
        if provider not in OAUTH_CLIENTS:
            raise ValueError(f"지원하지 않는 provider: {provider}")
        self.provider = provider
        self.client = OAUTH_CLIENTS[provider]
 
    def login_or_signup(self, code: str, user_type: str = None, invite_code: str = None):
        access_token = self.client.get_access_token(code)
        user_info = self.client.get_user_info(access_token)
 
        social_account = (
            SocialAccount.objects
            .filter(provider=self.provider, provider_user_id=user_info["provider_user_id"])
            .select_related("user")
            .first()
        )
        if social_account:
            return social_account.user, False  # 기존 회원 -> 로그인만
 
        if not user_type:
            raise SignupRequiredError("최초 로그인입니다. user_type을 포함해 다시 요청해주세요.")
 
        with transaction.atomic():
            user = User.objects.create_user(
                email=user_info.get("email") or f"{self.provider}_{user_info['provider_user_id']}@social.local",
                name=user_info.get("name") or "사용자",
                user_type=user_type,
            )
            SocialAccount.objects.create(
                user=user,
                provider=self.provider,
                provider_user_id=user_info["provider_user_id"],
            )
            create_group_membership_for_signup(user, invite_code=invite_code)
 
        return user, True