import json
from datetime import datetime, timedelta

from app.ai.tools import (
    execute_tool,
    check_appointment_availability,
    book_appointment,
)
from app.models.appointment import Appointment, AppointmentStatus


class TestCheckAppointmentAvailability:
    def test_returns_available_when_no_conflict(self, db_session, test_agent):
        start = datetime(2026, 8, 28, 15, 0)
        end = datetime(2026, 8, 28, 15, 30)

        result = check_appointment_availability(
            db=db_session,
            agent_id=test_agent.id,
            start_time=start,
            end_time=end,
        )

        assert result["available"] is True
        assert result["start_time"] == start.isoformat()
        assert result["end_time"] == end.isoformat()

    def test_returns_unavailable_when_conflict_exists(self, db_session, test_agent):
        existing = Appointment(
            agent_id=test_agent.id,
            customer_name="Existing Customer",
            customer_phone="1234567890",
            start_time=datetime(2026, 8, 28, 14, 0),
            end_time=datetime(2026, 8, 28, 15, 0),
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(existing)
        db_session.commit()

        start = datetime(2026, 8, 28, 14, 30)
        end = datetime(2026, 8, 28, 15, 30)

        result = check_appointment_availability(
            db=db_session,
            agent_id=test_agent.id,
            start_time=start,
            end_time=end,
        )

        assert result["available"] is False

    def test_returns_available_for_adjacent_times(self, db_session, test_agent):
        existing = Appointment(
            agent_id=test_agent.id,
            customer_name="Existing Customer",
            customer_phone="1234567890",
            start_time=datetime(2026, 8, 28, 14, 0),
            end_time=datetime(2026, 8, 28, 15, 0),
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(existing)
        db_session.commit()

        start = datetime(2026, 8, 28, 15, 0)
        end = datetime(2026, 8, 28, 15, 30)

        result = check_appointment_availability(
            db=db_session,
            agent_id=test_agent.id,
            start_time=start,
            end_time=end,
        )

        assert result["available"] is True


class TestBookAppointment:
    def test_creates_appointment_successfully(self, db_session, test_agent):
        start = datetime(2026, 8, 28, 15, 0)
        end = datetime(2026, 8, 28, 15, 30)

        result = book_appointment(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            customer_name="John Doe",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
            notes="Test appointment",
        )

        assert result["success"] is True
        assert "appointment_id" in result
        assert result["customer_name"] == "John Doe"

    def test_rejects_overlapping_appointment(self, db_session, test_agent):
        existing = Appointment(
            agent_id=test_agent.id,
            customer_name="Existing Customer",
            customer_phone="1234567890",
            start_time=datetime(2026, 8, 28, 14, 0),
            end_time=datetime(2026, 8, 28, 15, 0),
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(existing)
        db_session.commit()

        start = datetime(2026, 8, 28, 14, 30)
        end = datetime(2026, 8, 28, 15, 30)

        result = book_appointment(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            customer_name="John Doe",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
        )

        assert result["success"] is False
        assert "error" in result

    def test_rejects_end_before_start(self, db_session, test_agent):
        start = datetime(2026, 8, 28, 16, 0)
        end = datetime(2026, 8, 28, 15, 0)

        result = book_appointment(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            customer_name="John Doe",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
        )

        assert result["success"] is False
        assert "error" in result


class TestExecuteTool:
    def test_execute_check_availability_tool(self, db_session, test_agent):
        args = json.dumps({
            "start_time": "2026-08-28T15:00:00",
            "end_time": "2026-08-28T15:30:00",
        })

        result = execute_tool(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            tool_name="check_appointment_availability",
            arguments=args,
        )

        data = json.loads(result)
        assert data["available"] is True

    def test_execute_book_appointment_tool(self, db_session, test_agent):
        args = json.dumps({
            "customer_name": "John Doe",
            "customer_phone": "1234567890",
            "start_time": "2026-08-28T15:00:00",
            "end_time": "2026-08-28T15:30:00",
        })

        result = execute_tool(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            tool_name="book_appointment",
            arguments=args,
        )

        data = json.loads(result)
        assert data["success"] is True

    def test_rejects_unknown_tool(self, db_session, test_agent):
        args = json.dumps({})

        result = execute_tool(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            tool_name="unknown_tool",
            arguments=args,
        )

        data = json.loads(result)
        assert "error" in data

    def test_handles_invalid_json_arguments(self, db_session, test_agent):
        result = execute_tool(
            db=db_session,
            agent_id=test_agent.id,
            call_id=None,
            tool_name="check_appointment_availability",
            arguments="not json",
        )

        data = json.loads(result)
        assert "error" in data
