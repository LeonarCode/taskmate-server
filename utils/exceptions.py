class AppError(Exception):
    """Base class ng lahat ng business errors."""

class NotFoundError(AppError):
    pass

class BadRequestError(AppError):
    pass

class ForbiddenError(AppError):
    """Naka-login at may access, pero hindi puwede ang ginagawa (hal. member na magbura ng task ng server)."""

class EmailAlreadyExistsError(AppError):
    pass

class UsernameAlreadyExistsError(AppError):
    pass

class InvalidCredentialsError(AppError):
    pass

class UnauthorizedError(AppError):
    pass

class UserNotFoundError(AppError):
    pass

class InvalidResetCodeError(AppError):
    pass

class FileTooLargeError(AppError):
    pass

class StorageError(AppError):
    """Hindi maabot o hindi tanggap ng image storage (Cloudinary); puwedeng subukan ulit."""
