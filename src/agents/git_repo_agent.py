"""
Git Repository Agent
Clones a git repository into a temp directory and extracts structure information
"""

import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent

_CONFIG_FILES = [
    'Dockerfile',
    'docker-compose.yml',
    'Makefile',
    'package.json',
    'pyproject.toml',
    'requirements.txt',
    'setup.py',
    'go.mod',
    'Cargo.toml',
]
_CONFIG_DIRS = ['.github/workflows']
_README_CANDIDATES = ['README.md', 'README.rst', 'README.txt', 'README']
_MAX_TREE_ENTRIES = 200
_README_MAX_CHARS = 2000
_MAX_DEPTH = 3
_TOP_LANGS = 5


class GitRepoAgent(BaseAgent):
    """Sub-agent to clone a git repository and extract its structure"""

    def __init__(self):
        super().__init__(
            name="git_repo",
            description="Clones a git repository and extracts structure, README, and key config files"
        )

    def execute(self, repo_url: str = None, branch: str = None, depth: int = 1, **kwargs) -> Dict[str, Any]:
        if not repo_url:
            return {'success': False, 'error': 'repo_url is required'}

        tmp_dir = tempfile.mkdtemp(prefix='git_repo_agent_')
        try:
            cmd = ['git', 'clone', '--depth', str(depth), '--single-branch']
            if branch:
                cmd += ['--branch', branch]
            cmd += [repo_url, tmp_dir]

            clone_result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if clone_result.returncode != 0:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return {'success': False, 'error': clone_result.stderr.strip()}

            branch_name = self._get_branch(tmp_dir, branch)
            file_tree, total_files, total_dirs = self._build_tree(tmp_dir)
            readme = self._read_readme(tmp_dir)
            config_files = self._find_config_files(tmp_dir)
            lang_stats = self._language_stats(file_tree)

            # Keep the cloned directory so the model can tell the user its path
            return {
                'success': True,
                'data': {
                    'repo_url': repo_url,
                    'clone_path': tmp_dir,
                    'branch': branch_name,
                    'total_files': total_files,
                    'total_dirs': total_dirs,
                    'file_tree': file_tree,
                    'readme': readme,
                    'config_files_present': config_files,
                    'language_stats': lang_stats,
                }
            }
        except subprocess.TimeoutExpired:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {'success': False, 'error': 'git clone timed out after 30 seconds'}
        except Exception as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {'success': False, 'error': str(e)}

    def _get_branch(self, repo_dir: str, fallback: Optional[str]) -> str:
        result = subprocess.run(
            ['git', '-C', repo_dir, 'branch', '--show-current'],
            capture_output=True, text=True
        )
        return result.stdout.strip() or fallback or 'unknown'

    def _build_tree(self, repo_dir: str):
        file_tree = []
        total_files = 0
        total_dirs = 0

        for dirpath, dirnames, filenames in os.walk(repo_dir):
            # Skip .git entirely
            dirnames[:] = [d for d in dirnames if d != '.git']

            rel_dir = os.path.relpath(dirpath, repo_dir)
            depth = 0 if rel_dir == '.' else rel_dir.count(os.sep) + 1

            if depth > _MAX_DEPTH:
                dirnames.clear()
                continue

            if rel_dir != '.':
                total_dirs += 1

            for fname in filenames:
                total_files += 1
                if len(file_tree) < _MAX_TREE_ENTRIES:
                    rel_path = os.path.join(rel_dir, fname) if rel_dir != '.' else fname
                    file_tree.append(rel_path)

        return file_tree, total_files, total_dirs

    def _read_readme(self, repo_dir: str) -> Optional[str]:
        for name in _README_CANDIDATES:
            path = os.path.join(repo_dir, name)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        return f.read(_README_MAX_CHARS)
                except OSError:
                    pass
        return None

    def _find_config_files(self, repo_dir: str) -> list:
        found = []
        for name in _CONFIG_FILES:
            if os.path.exists(os.path.join(repo_dir, name)):
                found.append(name)
        for rel_dir in _CONFIG_DIRS:
            if os.path.isdir(os.path.join(repo_dir, rel_dir)):
                found.append(rel_dir)
        return found

    def _language_stats(self, file_tree: list) -> dict:
        counts = Counter()
        for path in file_tree:
            _, ext = os.path.splitext(path)
            if ext:
                counts[ext.lstrip('.')] += 1
        return dict(counts.most_common(_TOP_LANGS))
