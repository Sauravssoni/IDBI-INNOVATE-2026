from app.seed.seed_shakti import seed_shakti

def main():
    print("Starting data seeding process...")
    seed_shakti()
    print("✅ All deterministic seed data generated successfully.")

if __name__ == "__main__":
    main()
