#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

def setup_environment():
    """Set up virtual environment and install requirements"""
    print("Setting up development environment...")
    
    # Create virtual environment
    if not Path('venv').exists():
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
        print("Created virtual environment")
    
    # Determine the pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = 'venv\\Scripts\\pip'
    else:  # macOS/Linux
        pip_path = 'venv/bin/pip'
    
    # Install requirements
    requirements = ['requests>=2.31.0']
    
    # Create requirements.txt
    with open('requirements.txt', 'w') as f:
        f.write('\n'.join(requirements))
    
    # Install requirements
    subprocess.run([pip_path, 'install', '-r', 'requirements.txt'])
    print("Installed requirements")

if __name__ == '__main__':
    setup_environment()
    print("\nSetup complete! Now activate your virtual environment:")
    if os.name == 'nt':  # Windows
        print("run: .\\venv\\Scripts\\activate")
    else:  # macOS/Linux
        print("run: source venv/bin/activate")