from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customers import get_customer_by_phone


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


def _get_user_customer(
    db: Session,
    customer_id: int,
    user_id: int,
) -> Customer | None:
    return db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.owner_id == user_id,
        )
    )


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    data: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = get_customer_by_phone(
        db,
        current_user.id,
        data.phone_number,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with that phone number already exists",
        )

    customer = Customer(
        owner_id=current_user.id,
        phone_number=data.phone_number,
        name=data.name,
        email=str(data.email) if data.email else None,
        notes=data.notes,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    q: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        select(Customer)
        .where(Customer.owner_id == current_user.id)
        .order_by(Customer.id.desc())
    )

    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                Customer.name.ilike(pattern),
                Customer.phone_number.ilike(pattern),
                Customer.email.ilike(pattern),
            )
        )

    return db.scalars(statement).all()


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = _get_user_customer(db, customer_id, current_user.id)

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = _get_user_customer(db, customer_id, current_user.id)

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    new_phone = update_data.get("phone_number")

    if new_phone is not None and new_phone != customer.phone_number:
        existing = get_customer_by_phone(
            db,
            current_user.id,
            new_phone,
        )

        if existing is not None and existing.id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A customer with that phone number already exists",
            )

    if "email" in update_data:
        update_data["email"] = str(update_data["email"]) if update_data["email"] else None

    for field, value in update_data.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)

    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = _get_user_customer(db, customer_id, current_user.id)

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    db.delete(customer)
    db.commit()

    return None