"""SPARC Textbook Studio.

`app` is the object gunicorn serves (Procfile: web: gunicorn app:app) and
that app.py imports for `flask run`. All setup lives in app_factory.create_app().
"""

from .app_factory import create_app

app = create_app()
