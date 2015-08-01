#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# EM Slack Roll
# Copyright (c) 2015 Erin Morelli
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
'''
Module: slack_roll.roll

    - Parses POST data from Slack
    - Parses user roll request
    - Retrieves and returns roll data
'''

import re
import random
import argparse
import slack_roll as sr
from slacker import Chat, Error
from slack_roll.storage import Users


# Set globals
ERRORS = []
COMMAND = None


class RollParser(argparse.ArgumentParser):
    ''' Custom ArgumentParser object for special error and help messages.
    '''

    def error(self, message):
        ''' Stores all error messages in global errors list
        '''
        global ERRORS
        ERRORS.append(message)

    def print_help(self):
        ''' Generates help and list messages
        '''
        global ERRORS
        global COMMAND

        help_msg = "*{app_name}* can roll anywhere from "
        help_msg += "*1-100 dice* with *4-100 sides* each.\n"
        help_msg += "Here are some examples:\n\n"
        help_msg += "`{command}`\n\tRolls a single 6-sided die\n\n"
        help_msg += "`{command} d20`\n\tRolls a single 20-sided die\n\n"
        help_msg += "`{command} 4d10`\n\tRolls 4 10-sided dice\n\n"
        help_msg += "`{command} 1d6+3`\n\t"
        help_msg += "Rolls a single 6-sided die with a +3 modifier\n\n"
        help_msg += "`{command} help`\n\tShows this message\n"

        ERRORS.append(help_msg.format(
            app_name=sr.PROJECT_INFO['name_full'],
            command=COMMAND
        ))


class RollAction(argparse.Action):
    ''' Custom Action object for validating and parsing roll arguments
    '''

    def __call__(self, parser, namespace, values, option_string=None):
        ''' Validates flip arguments and stores them to namespace
        '''
        dice_roll = values.lower()

        # Check for help
        if dice_roll == 'help':
            parser.print_help()
            return

        # Set defaults
        count = 1
        sides = 6
        modifier = None
        modifier_count = None

        # Parse the roll
        result = re.match(r'(\d+)?d(\d+)(?:([-+])(\d+))?', dice_roll, re.I)

        # Check that roll is valid
        if result is None:
            parser.error(
                "'{0}' is not a recognized roll format".format(dice_roll))

        # Get the number of dice
        if result.group(1) is not None:
            count = int(result.group(1))

            # Set 100 count max
            if count > 100:
                count = 100

            # Set 1 count min
            if count < 1:
                count = 1

        # Get the number of sides
        if result.group(2) is not None:
            sides = int(result.group(2))

            # Set 100 side max
            if sides > 100:
                sides = 100

            # Set 4 side min
            if sides < 4:
                sides = 4

        # Get the modifiers
        if result.group(3) is not None:

            if result.group(4) is None:
                return "ERROR"

            modifier = result.group(3)
            modifier_count = int(result.group(4))

        # Set values
        setattr(namespace, 'count', count)
        setattr(namespace, 'sides', sides)
        setattr(namespace, 'modifier', modifier)
        setattr(namespace, 'modifier_count', modifier_count)

        return


def get_parser():
    ''' Sets up and returns custom ArgumentParser object
    '''

    # Create roll parser
    parser = RollParser()

    # Add valid args
    parser.add_argument('dice_roll', action=RollAction)

    return parser


def check_token(args):
    ''' Checks that the team is authenticated with the app
        Returns authenticated team token data
    '''

    # Set not authenticated error message
    auth_msg = "{0} is not authorized to post in this team: {1}"
    auth_error = auth_msg.format(
        sr.PROJECT_INFO['name_full'],
        '*<{0}|Click here to authorize>*'.format(sr.PROJECT_INFO['auth_url'])
    )

    # Look for team in DB
    team = Users.query.get(args['team_id'])

    # Validate team
    if not team:
        return False, auth_error

    # Return token
    return True, team.token


def do_roll(roll, user):
    ''' Performs requested roll
    '''

    # Trackers
    roll_sum = 0
    roll_result = []
    roll_modifier = ''

    # Roll dice
    for count in range(0, roll.count):
        die_roll = random.randint(1, roll.sides)
        roll_sum += die_roll
        roll_result.append(die_roll)

    # Deal with modifier
    if roll.modifier is not None:
        roll_modifier = '  {0} {1}'.format(roll.modifier, roll.modifier_count)

        if roll.modifier == '-':
            roll_sum -= roll.modifier_count

        elif roll.modifier == '+':
            roll_sum += roll.modifier_count

    # Format message
    formatted_result = ',  '.join(str(result) for result in roll_result)

    # Set plural
    die_word = 'dice'

    # Set singular case
    if roll.count == 1:
        die_word = 'die'

    # Set response
    response = '_{user} rolled {count} {sides}-sided {die}:_'.format(
        user=user,
        count=roll.count,
        sides=roll.sides,
        die=die_word
    )

    # Return response with results
    return '{response}  *{sum}*  ( {results} ){modifier}'.format(
        response=response,
        sum=roll_sum,
        results=formatted_result,
        modifier=roll_modifier
    )


def send_roll(token, roll, args):
    ''' Posts the roll to Slack
    '''

    # Set up chat object
    chat = Chat(token)

    try:
        # Attempt to post message
        chat.post_message(
            args['channel_id'],
            roll,
            username='Roll Bot',
            icon_emoji=':game_die:'
        )

    except Error as err:
        # Report if we got any errors
        return err

    # Return successful
    return


def make_roll(args):
    ''' Wrapper function for roll functions
        Returned error messages will post as private slackbot messages
    '''

    # Reset global error traker
    global ERRORS
    ERRORS = []

    # Make sure this is a valid slash command
    if args['command'] not in sr.ALLOWED_COMMANDS:
        return '"{0}" is not an allowed command'.format(args['command'])

    else:
        # Set global command value to access later
        global COMMAND
        COMMAND = args['command']

    # Check to see if user has authenticated with the app
    (valid, token) = check_token(args)

    # If the user is not valid, let them know
    if not valid:
        return token

    # If there's no input, use the default roll
    if not args['text']:
        dice_roll = 'd6'
    else:
        dice_roll = args['text']

    # Get parser
    parser = get_parser()

    # Parse args
    result = parser.parse_args([dice_roll])

    # Report any errors from parser
    if len(ERRORS) > 0:
        return ERRORS[0]

    # Get requested flip
    roll = do_roll(result, args['user_name'])

    # Post flip as user
    err = send_roll(token, roll, args)

    # If there were problems posting, report it
    if err is not None:
        return err

    # Return successful
    return ('', 204)
