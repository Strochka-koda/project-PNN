#!/bin/bash
pip install -r requirements.txt
python -c "from database import init_db, add_default_cities; from app import app; init_db(); add_default_cities()"