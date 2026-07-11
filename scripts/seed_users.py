"""
Seed script to populate default users with hashed passwords and role associations.

Why this approach:
We query the existing Org -> Team -> Advisor hierarchy in the Postgres database and 
programmatically seed one user account for each role:
- Director (organization-wide, no FKs)
- Team Leader (associated with Rohan's team)
- Advisor (associated with advisor Rohan)
Passwords are securely hashed using bcrypt via our auth_utils module.
"""

from src.storage.db import SessionLocal
from src.storage import models
from src.api import auth_utils

def seed_users():
    session = SessionLocal()
    try:
        # Check if users already exist
        if session.query(models.User).count() > 0:
            print("Users already seeded. Skipping.")
            return

        print("Seeding users...")

        # 1. Find Rohan (advisor) and his team
        rohan = session.query(models.Advisor).filter(models.Advisor.name == "Rohan").first()
        if not rohan:
            # Create backup Org/Team/Advisor if empty
            org = models.Org(name="FitNova Corporate")
            session.add(org)
            session.flush()
            team = models.Team(name="Elite Sales", org_id=org.id)
            session.add(team)
            session.flush()
            rohan = models.Advisor(name="Rohan", team_id=team.id)
            session.add(rohan)
            session.flush()
            session.commit()

        team_id = rohan.team_id
        advisor_id = rohan.id

        # 2. Define users to seed
        users_to_seed = [
            {
                "email": "director@fitnova.com",
                "password": "director_pass",
                "role": "director",
                "advisor_id": None,
                "team_id": None
            },
            {
                "email": "leader@fitnova.com",
                "password": "leader_pass",
                "role": "team_leader",
                "advisor_id": None,
                "team_id": team_id
            },
            {
                "email": "rohan@fitnova.com",
                "password": "rohan_pass",
                "role": "advisor",
                "advisor_id": advisor_id,
                "team_id": team_id
            }
        ]

        # 3. Insert users with hashed passwords
        for u_data in users_to_seed:
            hashed_pwd = auth_utils.hash_password(u_data["password"])
            db_user = models.User(
                email=u_data["email"],
                hashed_password=hashed_pwd,
                role=u_data["role"],
                advisor_id=u_data["advisor_id"],
                team_id=u_data["team_id"]
            )
            session.add(db_user)
            
        session.commit()
        print("Successfully seeded users:")
        print(" - Director: director@fitnova.com / director_pass")
        print(" - Team Leader: leader@fitnova.com / leader_pass")
        print(" - Advisor (Rohan): rohan@fitnova.com / rohan_pass")
        
    except Exception as e:
        session.rollback()
        print(f"Error seeding users: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_users()
