from abc import ABC
from pathlib import Path

try:
    from Cryptodome.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5  # type: ignore
    from Cryptodome.PublicKey import RSA  # type: ignore
except ImportError:
    from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5  # type: ignore
    from Crypto.PublicKey import RSA  # type: ignore
import base64


class RagflowAPIError(Exception):
    """Base exception for all RAGFlow API errors."""

    pass


class UnauthorizedError(RagflowAPIError):
    """Raised when authentication fails or token is invalid (HTTP 401)."""

    pass


class ForbiddenError(RagflowAPIError):
    """Raised when access to a resource is forbidden (HTTP 403)."""

    pass


class NotFoundError(RagflowAPIError):
    """Raised when a requested resource is not found (HTTP 404)."""

    pass


class BadRequestError(RagflowAPIError):
    """Raised when the request is malformed or invalid (HTTP 400)."""

    pass


class ValidationError(RagflowAPIError):
    """Raised when request data fails validation."""

    pass


class ServerError(RagflowAPIError):
    """Raised when the server encounters an internal error (HTTP 5xx)."""

    pass


class TimeoutError(RagflowAPIError):
    """Raised when a request times out."""

    pass


class RagflowAPIBase(ABC):
    """
    Base class for all RAGFlow API modules.

    Provides common functionality including:
    - URL construction
    - Public key management for password encryption
    - Token validation decorator
    - Password encryption utilities

    Args:
        hostname: The RAGFlow server hostname (e.g., "http://localhost:9380")
        public_key: Optional RSA public key string. If not provided, will attempt to load from public_key_path
        public_key_path: Optional path to public key file. Defaults to "conf/public.pem" relative to project root
        version: API version string (default: "v1")

    Example:
        >>> api = UserRagflowAPI("http://localhost:9380")
        >>> # Or with custom public key
        >>> api = UserRagflowAPI("http://localhost:9380", public_key="-----BEGIN PUBLIC KEY-----...")
    """

    def __init__(self, hostname: str, public_key: str = None, public_key_path: str = None, version: str = "v1"):
        self.hostname = hostname
        self.base_url = f"{hostname}/{version}"

        # Load public key from file or use provided key or fallback to default
        if public_key:
            self.public_key = public_key
        elif public_key_path:
            self.public_key = self._load_public_key_from_file(public_key_path)
        else:
            # Try to load from default location
            default_path = Path("conf/public.pem")
            if default_path.exists():
                self.public_key = self._load_public_key_from_file(str(default_path))
            else:
                # Fallback to hardcoded default key
                self.public_key = (
                    "-----BEGIN PUBLIC KEY-----\n"
                    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/"
                    "z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp"
                    "2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOO"
                    "UEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVK"
                    "RNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK"
                    "6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs"
                    "2wIDAQAB\n"
                    "-----END PUBLIC KEY-----"
                )

    @staticmethod
    def _load_public_key_from_file(file_path: str) -> str:
        """
        Load RSA public key from a PEM file.

        Args:
            file_path: Path to the public key file

        Returns:
            Public key as a string

        Raises:
            FileNotFoundError: If the key file doesn't exist
            ValueError: If the key file is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Public key file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            raise ValueError(f"Failed to read public key from {file_path}: {e}")

    @staticmethod
    def requires_token(func):
        """
        Decorator to ensure a valid token is provided to API methods.

        Raises:
            ValueError: If no token is provided in kwargs or args
        """

        async def wrapper(self, *args, **kwargs):
            # Check if token is in kwargs
            token = kwargs.get("token", None)
            # If not in kwargs, check positional arguments
            # Token can be first arg (for methods like list_invitations)
            # or second arg (for methods like create_dataset that have a request object first)
            if not token and len(args) > 0:
                token = args[0]
            if not token and len(args) > 1:
                token = args[1]
            if not token:
                raise ValueError("A valid token is required to perform this action.")
            return await func(self, *args, **kwargs)

        return wrapper

    def _encrypt_password(self, password: str) -> str:
        """
        Encrypt a password using RSA public key encryption.

        The password is first base64 encoded, then encrypted with the RSA public key,
        and finally base64 encoded again for transmission.

        Args:
            password: Plain text password to encrypt

        Returns:
            Base64 encoded encrypted password

        Raises:
            ValueError: If encryption fails
        """
        try:
            pub_key = RSA.importKey(self.public_key)
            cipher = Cipher_pkcs1_v1_5.new(pub_key)
            cipher_text = cipher.encrypt(base64.b64encode(password.encode("utf-8")))
            return base64.b64encode(cipher_text).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to encrypt password: {e}")
