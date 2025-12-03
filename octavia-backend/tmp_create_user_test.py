from app import db, models, security

# get a session from the generator
gen = db.get_db()
session = next(gen)
try:
    user = models.User(email="dev+test1@example.com", password_hash=security.get_password_hash("Password123!"))
    session.add(user)
    session.commit()
    print("Created user id:", user.id)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    session.close()
    try:
        next(gen)
    except StopIteration:
        pass
