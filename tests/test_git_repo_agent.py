"""Unit tests for GitRepoAgent."""
import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock, mock_open, call
from agents.git_repo_agent import GitRepoAgent


@pytest.fixture
def agent():
    return GitRepoAgent()


def _clone_ok():
    m = MagicMock()
    m.returncode = 0
    m.stderr = ''
    return m


def _clone_fail(stderr='fatal: repository not found'):
    m = MagicMock()
    m.returncode = 128
    m.stderr = stderr
    return m


def _branch_result(name='main'):
    m = MagicMock()
    m.stdout = name + '\n'
    return m


def _fake_walk(root, files_by_dir):
    """Produce os.walk tuples rooted at `root`."""
    for rel_dir, fnames in files_by_dir.items():
        dirpath = os.path.join(root, rel_dir) if rel_dir != '.' else root
        yield dirpath, [], fnames


# --- basic attributes ---

def test_agent_name(agent):
    assert agent.name == 'git_repo'


def test_agent_description_non_empty(agent):
    assert isinstance(agent.description, str) and len(agent.description) > 0


# --- missing repo_url ---

def test_execute_missing_repo_url_returns_error(agent):
    result = agent.execute()
    assert result['success'] is False
    assert 'repo_url' in result['error']


# --- clone failure ---

def test_execute_clone_failure_returns_error(agent):
    with patch('agents.git_repo_agent.subprocess.run', side_effect=[_clone_fail()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert result['success'] is False
    assert 'repository not found' in result['error']


def test_execute_clone_timeout_returns_error(agent):
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=subprocess.TimeoutExpired(cmd='git', timeout=30)), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert result['success'] is False
    assert 'timed out' in result['error']


# --- cleanup always called ---

def test_cleanup_not_called_on_success(agent):
    walk_data = {'.': ['README.md', 'main.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree') as mock_rm, \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        agent.execute(repo_url='https://github.com/user/repo')
    mock_rm.assert_not_called()


def test_clone_path_in_data_on_success(agent):
    walk_data = {'.': ['app.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert result['data']['clone_path'] == '/tmp/fake'


def test_cleanup_called_on_clone_failure(agent):
    with patch('agents.git_repo_agent.subprocess.run', side_effect=[_clone_fail()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree') as mock_rm:
        agent.execute(repo_url='https://github.com/user/repo')
    mock_rm.assert_called_once_with('/tmp/fake', ignore_errors=True)


# --- happy path ---

def test_execute_success_repo_url_in_data(agent):
    walk_data = {'.': ['README.md', 'app.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert result['success'] is True
    assert result['data']['repo_url'] == 'https://github.com/user/repo'


def test_execute_success_branch_detected(agent):
    walk_data = {'.': ['app.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result('develop')]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert result['data']['branch'] == 'develop'


# --- branch / depth params passed to git ---

def test_branch_param_included_in_clone_cmd(agent):
    walk_data = {'.': ['app.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result('feature-x')]) as mock_run, \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        agent.execute(repo_url='https://github.com/user/repo', branch='feature-x')
    clone_cmd = mock_run.call_args_list[0][0][0]
    assert '--branch' in clone_cmd
    assert 'feature-x' in clone_cmd


def test_depth_param_in_clone_cmd(agent):
    walk_data = {'.': ['app.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]) as mock_run, \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        agent.execute(repo_url='https://github.com/user/repo', depth=2)
    clone_cmd = mock_run.call_args_list[0][0][0]
    assert '--depth' in clone_cmd
    assert '2' in clone_cmd


# --- README ---

def test_readme_read_and_returned(agent):
    walk_data = {'.': ['README.md']}
    readme_text = 'Hello world readme'
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists',
               side_effect=lambda p: p.endswith('README.md')), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False), \
         patch('builtins.open', mock_open(read_data=readme_text)):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert result['data']['readme'] == readme_text


def test_readme_truncated_to_2000_chars(agent):
    walk_data = {'.': ['README.md']}
    long_text = 'x' * 5000
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists',
               side_effect=lambda p: p.endswith('README.md')), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False), \
         patch('builtins.open', mock_open(read_data=long_text)):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert len(result['data']['readme']) <= 2000


def test_no_readme_returns_none(agent):
    walk_data = {'.': ['app.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert result['data']['readme'] is None


# --- file tree ---

def test_file_tree_capped_at_200(agent):
    # 300 files in root
    walk_data = {'.': [f'file{i}.py' for i in range(300)]}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert len(result['data']['file_tree']) <= 200
    assert result['data']['total_files'] == 300


def test_git_dir_excluded_from_tree(agent):
    # Simulate os.walk including a .git entry that should be filtered
    fake_root = '/tmp/fake'

    def fake_walk(root):
        # dirnames includes .git which should be pruned
        yield fake_root, ['.git', 'src'], ['README.md']
        yield os.path.join(fake_root, 'src'), [], ['app.py']
        # .git subtree should never appear because dirnames[:] filters it

    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value=fake_root), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk', side_effect=fake_walk), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    tree = result['data']['file_tree']
    assert not any('.git' in p for p in tree)


# --- language stats ---

def test_language_stats_top_5_only(agent):
    # 8 different extensions
    files = [f'file.{ext}' for ext in ['py', 'js', 'ts', 'go', 'rb', 'java', 'c', 'cpp']]
    walk_data = {'.': files}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists', return_value=False), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    assert len(result['data']['language_stats']) <= 5


# --- config file detection ---

def test_config_files_detected(agent):
    walk_data = {'.': ['app.py']}
    with patch('agents.git_repo_agent.subprocess.run',
               side_effect=[_clone_ok(), _branch_result()]), \
         patch('agents.git_repo_agent.tempfile.mkdtemp', return_value='/tmp/fake'), \
         patch('agents.git_repo_agent.shutil.rmtree'), \
         patch('agents.git_repo_agent.os.walk',
               return_value=list(_fake_walk('/tmp/fake', walk_data))), \
         patch('agents.git_repo_agent.os.path.exists',
               side_effect=lambda p: p.endswith('Dockerfile') or p.endswith('Makefile')), \
         patch('agents.git_repo_agent.os.path.isdir', return_value=False):
        result = agent.execute(repo_url='https://github.com/user/repo')
    found = result['data']['config_files_present']
    assert 'Dockerfile' in found
    assert 'Makefile' in found
