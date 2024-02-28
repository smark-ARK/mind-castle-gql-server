from strawberry import type, field, enum
from typing import List
from enum import Enum
from datetime import datetime


@type
class User:
    id: int
    username: str
    email: str


@enum
class Permissions(str, Enum):
    read_only = "read_only"
    edit = "edit"


@type
class Note:
    id: int
    title: str
    detail: str
    created_at: datetime
    owner_id: int
    owner: User


@type
class PaginatedNotesResponse:
    notes: List[Note]
    total_pages: int


@type
class Participant:
    user: User
    permission: str


@type
class NoteWithParticipants:
    note: Note
    participants: List[Participant]


@type
class SharedResponse:
    note: Note
    user: User
    Permissions: str
