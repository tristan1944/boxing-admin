from __future__ import annotations

from sqlalchemy import select

from .database import Base, engine, SessionLocal
from .models import ClassType, Group, FacebookCampaign


def upsert_defaults() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ClassTypes
        defaults_class_types = [
            ("boxing_basics", "Boxing Basics", "beginner"),
            ("sparring", "Sparring", "advanced"),
            ("cardio_box", "Cardio Boxing", "intermediate"),
        ]
        for id_, name, level in defaults_class_types:
            if not db.get(ClassType, id_):
                db.add(ClassType(id=id_, name=name, level=level))

        # Groups
        defaults_groups = [
            ("youth", "Youth", False),
            ("competition_team", "Competition Team", True),
        ]
        for id_, name, requires in defaults_groups:
            if not db.get(Group, id_):
                db.add(Group(id=id_, name=name, requires_approval=requires))

        # Facebook Campaigns
        defaults_campaigns = [
            ("fb_spring_promo", "FB Spring Promo"),
            ("fb_summer_intake", "FB Summer Intake"),
        ]
        for id_, name in defaults_campaigns:
            if not db.get(FacebookCampaign, id_):
                db.add(FacebookCampaign(id=id_, name=name, platform="facebook"))

        db.commit()
    finally:
        db.close()


def main() -> None:
    upsert_defaults()
    print("Seed complete.")


if __name__ == "__main__":
    main()


