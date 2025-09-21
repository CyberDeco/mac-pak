import urllib.request
import json
import re
from packaging import version
from ..version import get_version_info

class UpdateChecker:
    def __init__(self):
        self.version_info = get_version_info()
        self.github_api_url = f"https://api.github.com/repos/{self.version_info['github_repo']}/releases/latest"
    
    def check_for_updates(self):
        """Check if a newer version is available"""
        try:
            with urllib.request.urlopen(self.github_api_url, timeout=10) as response:
                release_data = json.loads(response.read().decode())
            
            latest_version = release_data['tag_name'].lstrip('v')
            current_version = self.version_info['version']
            
            is_newer = version.parse(latest_version) > version.parse(current_version)
            
            return {
                'update_available': is_newer,
                'current_version': current_version,
                'latest_version': latest_version,
                'download_url': self._get_mac_download_url(release_data),
                'release_notes': release_data.get('body', ''),
                'release_date': release_data.get('published_at', '')
            }
            
        except Exception as e:
            return {
                'update_available': False,
                'error': str(e)
            }
    
    def _get_mac_download_url(self, release_data):
        """Find the macOS download URL from release assets"""
        for asset in release_data.get('assets', []):
            name = asset['name'].lower()
            if any(term in name for term in ['macos', 'mac', 'osx', 'darwin']) and name.endswith('.dmg'):
                return asset['browser_download_url']
        return None