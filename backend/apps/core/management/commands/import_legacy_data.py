"""Import legacy FastAPI business data into the Django org-scoped models.

Reads the legacy SQLAlchemy-owned tables (still in PostgreSQL) and re-points
every row into the single migrated organization while preserving original
timestamps. Telephony calls become ``Conversation(channel="phone")`` +
one-to-one ``PhoneCall`` profiles.

* The legacy tables are treated as read-only and are never modified/dropped.
* Idempotency: refuses to run when Django business tables already hold rows
  unless ``--reset`` is given (which wipes only the Django-side tables).
"""

import os

import psycopg
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.agents.models import Agent
from apps.appointments.models import Appointment
from apps.conversations.models import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
    PhoneCall,
)
from apps.crm.models import Customer
from apps.knowledge.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from apps.telephony.models import PhoneNumber
from apps.tenancy.models import Organization

_TARGET_MODELS = [
    Agent,
    Customer,
    PhoneNumber,
    Conversation,
    PhoneCall,
    KnowledgeBase,
    KnowledgeDocument,
    KnowledgeChunk,
    Appointment,
]

_RESET_ORDER = [
    KnowledgeChunk,
    KnowledgeDocument,
    Appointment,
    PhoneCall,
    Conversation,
    PhoneNumber,
    KnowledgeBase,
    Customer,
    Agent,
]


def _fetch(sql):
    url = os.environ["DATABASE_URL"].replace("+psycopg://", "://", 1)
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def _touch(model, pk, **fields):
    model.objects.filter(pk=pk).update(**fields)


