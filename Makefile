mig:
	python3 manage.py makemigrations
	python3 manage.py migrate

user:
	python3 manage.py createsuperuser

load_data:
	python3 manage.py loaddata categories
celery:
	celery -A root worker --loglevel=info

flush:
	python3 manage.py flush --no-input

loaddata:
	python3 manage.py loaddata country.json


del_mig:
	  find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	  find . -path "*/migrations/*.pyc"  -delete
