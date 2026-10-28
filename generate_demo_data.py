"""
generate_demo_data.py
Standalone script to populate Chai House AI demo data without running the web server.

Usage:
    python generate_demo_data.py
"""

import os
import sys

# Ensure the project root is on the Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.services.demo_service import load_demo_data


def main():
    app = create_app('development')
    with app.app_context():
        print('Creating database tables...')
        db.create_all()
        print('Loading demo data...')
        count = load_demo_data()
        print(f'✅ Done! {count} sale records inserted.')


if __name__ == '__main__':
    main()
