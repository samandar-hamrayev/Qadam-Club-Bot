from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base
from config import Config

engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Seed admins
    from .models import AdminUser
    db = SessionLocal()
    try:
        for admin_id in Config.ADMIN_IDS:
            exists = db.query(AdminUser).filter(AdminUser.telegram_id == admin_id).first()
            if not exists:
                admin = AdminUser(telegram_id=admin_id, role="superadmin")
                db.add(admin)
        db.commit()
    except Exception as e:
        print(f"Error seeding admins: {e}")
        db.rollback()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
