import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from ..base import RagflowAPIBase, ServerError, UnauthorizedError
from .dto import UpdateTenantInfoRequest, UpdateUserSettingRequest, UserInfoResponse


class UserRagflowAPI(RagflowAPIBase):
    """
    User authentication and management API.

    Provides methods for user registration, login, token retrieval, and team information.
    """

    def __init__(self, hostname: str, public_key: str = None, public_key_path: str = None, version: str = "v1"):
        """Initialize the User API client."""
        super().__init__(hostname, public_key, public_key_path, version)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def register_user(self, email: str, nickname: str, password: str) -> bool:
        """
        Register a new user account.

        Args:
            email: User's email address
            nickname: User's display name
            password: User's password (will be encrypted before transmission)

        Returns:
            True if registration successful, False otherwise

        Example:
            >>> api = UserRagflowAPI("http://localhost:9380")
            >>> success = await api.register_user("user@example.com", "John Doe", "password123")
        """
        url = f"{self.base_url}/user/register"
        encrypted_password = self._encrypt_password(password)
        payload = {"email": email, "nickname": nickname, "password": encrypted_password}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    return False
                res_json = await response.json()
                if res_json.get("code") == 0:
                    return True
                return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def login(self, email: str, password: str) -> dict:
        """
        Authenticate a user and retrieve login information.

        Args:
            email: User's email address
            password: User's password (will be encrypted before transmission)

        Returns:
            Dictionary containing user data and access_token

        Raises:
            UnauthorizedError: If login credentials are invalid
            ServerError: If server returns non-200 status

        Example:
            >>> api = UserRagflowAPI("http://localhost:9380")
            >>> login_data = await api.login("user@example.com", "password123")
            >>> token = login_data["access_token"]
        """
        url = f"{self.base_url}/user/login"
        encrypted_password = self._encrypt_password(password)
        payload = {"email": email, "password": encrypted_password}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    raise ServerError(f"Login failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise UnauthorizedError(f"Login failed: {res_json.get('message')}")

                # Extract token from header and add to result
                token = response.headers.get("Authorization")
                res_data = res_json.get("data", {})
                if token:
                    res_data["access_token"] = token
                return res_data

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_token(self, email: str, password: str) -> str:
        """
        Authenticate a user and retrieve only the access token.

        This is a convenience method that calls login() and extracts the token.

        Args:
            email: User's email address
            password: User's password (will be encrypted before transmission)

        Returns:
            Access token string

        Raises:
            UnauthorizedError: If login credentials are invalid
            ValueError: If token is not found in response

        Example:
            >>> api = UserRagflowAPI("http://localhost:9380")
            >>> token = await api.get_token("user@example.com", "password123")
        """
        auth_data = await self.login(email, password)
        token = auth_data.get("access_token")
        if not token:
            raise ValueError("Login successful but no token found in response.")
        return token

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_team_info(self, token: str) -> dict:
        """
        Retrieve tenant/team information for the authenticated user.

        Args:
            token: Valid authentication token

        Returns:
            Dictionary containing tenant information including tenant_id, role, etc.

        Raises:
            UnauthorizedError: If token is invalid
            ServerError: If server returns non-200 status

        Example:
            >>> api = UserRagflowAPI("http://localhost:9380")
            >>> token = await api.get_token("user@example.com", "password123")
            >>> team_info = await api.get_team_info(token)
            >>> tenant_id = team_info["tenant_id"]
        """
        url = f"{self.base_url}/user/tenant_info"
        headers = {"Authorization": token}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Failed to get team info, status: {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise UnauthorizedError(f"Failed to get team info: {res_json.get('message')}")
                return res_json.get("data", {})

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def update_tenant_info(self, token: str, req: UpdateTenantInfoRequest) -> bool:
        """
        Update tenant information.

        Args:
            token: Valid authentication token
            req: UpdateTenantInfoRequest object

        Returns:
            True if successful

        Raises:
            UnauthorizedError: If token is invalid
            ServerError: If server returns non-200 status
        """
        # Fetch current tenant info to support partial updates and satisfy server validation
        current_info = await self.get_team_info(token)

        # Prepare full payload
        payload = {
            "tenant_id": req.tenant_id,
            "llm_id": req.llm_id if req.llm_id is not None else current_info.get("llm_id"),
            "embd_id": req.embd_id if req.embd_id is not None else current_info.get("embd_id"),
            "asr_id": req.asr_id if req.asr_id is not None else current_info.get("asr_id"),
            "img2txt_id": req.img2txt_id if req.img2txt_id is not None else current_info.get("img2txt_id")
        }

        url = f"{self.base_url}/user/set_tenant_info"
        headers = {"Authorization": token}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Failed to update tenant info, status: {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise UnauthorizedError(f"Failed to update tenant info: {res_json.get('message')}")
                return res_json.get("data", False)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def logout(self, token: str) -> bool:
        """
        Logout the current user.

        Args:
            token: Valid authentication token

        Returns:
            True if successful
        """
        url = f"{self.base_url}/user/logout"
        headers = {"Authorization": token}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Failed to logout, status: {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise UnauthorizedError(f"Failed to logout: {res_json.get('message')}")
                return res_json.get("data", False)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def update_user_setting(self, token: str, req: UpdateUserSettingRequest) -> bool:
        """
        Update user settings.

        Args:
            token: Valid authentication token
            req: UpdateUserSettingRequest object

        Returns:
            True if successful
        """
        url = f"{self.base_url}/user/setting"
        headers = {"Authorization": token}
        payload = req.model_dump(exclude_none=True)
        if req.password:
            payload["password"] = self._encrypt_password(req.password)
        if req.new_password:
            payload["new_password"] = self._encrypt_password(req.new_password)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Failed to update user settings, status: {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise UnauthorizedError(f"Failed to update user settings: {res_json.get('message')}")
                return res_json.get("data", False)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_api_key(self, token: str) -> str:
        """
        Get or create an API key for the authenticated user, to be used with SDK endpoints.

        The `/v1/retrieval` and other SDK endpoints require an API key (not a user session token).
        This method fetches or creates an API key using the user's session token.

        Args:
            token: Valid user session authentication token (from get_token())

        Returns:
            API key string in 'Bearer ragflow-xxxx' format suitable for SDK endpoints

        Example:
            >>> token = await api.get_token("user@example.com", "password")
            >>> api_key = await api.get_api_key(token)
            >>> results = await api.search.retrieval(req, api_key)
        """
        # Try to list existing API tokens first
        url = f"{self.hostname}/v1/system/token_list"
        headers = {"Authorization": token}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    res_json = await response.json()
                    if res_json.get("code") == 0:
                        tokens = res_json.get("data", [])
                        if tokens:
                            # Return the first existing API key
                            existing_token = tokens[0].get("token", "")
                            if existing_token:
                                return f"Bearer {existing_token}"

        # No existing token found, create a new one
        url = f"{self.hostname}/v1/system/new_token"
        headers = {"Authorization": token}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={}, headers=headers) as response:
                if response.status != 200:
                    raise ServerError(f"Get API key failed with status {response.status}")
                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise ValueError(f"Failed to create API key: {res_json.get('message')}")
                new_token = res_json.get("data", {}).get("token", "")
                if not new_token:
                    raise ValueError("API key creation succeeded but no token returned")
                return f"Bearer {new_token}"

