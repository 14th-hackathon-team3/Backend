import requests
from django.conf import settings
 
 
class OAuthClient:
    provider = None
 
    def get_access_token(self, code: str) -> str:
        raise NotImplementedError
 
    def get_user_info(self, access_token: str) -> dict:
        """반환: {"provider_user_id": str, "email": str|None, "name": str|None}"""
        raise NotImplementedError
 
 
class KakaoOAuthClient(OAuthClient):
    provider = "kakao"
 
    def get_access_token(self, code: str) -> str:
        resp = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_CLIENT_ID,
                "client_secret": settings.KAKAO_CLIENT_SECRET,
                "redirect_uri": settings.KAKAO_REDIRECT_URI,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
 
    def get_user_info(self, access_token: str) -> dict:
        resp = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        kakao_account = data.get("kakao_account", {})
        return {
            "provider_user_id": str(data["id"]),
            "email": kakao_account.get("email"),
            "name": kakao_account.get("profile", {}).get("nickname"),
        }
 
 
class NaverOAuthClient(OAuthClient):
    provider = "naver"
 
    def get_access_token(self, code: str) -> str:
        resp = requests.post(
            "https://nid.naver.com/oauth2.0/token",
            params={
                "grant_type": "authorization_code",
                "client_id": settings.NAVER_CLIENT_ID,
                "client_secret": settings.NAVER_CLIENT_SECRET,
                "code": code,
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
 
    def get_user_info(self, access_token: str) -> dict:
        resp = requests.get(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()["response"]
        return {
            "provider_user_id": data["id"],
            "email": data.get("email"),
            "name": data.get("name"),
        }
 
 
OAUTH_CLIENTS = {"kakao": KakaoOAuthClient(), "naver": NaverOAuthClient()}