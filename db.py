import os

import boto3
from datetime import datetime, timedelta

import pytz


class dbLayer():
    def __init__(self):
        dynamo = boto3.resource("dynamodb")
        self.table = dynamo.Table(os.environ['ORDER_TABLE'])
        self.clear_hour = int(os.environ['CLEAR_HOUR'])
        self.local_timezone = pytz.timezone('Europe/Paris')

    def _key(self, team_id, user_id):
        return {'team_id': team_id, 'user_id': user_id}

    def delete_team(self, team_id):

        items = self.get_team_items(team_id)

        for item in items:
            self.table.delete_item(Key=self._key(item['team_id'], item['user_id']))

        return True

    def delete_user(self, team_id, user_id):

        self.table.delete_item(Key=self._key(team_id, user_id))

        return True

    def get_team_items(self, team_id):

        result = self.table.query(
            KeyConditionExpression='team_id = :team_id',
            ExpressionAttributeValues={
                ':team_id': team_id
            }
        )

        if result['ResponseMetadata']['HTTPStatusCode'] == 200:
            return result['Items']
        else:
            # todo: handle this case
            return []

    def get_user_item(self, team_id, user_id):

        result = self.table.get_item(Key=self._key(team_id, user_id))

        if 'Item' in result:
            return result['Item']
        else:
            return {}

    def remove_dish(self, team_id, user_id, dish_name):

        item = self.get_user_item(team_id, user_id)

        updated_dishes = []
        if 'dishes' in item:
            for dish in item['dishes']:
                if dish['dish_name'] != dish_name:
                    updated_dishes.append(dish)

        if updated_dishes:
            item['dishes'] = updated_dishes
            self.table.put_item(Item=item)
        else:
            self.delete_user(team_id, user_id)

        return True

    def add_dish(self, team_id, user_id, user_name, dish_type, *dish_names):

        new_dishes = []
        for dish_name in dish_names:
            dish = {'dish_type': dish_type, 'dish_name': dish_name}
            new_dishes.append(dish)

        tomorrow = datetime.utcnow() + timedelta(days=1)

        ttl_ts = int(tomorrow\
            .astimezone(self.local_timezone)\
            .replace(hour=self.clear_hour, minute=0, second=0, microsecond=0)\
            .astimezone(pytz.utc)\
            .timestamp())

        result = self.table.update_item(
            Key=self._key(team_id, user_id),
            UpdateExpression='SET dishes = list_append(if_not_exists(dishes, :empty_list), :new_dishes), user_name = :user_name, ttl_ts = :ttl_ts',
            ExpressionAttributeValues={
                ':empty_list': [],
                ':new_dishes': new_dishes,
                ':user_name': user_name,
                ':ttl_ts': ttl_ts
            },
            ReturnValues='NONE',
        )

        return result['ResponseMetadata']['HTTPStatusCode'] == 200
