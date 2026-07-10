import os
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.db.orm.users import User, UserRole
from app.db.orm.org import (
    Region,
    Branch,
    UserBranchScope,
    SanctioningMandate,
    ProductType,
)
from app.api.auth import get_password_hash

def seed_demo_principals(db):
    if os.environ.get("APP_ENV") == "production":
        raise RuntimeError("Demo seeding is refused in production.")

    default_pw = os.environ.get("DEMO_USER_PASSWORD")
    if not default_pw:
        raise RuntimeError("DEMO_USER_PASSWORD environment variable must be explicitly supplied for development/test seeding.")

    # 1. Org Structure
    jaipur_region = db.query(Region).filter(Region.code == "RJ-JAIPUR").first()
    if not jaipur_region:
        jaipur_region = Region(code="RJ-JAIPUR", name="Jaipur Region")
        db.add(jaipur_region)
        db.flush()

    malviya_nagar_branch = db.query(Branch).filter(Branch.code == "BR-MN-JAI").first()
    if not malviya_nagar_branch:
        malviya_nagar_branch = Branch(
            code="BR-MN-JAI", name="Jaipur/Malviya Nagar", region_id=jaipur_region.id
        )
        db.add(malviya_nagar_branch)
        db.flush()

    # Seed users
    users_to_seed = [
        {"email": "rm@bank.example", "password": default_pw, "full_name": "Relationship Manager", "role": UserRole.RELATIONSHIP_MANAGER},
        {"email": "credit@bank.example", "password": default_pw, "full_name": "Credit Analyst", "role": UserRole.CREDIT_ANALYST},
        {"email": "sa@bank.example", "password": default_pw, "full_name": "Sanctioning Authority", "role": UserRole.SANCTIONING_AUTHORITY},
        {"email": "admin@bank.example", "password": default_pw, "full_name": "Risk Admin", "role": UserRole.RISK_ADMIN},
        {"email": "auditor@bank.example", "password": default_pw, "full_name": "Auditor", "role": UserRole.AUDITOR},
        {"email": "system@bank.example", "password": default_pw, "full_name": "System Admin", "role": UserRole.SYSTEM_ADMIN},
    ]

    seeded_users = {}
    for u in users_to_seed:
        user = db.query(User).filter(User.email == u["email"]).first()
        if not user:
            user = User(
                email=u["email"],
                hashed_password=get_password_hash(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True
            )
            db.add(user)
        else:
            user.hashed_password = get_password_hash(u["password"])
            user.role = u["role"]
            user.is_active = True
        db.flush()
        seeded_users[user.role] = user

        # Add branch scope ONLY for roles that need it
        scope_role_map = {
            UserRole.RISK_ADMIN: "RISK",
            UserRole.AUDITOR: "AUDIT",
            UserRole.SANCTIONING_AUTHORITY: "REVIEW",
            UserRole.CREDIT_ANALYST: "ASSESSMENT",
            UserRole.RELATIONSHIP_MANAGER: "ORIGINATION"
        }

        if user.role in scope_role_map:
            scope = (
                db.query(UserBranchScope)
                .filter(
                    UserBranchScope.user_id == user.id,
                    UserBranchScope.branch_id == malviya_nagar_branch.id,
                )
                .first()
            )
            if not scope:
                scope = UserBranchScope(
                    user_id=user.id,
                    branch_id=malviya_nagar_branch.id,
                    active=True,
                    scope_role=scope_role_map[user.role],
                )
                db.add(scope)
            else:
                scope.active = True
                scope.scope_role = scope_role_map[user.role]
    db.flush()

    sa_user = seeded_users[UserRole.SANCTIONING_AUTHORITY]
    mandate = (
        db.query(SanctioningMandate)
        .filter(SanctioningMandate.user_id == sa_user.id)
        .first()
    )
    if not mandate:
        mandate = SanctioningMandate(
            user_id=sa_user.id,
            product_type=ProductType.WORKING_CAPITAL_LINE,
            currency="INR",
            maximum_amount=Decimal("10000000.00"),
            active=True,
            region_id=jaipur_region.id,
        )
        db.add(mandate)
    else:
        mandate.active = True
        mandate.maximum_amount = Decimal("10000000.00")
        mandate.region_id = jaipur_region.id
    db.flush()
