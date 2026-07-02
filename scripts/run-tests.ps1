# Lancer les tests localement (Windows)
pip install -r services/user-service/requirements.txt
pip install -r services/course-service/requirements.txt
pip install -r requirements-test.txt
python -m pytest tests/ -v
