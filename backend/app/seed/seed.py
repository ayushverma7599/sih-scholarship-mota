"""Seed the database with the two schemes, demo role logins, and ~200 synthetic
applicants spanning clean / deficient / mismatch / duplicate / ineligible cases.

Run:  python -m app.seed.seed          (from the backend/ directory)
This DROPS and recreates all tables, so it is safe to re-run.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import inspect

from app.core.database import Base, SessionLocal, engine, init_db
from app.core.security import encrypt_pii, hash_password, pii_fingerprint
from app.models import (
    AIFlag, AppStatus, Application, Deficiency, Disbursement,
    EligibilityRuleset, Fellowship, MeritCriteria, MeritScore, Notification,
    ProgressReport, Role, Roles, Scheme, SchemeDocument, StatusEvent, User,
)
from app.seed.sample_docs import generate_document
from app.seed.schemes_data import SCHEMES

random.seed(42)

FIRST_NAMES = [
    "Anil", "Sunita", "Ramesh", "Meena", "Suresh", "Lakshmi", "Rajesh", "Kavita",
    "Manoj", "Priya", "Deepak", "Anita", "Vijay", "Rekha", "Arjun", "Pooja",
    "Sanjay", "Neha", "Ravi", "Sarita", "Birsa", "Jaipal", "Soni", "Mangal",
    "Budhni", "Sombari", "Karma", "Phulmani", "Etwa", "Somra",
]
LAST_NAMES = [
    "Munda", "Oraon", "Hansda", "Soren", "Marandi", "Kisku", "Tudu", "Bhil",
    "Gond", "Meena", "Bhumij", "Ho", "Santal", "Kharia", "Toppo", "Ekka",
    "Minj", "Lakra", "Dungdung", "Barla",
]
STATES = [
    "Jharkhand", "Odisha", "Chhattisgarh", "Madhya Pradesh", "Rajasthan",
    "Gujarat", "Maharashtra", "Telangana", "Andhra Pradesh", "West Bengal",
    "Assam", "Tripura", "Manipur", "Mizoram", "Nagaland",
]
TRIBES = [
    "Munda", "Oraon", "Santal", "Gond", "Bhil", "Ho", "Kharia", "Bhumij",
    "Khond", "Koya", "Baiga", "Sahariya", "Bodo", "Naga", "Mizo",
]
UNIVERSITIES = [
    ("Univ. of Oxford", 3), ("Stanford Univ.", 5), ("Univ. of Toronto", 21),
    ("Univ. of Melbourne", 33), ("Univ. of Manchester", 34), ("KU Leuven", 61),
    ("Univ. of Amsterdam", 55), ("Michigan State", 158), ("Univ. of Sussex", 218),
    ("Curtin Univ.", 183), ("Some Regional Univ.", 780),
]
COURSES_NFST = ["M.Phil", "Ph.D"]
COURSES_NOS = ["Masters", "Ph.D"]

DEMO_PASSWORD = "demo1234"
# Precomputed once and reused for the 200 synthetic applicants (they never log in),
# so seeding does not pay bcrypt's cost 200 times.
_SYNTH_HASH = hash_password(DEMO_PASSWORD)


def _reset():
    Base.metadata.drop_all(bind=engine)
    init_db()


def _get_or_create_roles(db):
    roles = {}
    for name in Roles.ALL:
        r = db.query(Role).filter(Role.name == name).first()
        if not r:
            r = Role(name=name)
            db.add(r)
            db.flush()
        roles[name] = r
    db.commit()
    return roles


def _create_schemes(db) -> dict[str, Scheme]:
    out = {}
    for data in SCHEMES:
        scheme = Scheme(
            code=data["code"], name=data["name"], description=data["description"],
            academic_year=data["academic_year"], slots=data["slots"],
            window_open=date.fromisoformat(data["window_open"]),
            window_close=date.fromisoformat(data["window_close"]),
            is_active=data["is_active"], is_sample=data["is_sample"],
        )
        db.add(scheme)
        db.flush()
        db.add(EligibilityRuleset(scheme_id=scheme.id, rules=data["rules"]))
        db.add(MeritCriteria(scheme_id=scheme.id, weights=data["merit_weights"],
                             tiebreak=data["merit_tiebreak"], quotas=data["merit_quotas"]))
        for d in data["documents"]:
            db.add(SchemeDocument(scheme_id=scheme.id, **d))
        out[data["code"]] = scheme
    db.commit()
    return out


def _demo_users(db, roles):
    demos = [
        ("admin@demo.gov.in", "Ministry Admin", Roles.ADMIN, {}),
        ("scrutiny@demo.gov.in", "Scrutiny Officer", Roles.SCRUTINY, {}),
        ("committee@demo.gov.in", "Committee Member", Roles.COMMITTEE, {}),
        ("applicant@demo.gov.in", "Demo Applicant", Roles.APPLICANT, {
            "category": "ST", "tribe": "Munda", "state": "Jharkhand", "gender": "female",
            "age": 27, "family_income": 240000, "qualifying_marks": 74,
            "course_level": "Ph.D", "university": "Univ. of Delhi", "university_rank": 407,
            "research_proposal_score": 80, "dob": "12-05-1998",
            "aadhaar_enc": encrypt_pii("432112345678"),
            "aadhaar_fp": pii_fingerprint("432112345678"),
            "bank_account_enc": encrypt_pii("50100123456789"),
            "bank_account_fp": pii_fingerprint("50100123456789"),
        }),
    ]
    users = {}
    for email, name, role, profile in demos:
        u = User(email=email, full_name=name, mobile="9800000000",
                 password_hash=hash_password(DEMO_PASSWORD), role_id=roles[role].id,
                 profile=profile, campus_verified=True)
        db.add(u)
        db.flush()
        users[role] = u
    db.commit()
    return users


def _make_profile(i: int, case: str) -> tuple[dict, str]:
    gender = random.choice(["male", "female", "female"])  # skew for quota realism
    tribe = random.choice(TRIBES)
    state = random.choice(STATES)
    marks = random.randint(58, 92)
    income = random.choice([90000, 150000, 220000, 350000, 480000, 550000])
    age = random.randint(23, 34)
    pvtg = random.random() < 0.12
    profile = {
        "category": "ST", "tribe": tribe, "state": state, "gender": gender,
        "age": age, "family_income": income, "qualifying_marks": marks,
        "pvtg": pvtg, "research_proposal_score": random.randint(55, 95),
    }
    # Induce ineligibility variants
    if case == "ineligible_income":
        profile["family_income"] = random.choice([750000, 900000, 1100000])
    elif case == "ineligible_category":
        profile["category"] = random.choice(["OBC", "General"])
    elif case == "ineligible_marks":
        profile["qualifying_marks"] = random.randint(35, 52)
    return profile, gender


def _spread_time(days_ago_max=45) -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, days_ago_max), hours=random.randint(0, 23))


def _add_event(db, app, to_status, at, note=""):
    db.add(StatusEvent(application_id=app.id, from_status=None, to_status=to_status,
                       at=at, note=note))


def _gen_docs_and_process(db, app, scheme, case, applicant_name, aadhaar_plain):
    """Generate sample documents + sidecars, then process like a real upload."""
    from app.api.applications import _income_limit, _process_document
    from app.models import ApplicationDocument
    from app.services.storage import get_storage, sha256_bytes

    storage = get_storage()
    income_limit = _income_limit(scheme)
    profile = app.applicant.profile

    for sd in sorted(scheme.documents, key=lambda x: x.order):
        # deficient case: skip one mandatory doc (the NET/GATE or admission letter)
        if case == "deficient" and sd.doc_type in ("net_gate_scorecard", "admission_letter") \
                and sd.mandatory:
            continue
        # optional research proposal: only sometimes present
        if not sd.mandatory and random.random() < 0.4:
            continue

        # Build field values for this doc
        name_on_doc = applicant_name
        if case == "mismatch" and sd.doc_type in ("st_certificate", "income_certificate"):
            name_on_doc = random.choice(FIRST_NAMES) + " " + random.choice(LAST_NAMES)
        fields = {
            "name": name_on_doc,
            "dob": "10-06-1997",
            "certificate_number": f"{sd.doc_type[:3].upper()}/{random.randint(10000,99999)}",
            "issuing_authority": f"District Magistrate, {profile['state']}",
            "valid_upto": "31-12-2027",
            "income_amount": str(profile["family_income"]),
            "marks": str(profile["qualifying_marks"]),
            "aadhaar": aadhaar_plain,
        }
        # expired certificate variant
        if case == "expired" and sd.doc_type == "st_certificate":
            fields["valid_upto"] = "01-01-2023"

        dest = f"{storage.base}/app_{app.id}"
        pdf_path = generate_document(dest, sd.doc_type, fields)
        data = open(pdf_path, "rb").read()
        adoc = ApplicationDocument(
            application_id=app.id, scheme_document_id=sd.id, doc_type=sd.doc_type,
            file_path=pdf_path, original_name=f"{sd.doc_type}.pdf",
            content_type="application/pdf", sha256=sha256_bytes(data),
        )
        db.add(adoc)
        db.flush()
        _process_document(db, app, adoc, sd, income_limit)
    db.commit()


def _synthetic_merit(db, app, scheme):
    from app.services import merit as merit_svc, rule_engine
    ctx = rule_engine.build_context(app.applicant.profile, app.form_data)
    weights = scheme.merit_criteria.weights
    values = {
        "marks": ctx.get("qualifying_marks"),
        "income_bracket": ctx.get("family_income"),
        "family_income": ctx.get("family_income"),
        "research_proposal": ctx.get("research_proposal_score"),
        "interview": random.randint(55, 90),
        "university_rank": ctx.get("university_rank", 400),
    }
    s = merit_svc.score(weights, values)
    ms = MeritScore(application_id=app.id, total=s["total"], breakdown=s["breakdown"])
    db.add(ms)
    return s["total"]


def seed():
    _reset()
    db = SessionLocal()
    try:
        roles = _get_or_create_roles(db)
        schemes = _create_schemes(db)
        _demo_users(db, roles)
        applicant_role = roles[Roles.APPLICANT]

        # Case distribution for the 200 synthetic applicants.
        cases = (["clean"] * 90 + ["deficient"] * 25 + ["mismatch"] * 15 +
                 ["duplicate"] * 12 + ["expired"] * 8 +
                 ["ineligible_income"] * 20 + ["ineligible_category"] * 8 +
                 ["ineligible_marks"] * 12 + ["clean"] * 10)
        random.shuffle(cases)

        prev_aadhaar_for_dup = None
        full_pipeline_budget = 70  # generate real docs + run pipeline for this many

        for i, case in enumerate(cases):
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            profile, gender = _make_profile(i, case)

            # Scheme choice: weight toward NFST; NOS applicants get a university rank.
            scheme = schemes["NFST"] if random.random() < 0.65 else schemes["NOS"]
            if scheme.code == "NFST":
                profile["course_level"] = random.choice(COURSES_NFST)
            else:
                uni, rank = random.choice(UNIVERSITIES)
                profile["course_level"] = random.choice(COURSES_NOS)
                profile["university"] = uni
                profile["university_rank"] = rank

            # Aadhaar: mostly unique; duplicate case shares the previous one.
            aadhaar_plain = f"{random.randint(2000,9999)}{random.randint(1000,9999)}{random.randint(1000,9999)}"
            if case == "duplicate" and prev_aadhaar_for_dup:
                aadhaar_plain = prev_aadhaar_for_dup
            else:
                prev_aadhaar_for_dup = aadhaar_plain
            profile["aadhaar_enc"] = encrypt_pii(aadhaar_plain)
            profile["aadhaar_fp"] = pii_fingerprint(aadhaar_plain)
            bank_acct = f"5010{random.randint(10**9, 10**10-1)}"
            profile["bank_account_enc"] = encrypt_pii(bank_acct)
            profile["bank_account_fp"] = pii_fingerprint(bank_acct)

            user = User(
                email=f"applicant{i+1}@example.com", full_name=name,
                mobile=f"9{random.randint(700000000, 799999999)}",
                password_hash=_SYNTH_HASH, role_id=applicant_role.id,
                profile=profile, campus_verified=random.random() < 0.85,
            )
            db.add(user)
            db.flush()

            form_data = {
                "full_name": name, "category": profile["category"],
                "family_income": profile["family_income"],
                "qualifying_marks": profile["qualifying_marks"],
                "course_level": profile["course_level"], "age": profile["age"],
                "university_rank": profile.get("university_rank"),
                "research_proposal_score": profile["research_proposal_score"],
            }
            submitted = _spread_time()
            app = Application(user_id=user.id, scheme_id=scheme.id,
                              status=AppStatus.SUBMITTED, form_data=form_data,
                              submitted_at=submitted, created_at=submitted)
            db.add(app)
            db.flush()
            _add_event(db, app, AppStatus.SUBMITTED, submitted, "Application submitted.")

            if full_pipeline_budget > 0 and case in (
                    "clean", "deficient", "mismatch", "duplicate", "expired"):
                full_pipeline_budget -= 1
                _gen_docs_and_process(db, app, scheme, case, name, aadhaar_plain)
                from app.services.pipeline import run_auto_verification
                run_auto_verification(db, app, actor=None)
                # Advance a share of clean ones through scrutiny -> screened.
                if app.status == AppStatus.AUTO_VERIFIED and random.random() < 0.6:
                    t = submitted + timedelta(days=random.randint(1, 5))
                    _add_event(db, app, AppStatus.UNDER_SCRUTINY, t)
                    _add_event(db, app, AppStatus.SCREENED, t + timedelta(hours=6),
                               "Verified by officer.")
                    app.status = AppStatus.SCREENED
                    _synthetic_merit(db, app, scheme)
                db.commit()
                continue

            # Lightweight path: assign a status across the funnel + synthetic signals.
            db.commit()
            _assign_lightweight(db, app, scheme, case, submitted, roles)

        db.commit()
        _finalize_selection(db, schemes["NFST"], roles)
        _summary(db)
    finally:
        db.close()


def _assign_lightweight(db, app, scheme, case, submitted, roles):
    """No physical docs — set a realistic status and synthetic flags/merit."""
    if case.startswith("ineligible"):
        # Ineligible -> deficiency raised with an explanatory reason.
        from app.services import rule_engine
        ctx = rule_engine.build_context(app.applicant.profile, app.form_data)
        res = rule_engine.evaluate(scheme.ruleset.rules, ctx)
        for r in res["results"]:
            if not r["pass"]:
                db.add(AIFlag(application_id=app.id, type="ineligible", severity="high",
                              confidence=0.95, reason=r["reason"]))
                db.add(Deficiency(application_id=app.id, message=r["reason"], status="OPEN"))
        app.status = AppStatus.DEFICIENCY_RAISED
        app.risk_score = 70
        _add_event(db, app, AppStatus.DEFICIENCY_RAISED,
                   submitted + timedelta(days=1), "Auto eligibility check failed.")
        return

    roll = random.random()
    if roll < 0.18:
        app.status = AppStatus.UNDER_SCRUTINY
        app.risk_score = random.choice([10, 20, 35])
        _add_event(db, app, AppStatus.AUTO_VERIFIED, submitted + timedelta(hours=2))
        _add_event(db, app, AppStatus.UNDER_SCRUTINY, submitted + timedelta(days=1))
    elif roll < 0.30:
        app.status = AppStatus.AUTO_VERIFIED
        app.risk_score = random.choice([5, 12, 18])
        _add_event(db, app, AppStatus.AUTO_VERIFIED, submitted + timedelta(hours=2))
    else:
        # Screened -> eligible for merit ranking / selection.
        app.status = AppStatus.SCREENED
        app.risk_score = random.choice([5, 8, 12])
        t = submitted + timedelta(days=random.randint(1, 7))
        _add_event(db, app, AppStatus.AUTO_VERIFIED, submitted + timedelta(hours=2))
        _add_event(db, app, AppStatus.UNDER_SCRUTINY, t)
        _add_event(db, app, AppStatus.SCREENED, t + timedelta(hours=8), "Verified by officer.")
        _synthetic_merit(db, app, scheme)


def _finalize_selection(db, scheme, roles):
    """Rank screened NFST applications, mark top ones selected, create fellowships."""
    from app.services import merit as merit_svc

    apps = (db.query(Application)
            .filter(Application.scheme_id == scheme.id,
                    Application.status == AppStatus.SCREENED)
            .all())
    apps = [a for a in apps if a.merit]
    scored = []
    for a in apps:
        scored.append({
            "application_id": a.id, "total": a.merit.total,
            "values": {"marks": a.applicant.profile.get("qualifying_marks", 0),
                       "age": a.applicant.profile.get("age", 30)},
            "attributes": {
                "women": str(a.applicant.profile.get("gender", "")).lower() == "female",
                "pvtg": bool(a.applicant.profile.get("pvtg")),
            },
            "app": a,
        })
    criteria = {"tiebreak": scheme.merit_criteria.tiebreak,
                "quotas": scheme.merit_criteria.quotas}
    ranked = merit_svc.rank_applicants(scored, criteria, scheme.slots)
    for it in ranked:
        a = it["app"]
        a.merit.rank = it["rank"]
        a.merit.quota_tag = it.get("quota_tag")
        if it["selected"]:
            a.status = AppStatus.SELECTED
            _add_event(db, a, AppStatus.SELECTED,
                       datetime.now(timezone.utc) - timedelta(days=2), "Result published.")
            # Half of the selected have joined (fellowship active).
            fel = Fellowship(application_id=a.id, stage="JRF",
                             status="AWAITING_JOINING")
            db.add(fel)
            db.flush()
            if random.random() < 0.5:
                fel.status = "ACTIVE"
                fel.joining_date = date.today() - timedelta(days=20)
                a.status = AppStatus.FELLOWSHIP_ACTIVE
                _add_event(db, a, AppStatus.FELLOWSHIP_ACTIVE,
                           datetime.now(timezone.utc) - timedelta(days=1))
                for q in range(2):
                    db.add(Disbursement(fellowship_id=fel.id, period=f"Q{q+1}",
                                        amount=75000.0,
                                        status="DISBURSED" if q == 0 else "SCHEDULED",
                                        scheduled_for=date.today() + timedelta(days=90 * q)))
                db.add(ProgressReport(fellowship_id=fel.id, period="Semester 1",
                                      status="SUBMITTED"))
            db.add(Notification(user_id=a.user_id, title="Congratulations — selected!",
                                message="You have been selected under NFST (sample)."))
    db.commit()


def _summary(db):
    from collections import Counter
    total = db.query(User).count()
    apps = db.query(Application).count()
    statuses = Counter(a.status for a in db.query(Application).all())
    flags = db.query(AIFlag).count()
    defs = db.query(Deficiency).count()
    print("\n================ SEED COMPLETE ================")
    print(f"Users: {total} | Applications: {apps} | AI flags: {flags} | Deficiencies: {defs}")
    print("Status distribution:")
    for s, c in statuses.most_common():
        print(f"   {s:<20} {c}")
    print("\nDemo logins (password: demo1234):")
    print("   admin@demo.gov.in       (Ministry Admin)")
    print("   scrutiny@demo.gov.in    (Scrutiny Officer)")
    print("   committee@demo.gov.in   (Committee Member)")
    print("   applicant@demo.gov.in   (Applicant)")
    print("===============================================\n")


if __name__ == "__main__":
    seed()
