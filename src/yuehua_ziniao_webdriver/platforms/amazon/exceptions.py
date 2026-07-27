"""Amazon Seller Central platform exceptions."""


class AmazonError(RuntimeError):
    """Base exception for Amazon platform automation."""


class AmazonLoginRequired(AmazonError):  # noqa: N818 - public compatibility name
    """Raised when an automated sign-in step cannot be completed."""


class AmazonMarketplaceError(AmazonError):
    """Raised when a marketplace cannot be selected or verified."""


class AmazonLocaleError(AmazonError):
    """Raised when the Seller Central locale cannot be selected or verified."""
