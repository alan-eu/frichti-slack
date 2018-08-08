from parser import CommandParser
from response import ResponseLayer
from db import dbLayer

db_layer = dbLayer()
response_layer = ResponseLayer()


def endpoint(event, context):

    print(event)
    commandHandler = CommandParser(event, db_layer, response_layer)

    return commandHandler.parse()
