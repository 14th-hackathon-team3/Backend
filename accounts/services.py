from .models import User, SocialAccount
from .oauth_clients import OAUTH_CLIENTS
 
 
class SignupRequiredError(Exception):
    pass
 
 
class SocialLoginService:
    def __init__(self, provider: str):
        if provider not in OAUTH_CLIENTS:
            raise ValueError(f"지원하지 않는 provider: {provider}")
        self.provider = provider
        self.client = OAUTH_CLIENTS[provider]
 
    def login_or_signup(self, code: str, user_type: str = None):
        access_token = self.client.get_access_token(code)
        user_info = self.client.get_user_info(access_token)
 
        social_account = (
            SocialAccount.objects
            .filter(provider=self.provider, provider_user_id=user_info["provider_user_id"])
            .select_related("user")
            .first()
        )
        if social_account:
            return social_account.user, False
 
        if not user_type:
            raise SignupRequiredError("최초 로그인입니다. user_type을 포함해 다시 요청해주세요.")
 
        # TODO: groups 앱 만들면 여기서 user_type에 따라 Group/Membership 생성 로직 추가
        # (지난번 논의한 transaction.atomic() 블록 - mother는 group 생성, guardian은 invite_code로 가입)
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
        return user, True