class Command(BaseCommand):
    help = "Import legacy FastAPI business data into Django org-scoped models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org", default="Default Organization", help="Target organization name"
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe existing Django business rows before importing",
        )

    def handle(self, *args, **opts):
        org = Organization.objects.filter(name=opts["org"]).first()
        if org is None:
            raise CommandError(
                f"Organization {opts['org']!r} not found; run import_legacy_users first."
            )

        populated = [m.__name__ for m in _TARGET_MODELS if m.objects.exists()]
        if populated:
            if not opts["reset"]:
                raise CommandError(
                    f"Already imported into {', '.join(populated)}. "
                    "Pass --reset to wipe the Django business tables first "
                    "(legacy tables are never touched)."
                )
            for model in _RESET_ORDER:
                model.objects.all().delete()
            self.stdout.write("Reset Django business tables.")

        counts = {}
        with transaction.atomic():
            agent_map = {}
            for legacy_id, name, description, system_prompt, is_active, created_at, updated_at in _fetch(
                "SELECT id, name, description, system_prompt, is_active, created_at, updated_at "
                "FROM agents ORDER BY id"
            ):
                agent = Agent.objects.create(
                    organization=org,
                    name=name,
                    description=description,
                    system_prompt=system_prompt,
                    is_active=is_active,
                )
                _touch(Agent, agent.id, created_at=created_at, updated_at=updated_at)
                agent_map[legacy_id] = agent.id
            counts["agents"] = len(agent_map)

            customer_map = {}
            for legacy_id, phone_number, name, email, notes, memory, created_at, updated_at in _fetch(
                "SELECT id, phone_number, name, email, notes, memory, created_at, updated_at "
                "FROM customers ORDER BY id"
            ):
                customer, _ = Customer.objects.get_or_create(
                    organization=org,
                    phone_number=phone_number,
                    defaults={"name": name, "email": email, "notes": notes, "memory": memory},
                )
                _touch(
                    Customer,
                    customer.id,
                    name=name,
                    email=email,
                    notes=notes,
                    memory=memory,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                customer_map[legacy_id] = customer.id
            counts["customers"] = len(customer_map)

            phone_map = {}
            for legacy_id, agent_id, phone_number, provider, is_active, created_at, provider_number_id in _fetch(
                "SELECT id, agent_id, phone_number, provider, is_active, created_at, "
                "provider_number_id FROM phone_numbers ORDER BY id"
            ):
                phone = PhoneNumber.objects.create(
                    organization=org,
                    agent_id=agent_map[agent_id],
                    phone_number=phone_number,
                    provider=provider,
                    is_active=is_active,
                    provider_number_id=provider_number_id,
                )
                _touch(PhoneNumber, phone.id, created_at=created_at)
                phone_map[legacy_id] = phone.id
            counts["phone_numbers"] = len(phone_map)

            conversation_map = {}
            for (
                legacy_id,
                agent_id,
                customer_id,
                phone_number_id,
                provider_call_id,
                direction,
                status,
                caller_number,
                recording_url,
                transcript,
                summary,
                outcome,
                started_at,
                ended_at,
            ) in _fetch(
                "SELECT id, agent_id, customer_id, phone_number_id, provider_call_id, direction, "
                "status, caller_number, recording_url, transcript, summary, outcome, started_at, "
                "ended_at FROM calls ORDER BY id"
            ):
                conversation = Conversation.objects.create(
                    organization=org,
                    agent_id=agent_map[agent_id],
                    customer_id=customer_map.get(customer_id),
                    deployment=None,
                    channel=ConversationChannel.PHONE,
                    status=(
                        ConversationStatus.CLOSED if ended_at else ConversationStatus.OPEN
                    ),
                    outcome=outcome,
                    transcript=transcript,
                    summary=summary,
                )
                phone_call = PhoneCall.objects.create(
                    conversation=conversation,
                    phone_number_id=phone_map.get(phone_number_id),
                    provider_call_id=provider_call_id,
                    direction=direction,
                    caller_number=caller_number or "",
                    recording_url=recording_url,
                    provider_status=status,
                )
                _touch(
                    Conversation,
                    conversation.id,
                    started_at=started_at,
                    ended_at=ended_at,
                )
                _touch(PhoneCall, phone_call.id, created_at=started_at)
                conversation_map[legacy_id] = conversation.id
            counts["conversations"] = len(conversation_map)

            kb_map = {}
            for legacy_id, agent_id, name, description, created_at, updated_at in _fetch(
                "SELECT id, agent_id, name, description, created_at, updated_at "
                "FROM knowledge_bases ORDER BY id"
            ):
                kb = KnowledgeBase.objects.create(
                    organization=org,
                    agent_id=agent_map[agent_id],
                    name=name,
                    description=description,
                )
                _touch(KnowledgeBase, kb.id, created_at=created_at, updated_at=updated_at)
                kb_map[legacy_id] = kb.id
            counts["knowledge_bases"] = len(kb_map)

            doc_map = {}
            for (
                legacy_id,
                kb_id,
                filename,
                content_type,
                source_type,
                title,
                status,
                error,
                created_at,
            ) in _fetch(
                "SELECT id, knowledge_base_id, filename, content_type, source_type, title, "
                "status, error, created_at FROM knowledge_documents ORDER BY id"
            ):
                doc = KnowledgeDocument.objects.create(
                    knowledge_base_id=kb_map[kb_id],
                    filename=filename,
                    content_type=content_type,
                    source_type=source_type,
                    title=title,
                    status=status,
                    error=error,
                )
                _touch(KnowledgeDocument, doc.id, created_at=created_at)
                doc_map[legacy_id] = doc.id
            counts["knowledge_documents"] = len(doc_map)

            chunk_count = 0
            for document_id, chunk_index, content, embedding, token_count, created_at in _fetch(
                "SELECT document_id, chunk_index, content, embedding, token_count, created_at "
                "FROM knowledge_chunks ORDER BY document_id, chunk_index"
            ):
                chunk = KnowledgeChunk.objects.create(
                    document_id=doc_map[document_id],
                    chunk_index=chunk_index,
                    content=content,
                    embedding=embedding,
                    token_count=token_count,
                )
                _touch(KnowledgeChunk, chunk.id, created_at=created_at)
                chunk_count += 1
            counts["knowledge_chunks"] = chunk_count

            appointment_count = 0
            for (
                legacy_id,
                agent_id,
                call_id,
                customer_name,
                customer_phone,
                start_time,
                end_time,
                status,
                notes,
                created_at,
            ) in _fetch(
                "SELECT id, agent_id, call_id, customer_name, customer_phone, start_time, "
                "end_time, status, notes, created_at FROM appointments ORDER BY id"
            ):
                appointment = Appointment.objects.create(
                    organization=org,
                    agent_id=agent_map[agent_id],
                    conversation_id=conversation_map.get(call_id),
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    start_time=start_time,
                    end_time=end_time,
                    status=status,
                    notes=notes,
                )
                _touch(Appointment, appointment.id, created_at=created_at)
                appointment_count += 1
            counts["appointments"] = appointment_count

        self.stdout.write(
            self.style.SUCCESS(f"Import done (org={org.id!r} {org.name!r}): {counts}")
        )