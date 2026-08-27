from datetime import datetime

from sqlalchemy.orm import Session

from app.services.appointments import check_availability


def check_appointment_availability(db: Session, agent_id: int, start_time: datetime, end_time: datetime,) -> dict:
    available = check_availability(
        db=db,
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "available": available,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }