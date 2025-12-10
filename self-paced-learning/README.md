# Self-Paced Learning

## Setup

### Environment Variables

Create a `.env` file in the project root with at least:

```
OPENAI_API_KEY=your_api_key_here
FLASK_KEY=some_dev_secret_key
# Optional: override the default SQLite database path
# DATABASE_URL=sqlite:///self_paced_learning.db
```

### Dependencies

Install the required packages (Flask-SQLAlchemy, Flask-Migrate, Alembic, etc.):

```bash
pip install -r requirements.txt
```

### Database

Run the Alembic migrations to create the authentication and progress tables.
From `self-paced-learning/` (and after setting `FLASK_APP=app.py` for your shell):

```bash
flask db upgrade
```

The default configuration stores a SQLite database at
`self_paced_learning.db`. Set `DATABASE_URL` if you want to point to Postgres or
another backend.

## Authentication & Roles

- `/register` – create student or teacher accounts.
- `/login` – access the learning experience (all core routes now require login).
- Teachers receive a shareable class code and can manage students from
  `/teacher/students`.
- Students can join classes via `/student/classes` using the teacher code.

Use `/auth/logout` to end the session when testing different roles.
