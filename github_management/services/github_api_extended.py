import requests
import logging
from django.conf import settings
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class GitHubAPIExtended:
    """Extended GitHub API client for rich data collection."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token=None):
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API Error ({endpoint}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    def get_repositories(self, username: str, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """Fetch public repositories for a user."""
        return self._get(f"users/{username}/repos", params={
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }) or []

    def get_events(self, username: str, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """Fetch public events for a user."""
        return self._get(f"users/{username}/events/public", params={
            "page": page,
            "per_page": per_page
        }) or []

    def get_organization(self, org_login: str) -> Optional[Dict[str, Any]]:
        """Fetch organization details."""
        return self._get(f"orgs/{org_login}")

    def get_repo_languages(self, owner: str, repo_name: str) -> Dict[str, int]:
        """Fetch languages used in a repository."""
        return self._get(f"repos/{owner}/{repo_name}/languages") or {}

    def get_repo_topics(self, owner: str, repo_name: str) -> List[str]:
        """Fetch topics for a repository."""
        data = self._get(f"repos/{owner}/{repo_name}/topics")
        return data.get('names', []) if data else []
