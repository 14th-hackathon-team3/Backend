from rest_framework_simplejwt.tokens import RefreshToken
 
 
def issue_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["user_type"] = user.user_type
    return {"access": str(refresh.access_token), "refresh": str(refresh)}