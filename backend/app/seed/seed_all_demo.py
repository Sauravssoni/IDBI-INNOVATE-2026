import os

def seed_all_demo():
    print("Seeding Shakti Precision...")
    from app.seed.seed_shakti import seed_shakti
    seed_shakti()

    print("Seeding Navprerna Tech Solutions...")
    from app.seed.seed_navprerna import seed_navprerna
    seed_navprerna()

    print("Seeding Rangrez Textiles...")
    from app.seed.seed_rangrez import seed_rangrez
    seed_rangrez()

    print("Seeding Aarohan Infrastructure...")
    from app.seed.seed_aarohan import seed_aarohan
    seed_aarohan()

    print("Running evaluations for advanced states...")
    from app.seed.run_evaluations import run_evaluations
    run_evaluations()

    print("Demo seeding complete!")

if __name__ == "__main__":
    seed_all_demo()
