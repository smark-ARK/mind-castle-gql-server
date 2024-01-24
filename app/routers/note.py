from fastapi import APIRouter

from app.types.note import Query, Mutation
from strawberry import Schema
from strawberry.fastapi import GraphQLRouter
from app.oauth2 import get_context

schema = Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema=schema, context_getter=get_context)
