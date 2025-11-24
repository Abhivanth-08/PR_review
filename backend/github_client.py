"""
GitHub API client for fetching PR data
"""
import requests
from typing import Optional, Dict, List
from models import PRMetadata, FileChange
import re


class GitHubClient:

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def parse_pr_url(self, url: str) -> Optional[Dict[str, str]]:
        """Parse GitHub PR URL to extract owner, repo, and PR number"""
        # Pattern: https://github.com/owner/repo/pull/123
        pattern = r'github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        match = re.search(pattern, url)

        if match:
            return {
                'owner': match.group(1),
                'repo': match.group(2),
                'pr_number': match.group(3)
            }
        return None

    def fetch_pr_metadata(self, owner: str, repo: str, pr_number: int) -> Optional[PRMetadata]:
        """Fetch PR metadata from GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return PRMetadata(
                pr_number=pr_number,
                title=data.get('title', ''),
                description=data.get('body', ''),
                author=data.get('user', {}).get('login', ''),
                branch=data.get('head', {}).get('ref', ''),
                files_changed=data.get('changed_files', 0),
                additions=data.get('additions', 0),
                deletions=data.get('deletions', 0)
            )
        except Exception as e:
            print(f"Error fetching PR metadata: {e}")
            return None

    def fetch_pr_files(self, owner: str, repo: str, pr_number: int) -> List[FileChange]:
        """Fetch files changed in PR"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            files_data = response.json()

            file_changes = []
            for file_data in files_data:
                file_change = FileChange(
                    filename=file_data.get('filename', ''),
                    additions=file_data.get('additions', 0),
                    deletions=file_data.get('deletions', 0),
                    patch=file_data.get('patch', ''),
                    status=file_data.get('status', 'modified')
                )
                file_changes.append(file_change)

            return file_changes
        except Exception as e:
            print(f"Error fetching PR files: {e}")
            return []

    def fetch_pr_diff(self, owner: str, repo: str, pr_number: int) -> Optional[str]:
        """Fetch unified diff for entire PR"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching PR diff: {e}")
            return None

    def post_review_comment(
            self,
            owner: str,
            repo: str,
            pr_number: int,
            body: str,
            commit_id: Optional[str] = None,
            path: Optional[str] = None,
            position: Optional[int] = None
    ) -> bool:
        """Post a review comment on GitHub PR"""
        if not self.token:
            print("GitHub token required to post comments")
            return False

        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"

        payload = {
            "body": body
        }

        if commit_id:
            payload["commit_id"] = commit_id
        if path:
            payload["path"] = path
        if position:
            payload["position"] = position

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error posting comment: {e}")
            return False

