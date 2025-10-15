import os
import time
import logging
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class GitHubAPIClient:
    """Client for fetching GitHub user data from committers.top API."""
    
    BASE_API_URL = "https://committers.top"
    
    def __init__(self, token: str = None):
        """Initialize the client.
        
        Args:
            token: Optional GitHub token (not required for committers.top)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GitHub-Management-App/1.0',
            'Accept': 'application/json',
        })
    
    def _make_request(self, url: str, params: Optional[dict] = None, parse_json: bool = False) -> Any:
        """Make a request to the committers.top website.
        
        Args:
            url: Full URL or endpoint to request
            params: Optional query parameters
            parse_json: Whether to parse response as JSON
            
        Returns:
            Parsed response (JSON or BeautifulSoup)
        """
        if not url.startswith('http'):
            url = f"{self.BASE_API_URL}/{url.lstrip('/')}"
            
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            if parse_json:
                return response.json()
                
            # Parse HTML with BeautifulSoup
            return BeautifulSoup(response.text, 'html.parser')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def get_users_by_country(self, country: str, max_users: int = 256) -> List[Dict[str, Any]]:
        """Get top GitHub users by country from committers.top.
        
        Args:
            country: Country name (e.g., 'tanzania')
            max_users: Maximum number of users to return (max 256)
            
        Returns:
            List of user dictionaries with their details
        """
        try:
            # First try to get the main page for the country
            soup = self._make_request(f"{country.lower()}_public")
            
            # Find the users table
            users_table = soup.find('table', class_='users-list')
            if not users_table:
                logger.warning(f"Could not find users table for country: {country}")
                return []
                
            # Extract user data from the table
            users = []
            rows = users_table.find('tbody').find_all('tr')
            
            for i, row in enumerate(rows[:max_users], 1):
                try:
                    # Extract user data from the row
                    cols = row.find_all('td')
                    if len(cols) < 4:  # Ensure we have all columns
                        continue
                        
                    # Get username and profile URL
                    user_link = cols[1].find('a')
                    if not user_link:
                        continue
                        
                    username = user_link.get('href').strip('/')
                    if 'github.com' in username:
                        username = username.split('github.com/')[-1].split('/')[0]
                    
                    # Get user's name (if available)
                    name = None
                    name_span = cols[1].find('span')
                    if name_span:
                        name = name_span.get_text(strip=True).strip('()')
                        # Clean up common patterns
                        name = re.sub(r'\(.*\)', '', name).strip()  # Remove anything in parentheses
                        name = re.sub(r',.*', '', name).strip()  # Remove anything after comma
                        name = re.sub(r'[^\w\s-]', '', name)  # Remove special characters except spaces and hyphens
                    
                    # Get contributions count
                    contributions = 0
                    try:
                        contrib_text = cols[2].get_text(strip=True).replace(',', '')
                        contributions = int(contrib_text) if contrib_text.isdigit() else 0
                    except (ValueError, AttributeError):
                        pass
                    
                    # Get avatar URL
                    avatar_url = ''
                    img = cols[3].find('img')
                    if img and 'data-src' in img.attrs:
                        avatar_url = img['data-src'].split('?')[0]  # Remove query params
                    
                    # Create user data dict
                    user_data = {
                        'username': username,
                        'rank': i,
                        'contributions': contributions,
                        'profile_url': f"https://github.com/{username}",
                        'avatar_url': avatar_url or f"https://github.com/{username}.png"
                    }
                    
                    # Add name if available
                    if name and name.lower() != username.lower():  # Only add if name is different from username
                        # Handle different name formats
                        name = name.strip()
                        
                        # Handle special cases like "DML" or other initials
                        if len(name) <= 3 and name.isupper():
                            first_name = name
                            last_name = ''
                        # Handle names with titles or suffixes (e.g., "Gift Nnko")
                        else:
                            name_parts = name.split()
                            if len(name_parts) >= 2:
                                first_name = name_parts[0]
                                last_name = ' '.join(name_parts[1:])  # Handle multiple last names
                            else:
                                first_name = name
                                last_name = ''
                        
                        user_data.update({
                            'name': name,
                            'first_name': first_name,
                            'last_name': last_name,
                            'followers': 0  # Default value since we don't have this info
                        })
                    
                    users.append(user_data)
                    
                except Exception as e:
                    logger.error(f"Error processing user row {i}: {e}")
                    continue
                    
                # Add a small delay to be nice to the server
                time.sleep(0.2)
                
            return users
            
        except Exception as e:
            logger.error(f"Error getting users for country {country}: {e}")
            return []
    
    def search_users_by_location(self, location: str, page: int = 1, per_page: int = 100) -> Tuple[List[Dict], bool]:
        """Search users by location.
        
        Args:
            location: Location to search for (e.g., 'Tanzania')
            page: Page number (1-based)
            per_page: Number of results per page (max 100)
            
        Returns:
            Tuple of (list of user items, has_next_page)
        """
        try:
            # Get all users for the country (up to 256)
            users = self.get_users_by_country(location.lower())
            
            # Paginate the results
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_users = users[start_idx:end_idx]
            
            # Convert to the expected format
            result = [{
                'login': user['username'],
                'html_url': user['profile_url'],
                'avatar_url': user['avatar_url'],
                'contributions': user.get('contributions', 0),
                'followers': user.get('followers', 0),
                'name': user.get('name', ''),
                'rank': user.get('rank', 0)
            } for user in paginated_users]
            
            has_next = end_idx < len(users)
            return result, has_next
            
        except Exception as e:
            logger.error(f"Error searching users in {location}: {e}")
            return [], False
    
    def get_user_details(self, username: str) -> Optional[Dict]:
        """Get detailed user information.
        
        Args:
            username: GitHub username
            
        Returns:
            Dictionary with user details or None if not found
        """
        try:
            # Try to get user info from GitHub's API
            user_data = self._make_request(f"https://api.github.com/users/{username}", parse_json=True)
            
            if not user_data or 'message' in user_data:  # GitHub returns {'message': 'Not Found'}
                logger.warning(f"User not found on GitHub: {username}")
                return None
                
            # Parse name into first and last name
            full_name = user_data.get('name', '')
            if full_name:
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
            else:
                first_name = last_name = ''
            
            # Build the result with available data
            return {
                'username': username,
                'first_name': first_name or None,
                'last_name': last_name or None,
                'followers': user_data.get('followers', 0),
                'following': user_data.get('following', 0),
                'contributions_last_year': 0,  # Will be updated from the main list
                'profile_url': user_data.get('html_url', f"https://github.com/{username}"),
                'avatar_url': user_data.get('avatar_url', f"https://github.com/{username}.png"),
                'public_repos': user_data.get('public_repos', 0),
                'bio': user_data.get('bio'),
                'company': user_data.get('company'),
                'location': user_data.get('location'),
                'created_at': user_data.get('created_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting details for user {username}: {e}")
            return None
    
    def search_users_by_location(self, location: str, page: int = 1, per_page: int = 100) -> Tuple[List[Dict], bool]:
        """Search GitHub users by location.
        
        Args:
            location: Location to search for (e.g., 'United States')
            page: Page number for pagination
            per_page: Number of results per page (max 100)
            
        Returns:
            Tuple of (list of user items, has_next_page)
        """
        # Search for users with public repositories and sort by repositories count first
        # This helps find more active users who contribute to open source
        query = f'location:"{location}" repos:>0'
        endpoint = f"search/users?q={query}&page={page}&per_page={per_page}&sort=repositories&order=desc"
        
        try:
            data = self._make_rest_request('GET', endpoint)
            users = data.get('items', [])
            
            # Check if there are more pages
            total_count = data.get('total_count', 0)
            has_next_page = (page * per_page) < min(total_count, 1000)  # GitHub limits to 1000 results
            
            return users, has_next_page
            
        except Exception as e:
            logger.error(f"Error searching users in {location}: {e}")
            return [], False
    
    def get_user_details(self, username: str) -> Optional[Dict]:
        """Get detailed user information including contribution stats.
        
        Args:
            username: GitHub username
            
        Returns:
            Dictionary with user details or None if not found
        """
        # GraphQL query with only the essential fields that don't require additional scopes
        query = """
        query($username: String!) {
            user(login: $username) {
                login
                name
                url
                avatarUrl
                repositories(ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER], isFork: false) {
                    totalCount
                }
                repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
                    totalCount
                }
                followers {
                    totalCount
                }
                following {
                    totalCount
                }
                contributionsCollection(
                    from: "%sT00:00:00Z"
                    to: "%sT23:59:59Z"
                ) {
                    totalCommitContributions
                    totalIssueContributions
                    totalPullRequestContributions
                    totalPullRequestReviewContributions
                    totalRepositoryContributions
                    totalRepositoriesWithContributedCommits
                    totalRepositoriesWithContributedPullRequests
                    totalRepositoriesWithContributedIssues
                    contributionCalendar {
                        totalContributions
                    }
                    commitContributionsByRepository(maxRepositories: 10) {
                        contributions(first: 10) {
                            totalCount
                        }
                        repository {
                            nameWithOwner
                            stargazerCount
                            forkCount
                        }
                    }
                }
            }
        }
        """
        
        # Calculate date range for the last year
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365)
        
        # Format dates for the query
        query = query % (
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        try:
            data = self._make_graphql_request(query, {'username': username})
            user_data = data.get('user')
            
            if not user_data:
                return None
                
            # Calculate total contributions (if available in the response)
            contributions = user_data.get('contributionsCollection', {})
            if contributions:
                total_contributions = (
                    contributions.get('totalCommitContributions', 0) +
                    contributions.get('totalIssueContributions', 0) +
                    contributions.get('totalPullRequestContributions', 0) +
                    contributions.get('totalPullRequestReviewContributions', 0)
                )
            else:
                # Fallback to 0 if contributions data is not available
                total_contributions = 0
            
            # Parse name into first and last name
            full_name = user_data.get('name', '')
            if full_name:
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
            else:
                first_name = last_name = None
            
            # Build the result with available data
            result = {
                'username': user_data.get('login', username),
                'first_name': first_name,
                'last_name': last_name,
                'followers': user_data.get('followers', {}).get('totalCount', 0),
                'following': user_data.get('following', {}).get('totalCount', 0),
                'contributions_last_year': total_contributions,
                'profile_url': user_data.get('url', f'https://github.com/{username}'),
                'avatar_url': user_data.get('avatarUrl', '')
            }
            
            # Only return if we have at least some data
            if result['username'] and (result['followers'] > 0 or result['contributions_last_year'] > 0):
                return result
            return None
            
        except Exception as e:
            logger.error(f"Error getting details for user {username}: {e}")
            return None

import requests
from django.conf import settings

class GitHubAPI:
    def __init__(self, token=None):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token or settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get_user(self, username):
        """Get user data including contribution statistics."""
        try:
            # Get basic user info
            user_url = f"{self.base_url}/users/{username}"
            response = requests.get(user_url, headers=self.headers)
            response.raise_for_status()
            user_data = response.json()

            # Get contribution statistics (you'll need to implement this)
            contributions = self.get_contributions(username)
            
            return {
                **user_data,
                'contributions': contributions
            }
        except requests.RequestException as e:
            print(f"Error fetching GitHub user {username}: {e}")
            return None

    def get_contributions(self, username):
        """Get user contribution statistics."""
        # This is a simplified example - you might need to use the GitHub GraphQL API
        # or a service like GitHub Archive for more detailed stats
        return {
            'last_year': 0,  # Implement actual calculation
            'total': 0
        }