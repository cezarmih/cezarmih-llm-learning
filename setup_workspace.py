import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
import requests
from datetime import datetime

class WorkspaceManager:
    def __init__(self, project_name, github_token=None):
        self.project_name = project_name
        self.github_token = github_token or os.getenv('GITHUB_CEZAR_TOKEN')
        self.base_path = Path.cwd()
        self.project_path = self.base_path / project_name

    def create_workspace_file(self):
        """Create VS Code/Cursor workspace file"""
        workspace_config = {
            "folders": [
                {
                    "path": "."
                }
            ],
            "settings": {
                "files.exclude": {
                    "**/.git": True,
                    "**/.svn": True,
                    "**/.hg": True,
                    "**/CVS": True,
                    "**/.DS_Store": True,
                    "**/Thumbs.db": True,
                    "**/__pycache__": True,
                    "**/.pytest_cache": True
                },
                "editor.formatOnSave": True,
                "editor.rulers": [80, 100],
                "files.trimTrailingWhitespace": True,
                "files.insertFinalNewline": True
            },
            "extensions": {
                "recommendations": [
                    "ms-python.python",
                    "ms-python.vscode-pylance",
                    "yzhang.markdown-all-in-one",
                    "bierner.markdown-mermaid",
                    "davidanson.vscode-markdownlint",
                    "github.copilot"
                ]
            }
        }
        
        workspace_file = self.project_path / f"{self.project_name}.code-workspace"
        with open(workspace_file, 'w') as f:
            json.dump(workspace_config, f, indent=2)
        
        print(f"Created workspace file: {workspace_file}")

    def create_directory_structure(self):
        """Create the repository directory structure"""
        directories = [
            "meetings/meetup-notes",
            "meetings/templates",
            "research/papers/2024",
            "research/blogs/2024",
            "research/tools/autogen",
            "research/tools/langchain",
            "research/tools/llamaindex",
            "learning/books/aima-notes",
            "learning/books/transformers-nlp-notes",
            "learning/books/rag-notes",
            "learning/courses",
            "learning/tutorials",
            "implementations/experiments",
            "implementations/projects",
            "implementations/examples",
            "resources/tools/distil-whisper",
            "resources/tools/insanely-fast-whisper",
            "resources/communities",
            "scripts"
        ]
        
        for directory in directories:
            dir_path = self.project_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            readme_path = dir_path / "README.md"
            if not readme_path.exists():
                with open(readme_path, 'w') as f:
                    f.write(f"# {directory.replace('/', ' - ').title()}\n\nAdd content here.\n")
        
        print("Created directory structure")

    def create_github_repository(self):
        """Create GitHub repository using GitHub API"""
        if not self.github_token:
            raise ValueError("GitHub token is required. Set GITHUB_CEZAR_TOKEN environment variable.")

        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        data = {
            'name': self.project_name,
            'description': 'LLM Agent Development Resources and Notes',
            'private': False,
            'has_issues': True,
            'has_projects': True,
            'has_wiki': True
        }
        
        response = requests.post(
            'https://api.github.com/user/repos',
            headers=headers,
            json=data
        )
        
        if response.status_code == 201:
            print(f"Created GitHub repository: {self.project_name}")
            return response.json()['clone_url']
        else:
            print(f"Failed to create repository: {response.json()}")
            return None

    def initialize_git(self, clone_url):
        """Initialize git repository and push initial commit"""
        os.chdir(self.project_path)
        
        # Initialize git
        subprocess.run(['git', 'init'])
        
        # Create .gitignore
        gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# VS Code
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json
*.code-workspace

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)

        # Initial commit
        subprocess.run(['git', 'add', '.'])
        subprocess.run(['git', 'commit', '-m', 'Initial commit'])
        
        # Add remote and push
        subprocess.run(['git', 'remote', 'add', 'origin', clone_url])
        subprocess.run(['git', 'branch', '-M', 'main'])
        subprocess.run(['git', 'push', '-u', 'origin', 'main'])
        
        print("Initialized git repository and pushed initial commit")

    def setup_workspace(self):
        """Run the complete workspace setup"""
        print(f"Setting up workspace for {self.project_name}")
        
        # Create project directory
        self.project_path.mkdir(exist_ok=True)
        
        # Create workspace file
        self.create_workspace_file()
        
        # Create directory structure
        self.create_directory_structure()
        
        # Create GitHub repository
        clone_url = self.create_github_repository()
        if clone_url:
            self.initialize_git(clone_url)
        
        print("\nWorkspace setup complete!")
        print(f"To open in Cursor/VS Code, run: code {self.project_path / f'{self.project_name}.code-workspace'}")

def main():
    parser = argparse.ArgumentParser(description='Setup workspace and GitHub repository')
    parser.add_argument('project_name', help='Name of the project')
    parser.add_argument('--token', help='GitHub token (or set GITHUB_CEZARTOKEN environment variable)')
    
    args = parser.parse_args()
    
    try:
        manager = WorkspaceManager(args.project_name, args.token)
        manager.setup_workspace()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()