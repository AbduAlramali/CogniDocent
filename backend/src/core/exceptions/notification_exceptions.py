class NotificationError(Exception):
    """Base exception for notification-related errors."""

    pass


class NotificationSendError(NotificationError):
    """Raised when a notification fails to be sent."""

    pass


class NotificationSubscriptionError(NotificationError):
    """Raised when a subscription to notifications fails."""

    pass
