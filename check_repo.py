import os
import subprocess
from pathlib import Path

def check_repository_structure():
    """Check and display repository file structure"""
    
    print("=== Tracked Files (git ls-files) ===")
    tracked = subprocess.run(['git', 'ls-files'], 
                           capture_output=True, 
                           text=True)
    tracked_files = set(tracked.stdout.splitlines())
    print("\n".join(tracked_files) or "No tracked files found")
    
    print("\n=== All Files in Directory ===")
    all_files = []
    for root, dirs, files in os.walk('.'):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')
        # Skip venv directory if it exists
        if 'venv' in dirs:
            dirs.remove('venv')
            
        for file in files:
            path = os.path.join(root, file)
            # Convert to forward slashes for consistency
            path = path.replace('\\', '/').lstrip('./')
            all_files.append(path)
    
    all_files = set(all_files)
    print("\n".join(sorted(all_files)) or "No files found")
    
    print("\n=== Files Not Tracked in Git ===")
    untracked = all_files - tracked_files
    print("\n".join(sorted(untracked)) or "All files are tracked")
    
    print("\n=== Expected Directory Structure ===")
    expected_dirs = [
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
    
    print("\nChecking expected directories...")
    for dir_path in expected_dirs:
        path = Path(dir_path)
        if path.exists():
            readme = path / "README.md"
            if readme.exists():
                print(f"✅ {dir_path} (with README)")
            else:
                print(f"⚠️  {dir_path} (missing README)")
        else:
            print(f"❌ {dir_path} (missing)")

if __name__ == '__main__':
    check_repository_structure()