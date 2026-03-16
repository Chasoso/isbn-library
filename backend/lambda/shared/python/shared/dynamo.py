import os

import boto3

from .constants import BOOKS_TABLE_NAME_ENV


_resource = boto3.resource("dynamodb")


def get_books_table():
    table_name = os.environ[BOOKS_TABLE_NAME_ENV]
    return _resource.Table(table_name)
