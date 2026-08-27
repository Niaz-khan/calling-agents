from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def get_customer_by_phone(db: Session, phone_number: str) -> Customer | None:
    statement = select(Customer).where(
        Customer.phone_number == phone_number,
    )

    return db.scalar(statement)


def create_customer(
    db: Session,
    phone_number: str,
    name: str | None = None,
    email: str | None = None,
    notes: str | None = None,
) -> Customer:
    existing = get_customer_by_phone(db, phone_number)

    if existing:
        if name:
            existing.name = name
        if email:
            existing.email = email
        if notes:
            existing.notes = notes
        db.commit()
        db.refresh(existing)
        return existing

    customer = Customer(
        phone_number=phone_number,
        name=name,
        email=email,
        notes=notes,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer
