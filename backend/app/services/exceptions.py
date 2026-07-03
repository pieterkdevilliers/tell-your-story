from app.models.user import User


class EmailAlreadyExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class LastOwnerError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidResetTokenError(Exception):
    pass


class AmbiguousAccountError(Exception):
    def __init__(self, candidates: list[User]):
        self.candidates = candidates
        super().__init__("Email matches users in multiple accounts")
