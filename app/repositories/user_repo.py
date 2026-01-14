from app.repositories.user_repo_accounts import UserRepoAccountsMixin
from app.repositories.user_repo_admin import UserRepoAdminMixin
from app.repositories.user_repo_otp import UserRepoOtpMixin
from app.repositories.user_repo_transactions import UserRepoTransactionsMixin
from app.repositories.user_repo_users import UserRepoUsersMixin


class UserRepository(
    UserRepoUsersMixin,
    UserRepoOtpMixin,
    UserRepoAdminMixin,
    UserRepoAccountsMixin,
    UserRepoTransactionsMixin,
):
    pass
