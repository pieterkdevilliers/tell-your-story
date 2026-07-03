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


class StoryRequesterNotAllowedError(Exception):
    pass


class UserTypeNotAllowedError(Exception):
    pass


class StorytellerAlreadyExistsError(Exception):
    pass


class NoStorytellerYetError(Exception):
    pass


class InvalidInviteTokenError(Exception):
    pass


class AccountNotAccessibleError(Exception):
    pass


class QuestionNotFoundError(Exception):
    pass
