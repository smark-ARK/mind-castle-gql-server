from fastapi import Depends
from strawberry import type, field, mutation, enum
from typing import List, Optional
from datetime import datetime
from enum import Enum


from app.types.types import (
    User,
    Note,
    PaginatedNotesResponse,
    SharedResponse,
    NoteWithParticipants,
    Permissions,
)
from app.helpers.note import (
    get_notes,
    create_note,
    update_note,
    get_note,
    delete_note,
    share_note,
    unshare_note,
    update_permission,
    list_shared_notes,
)
from app.oauth2 import Info


@type
class Query:
    @field
    async def notes(
        self, info: Info, q: Optional[str] = "", page: Optional[int] = 1
    ) -> PaginatedNotesResponse:
        notes = get_notes(current_user=info.context.user, q=q, page=page)
        return PaginatedNotesResponse(
            notes=notes.get("notes"), total_pages=notes.get("total_pages")
        )

    @field
    async def note(self, info: Info, id: int) -> NoteWithParticipants:
        note = await get_note(current_user=info.context.user, id=id)
        return NoteWithParticipants(
            note=note.get("note"), participants=note.get("participants")
        )

    @field
    async def shared_notes(
        self, info: Info, limit: Optional[int] = 10, skip: Optional[int] = 0
    ) -> List[Note]:
        return list_shared_notes(current_user=info.context.user, limit=limit, skip=skip)


@type
class Mutation:
    @field
    def add_note(self, info: Info, title: str, detail: str) -> Note:
        return create_note(current_user=info.context.user, title=title, detail=detail)

    @field
    def update_note(self, info: Info, id: int, title: str, detail: str) -> Note:
        return update_note(
            current_user=info.context.user,
            id=id,
            title=title,
            detail=detail,
        )

    @field
    def delete_note(self, info: Info, id: int) -> None:
        return delete_note(current_user=info.context.user, id=id)

    @field
    async def share_note(
        self,
        info: Info,
        id: int,
        user_id: int,
        permission: Optional[Permissions] = Permissions.read_only,
    ) -> SharedResponse:
        shared = await share_note(
            current_user=info.context.user,
            id=id,
            user_id=user_id,
            permission=permission,
        )
        return SharedResponse(
            note=shared.get("note"),
            user=shared.get("user"),
            Permissions=shared.get("permission"),
        )

    @field
    async def unshare_note(
        self,
        info: Info,
        id: int,
        user_id: int,
    ) -> None:
        return await unshare_note(
            current_user=info.context.user,
            id=id,
            user_id=user_id,
        )

    @field
    async def update_permission(
        self,
        info: Info,
        id: int,
        user_id: int,
        permission: Permissions = Permissions.read_only,
    ) -> SharedResponse:
        shared = await update_permission(
            current_user=info.context.user,
            id=id,
            user_id=user_id,
            permission=permission,
        )
        return await SharedResponse(
            note=shared.get("note"),
            user=shared.get("user"),
            Permissions=shared.get("permission"),
        )
