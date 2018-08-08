import html
import json
from urllib.parse import parse_qs

import requests


class Action:
    clear = 'clear'
    edit = 'edit'
    order = 'order'
    list = 'list'

class CallbackAction:
    selected_dish = 'selected_dish'
    remove = 'remove'
    cancel = 'cancel'


class CallbackId:
    edit = 'edit'
    clear = 'clear'


AVAILABLE_ACTIONS = ('starter', 'main', 'dessert', 'extra', 'edit', 'clear', 'list', 'order')
AVAILABLE_DISH_TYPES = ('starter', 'main', 'dessert', 'extra')

class CommandParser():


    def __init__(self, event, db_layer, response_layer):
        self.body = parse_qs(event['body'])

        if 'payload' in self.body:  # Callback
            self.payload = json.loads(self.body['payload'][0])
            self.callback_id = self.payload['callback_id']
            self.callback_action = self.payload['actions'][0]
            self.team_id = self.payload['team']['id']
            self.user_id = self.payload['user']['id']
            self.user_name = self.payload['user']['name']
            self.response_url = self.payload['response_url']

        else:  # Command
            self.payload = None
            self.team_id = self.body['team_id'][0]
            self.user_id = self.body['user_id'][0]
            self.user_name = self.body['user_name'][0]
            self.command = self.body['text'][0]

        self.db_layer = db_layer
        self.response_layer = response_layer

    def parse(self):
        if self.payload:
            result = self._parseCallback()
        else:
            result = self._parseCommand()

        return result

    def _parseCallback(self):

        if self.callback_id == CallbackId.edit:

            callback_action_name = self.callback_action['name']

            if callback_action_name == CallbackAction.selected_dish:
                data = self.db_layer.get_user_item(self.team_id, self.user_id)

                selected_dish = html.unescape(self.callback_action['selected_options'][0]['value'])
                callback_response_body = self.response_layer.edit_response(data, selected_dish)

            elif callback_action_name == CallbackAction.remove:
                selected_dish = html.unescape(self.callback_action['value'])
                self.db_layer.remove_dish(self.team_id, self.user_id, selected_dish)

                data = self.db_layer.get_user_item(self.team_id, self.user_id)
                callback_response_body = self.response_layer.edit_response(data)

            elif callback_action_name == CallbackAction.cancel:
                data = self.db_layer.get_user_item(self.team_id, self.user_id)
                callback_response_body = self.response_layer.list_user_dishes(data)


        elif self.callback_id == CallbackId.clear:

            callback_action_name = self.callback_action['name']

            if callback_action_name == CallbackAction.cancel:
                callback_response_body = self.response_layer.cancel_clear_response()

            elif callback_action_name == CallbackAction.remove:
                self.db_layer.delete_team(self.team_id)
                callback_response_body = self.response_layer.confirm_clear_response()

        requests.post(self.response_url, json=callback_response_body)
        return self.response_layer.format_response()

    def _parseCommand(self):
        body = {}
        if '/frichti' in self.command:
            body = self.response_layer.several_commands_response()
        else:
            args = self.command.split(' ')
            action = args[0]

            if action not in AVAILABLE_ACTIONS:
                body = self.response_layer.not_available_action()

            if action in AVAILABLE_DISH_TYPES:

                if len(args) == 1:
                    body = self.response_layer.no_dish()
                else:

                    dishes = ' '.join(args[1:]).split(';')
                    dishes = [item.strip() for item in dishes]

                    self.db_layer.add_dish(self.team_id, self.user_id, self.user_name, action, *dishes)

                    body = self.response_layer.dishes_added_response()

            elif action == Action.edit:

                data = self.db_layer.get_user_item(self.team_id, self.user_id)

                body = self.response_layer.edit_response(data)

            elif action == Action.list:

                if len(args) == 1:

                    data = self.db_layer.get_user_item(self.team_id, self.user_id)
                    body = self.response_layer.list_user_dishes(data)

                else:
                    if args[1] == 'team':
                        data = self.db_layer.get_team_items(self.team_id)
                        body = self.response_layer.list_team_dishes(data)
                    else:
                        body = self.response_layer.not_available_list_action()

            elif action == Action.order:

                data = self.db_layer.get_team_items(self.team_id)
                body = self.response_layer.order_response(data)

            elif action == Action.clear:

                body = self.response_layer.clear_db()

        return self.response_layer.format_response(body)
