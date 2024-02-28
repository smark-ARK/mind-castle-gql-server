from sqlalchemy.orm.session import Session
from sqlalchemy import desc, or_, func
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation
from typing import Optional, List

from app.database import SessionLocal
from app.models import User, Note, SharedNotes
from app.types.types import Participant


def get_notes(
    current_user: User,
    q: Optional[str] = "",
    page: Optional[int] = 1,
    db: Session = SessionLocal(),
):

    limit = 10
    skip = (page - 1) * limit

    # Count total notes meeting the criteria
    total_notes = (
        db.query(func.count(Note.id))
        .filter(
            Note.owner_id == current_user.id,
            or_(
                Note.title.ilike(f"%{q}%"),
                Note.detail.ilike(f"%{q}%"),
            ),
        )
        .scalar()
    )

    # Calculate total pages
    total_pages = total_notes // limit

    notes = (
        db.query(Note)
        .filter(
            Note.owner_id == current_user.id,
            or_(
                Note.title.ilike(f"%{q}%"),
                Note.detail.ilike(f"%{q}%"),
            ),
        )
        .order_by(desc(Note.created_at))
        .limit(limit)
        .offset(skip)
        .all()
    )

    return {"notes": notes, "total_pages": total_pages}


async def get_note(
    current_user,
    id: int,
    db: Session = SessionLocal(),
):
    note = (
        db.query(Note).filter(Note.id == id, Note.owner_id == current_user.id).first()
    )

    if note:
        participants = (
            db.query(User, SharedNotes.permission)
            .join(SharedNotes, SharedNotes.user_id == User.id)
            .filter(SharedNotes.note_id == note.id)
            .all()
        )

        participants_info = [
            Participant(user=user, permission=permission)
            for user, permission in participants
        ]
        return {"note": note, "participants": participants_info}

    # If the note is not owned by the current user, check if it's shared
    shared_note = (
        db.query(Note)
        .join(SharedNotes, SharedNotes.note_id == Note.id)
        .filter(Note.id == id, SharedNotes.user_id == current_user.id)
        .first()
    )
    note = shared_note

    if not shared_note:
        raise Exception(
            f"Note with id {id} is not shared with or owned by the current user",
        )
    participants = (
        db.query(User, SharedNotes.permission)
        .join(SharedNotes, SharedNotes.user_id == User.id)
        .filter(SharedNotes.note_id == note.id)
        .all()
    )

    participants_info = [
        Participant(user=user, permission=permission)
        for user, permission in participants
    ]

    return {"note": note, "participants": participants_info}


async def create_note(
    current_user,
    title: str,
    detail: str,
    db: Session = SessionLocal(),
):
    try:
        new_note = Note(title=title, detail=detail, owner_id=current_user.id)
        db.add(new_note)
        db.commit()
        db.refresh(new_note)
    except Exception as e:
        raise Exception(
            str(e),
        )
    return new_note


async def update_note(
    current_user,
    id: int,
    title: str,
    detail: str,
    db: Session = SessionLocal(),
):
    note_query = db.query(Note).filter(Note.id == id)

    if not note_query.first():
        raise Exception(
            f"Note with id {id} does not exist",
        )

    # Check if the current user has access to the note
    if note_query.first().owner_id != current_user.id:
        # Check if the note is shared with the current user
        shared_note = (
            db.query(SharedNotes)
            .filter(SharedNotes.note_id == id, SharedNotes.user_id == current_user.id)
            .first()
        )
        if not shared_note or shared_note.permission != "edit":
            raise Exception(
                "You do not have permission to edit this note",
            )

    # Update the note
    note_query.update({"title": title, "detail": detail}, synchronize_session=False)
    db.commit()

    return note_query.first()


async def delete_note(
    current_user,
    id: int,
    db: Session = SessionLocal(),
):
    note_query = db.query(Note).filter(Note.id == id, Note.owner_id == current_user.id)
    note = note_query.first()
    if not note:
        raise Exception(
            f"Note with id {id} Does not Exist",
        )
    note_query.delete(synchronize_session=False)
    db.commit()
    return


async def share_note(
    current_user,
    user_id: int,
    permission: str,
    id: int,
    db: Session = SessionLocal(),
):
    note = (
        db.query(Note).filter(Note.id == id, Note.owner_id == current_user.id).first()
    )
    if not note:
        raise Exception(
            f"Note with id {id} Does not Exist",
        )
    other_user = db.query(User).filter(User.id == user_id).first()
    if not other_user:
        raise Exception(
            f"User with id {id} Does not Exist",
        )
    try:
        shared = SharedNotes(user_id=user_id, permission=permission, note_id=id)
        db.add(shared)
        db.commit()
    except Exception as e:
        db.rollback()
        if "duplicate key" in str(e):
            raise Exception(
                f"Already sharing note with id: {id} with {other_user.username}",
            )
        raise Exception(
            str(e),
        )
    return {"note": note, "user": other_user, "permission": permission}


async def unshare_note(
    current_user,
    id: int,
    user_id: int,
    db: Session = SessionLocal(),
):
    note = (
        db.query(Note).filter(Note.id == id, Note.owner_id == current_user.id).first()
    )
    if not note:
        raise Exception(
            f"Note with id {id} not found.",
        )
    if note.owner_id != current_user.id:
        raise Exception(
            "you are not the owner of this note",
        )
    # Delete the shared note entry
    shared_note = (
        db.query(SharedNotes)
        .filter(SharedNotes.note_id == id, SharedNotes.user_id == user_id)
        .first()
    )
    if not shared_note:
        raise Exception(
            f"Note is not shared with user {user_id}.",
        )
    try:
        db.delete(shared_note)
        db.commit()

    except IntegrityError as e:
        raise Exception(
            f"Error unsharing note: {str(e)}",
        )

    return  # 204 No Content for successful deletion


async def update_permission(
    current_user,
    user_id: int,
    permission: str,
    id: int,
    db: Session = SessionLocal(),
):
    note = (
        db.query(Note).filter(Note.id == id, Note.owner_id == current_user.id).first()
    )
    if not note:
        raise Exception(
            f"Note with id {id} Does not Exist",
        )
    if note.owner_id != current_user.id:
        raise Exception(
            "you are not the owner of this note",
        )
    other_user = db.query(User).filter(User.id == user_id).first()
    if not other_user:
        raise Exception(
            f"User with id {id} Does not Exist",
        )
    shared_note = (
        db.query(SharedNotes)
        .filter(SharedNotes.note_id == id, SharedNotes.user_id == user_id)
        .first()
    )
    if not shared_note:
        raise Exception(
            f"Note is not shared with user {user_id}.",
        )

    try:
        shared_note.permission = permission
        db.add(shared_note)
        db.commit()
    except IntegrityError as e:
        raise Exception(
            f"Error updating permission: {str(e)}",
        )
    return {"note": note, "user": other_user, "permission": permission}


async def list_shared_notes(
    current_user,
    db: Session = SessionLocal(),
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
):
    shared_notes = (
        db.query(Note)
        .join(SharedNotes, SharedNotes.note_id == Note.id)
        .filter(SharedNotes.user_id == current_user.id)
        .order_by(desc(Note.created_at))
        .limit(limit)
        .offset(skip)
        .all()
    )
    return shared_notes
