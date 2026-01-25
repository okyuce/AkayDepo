from app.core.database import engine
from sqlalchemy import text
from app.models.user import User

# Generate correct password hash
u = User(username='admin', role='admin')
u.set_password('Akay1234')

# Update database
with engine.connect() as conn:
    result = conn.execute(
        text("UPDATE users SET password_hash = :hash WHERE username = 'admin'"),
        {'hash': u.password_hash}
    )
    conn.commit()
    print(f'Password updated for admin user. Rows affected: {result.rowcount}')
