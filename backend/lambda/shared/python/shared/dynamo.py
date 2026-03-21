import os
from typing import Any

import boto3

from .constants import BOOKS_TABLE_NAME_ENV, CATEGORIES_TABLE_NAME_ENV


def get_dynamodb_resource() -> Any:
    return boto3.resource("dynamodb")


def get_books_table() -> Any:
    table_name = os.environ[BOOKS_TABLE_NAME_ENV]
    return get_dynamodb_resource().Table(table_name)


def get_categories_table() -> Any:
    table_name = os.environ[CATEGORIES_TABLE_NAME_ENV]
    return get_dynamodb_resource().Table(table_name)
