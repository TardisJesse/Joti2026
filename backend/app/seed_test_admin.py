"""Ensure the mvp-admin test account exists and is active.

This is intended to run as part of the Railway pre-deploy command so the
mvp-admin / mvp-admin-change-me credentials are guaranteed to work
immediately after every deploy, regardless of prior database state.
"""
from .database import SessionLocal
from .models import User, UserRole
from .security import hash_password

TEST_ADMIN_NAME = "mvp-admin"
TEST_ADMIN_PASSWORD = "mvp-admin-change-me"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.name == TEST_ADMIN_NAME).first()
        if user:
            user.active = True
            user.password_hash = hash_password(TEST_ADMIN_PASSWORD)
        else:
            user = User(
                name=TEST_ADMIN_NAME,
                role=UserRole.ADMIN,
                password_hash=hash_password(TEST_ADMIN_PASSWORD),
                active=True,
            )
            db.add(user)
        db.commit()
        print("mvp-admin test account ready")
    finally:
        db.close()


if __name__ == "__main__":
    main()
