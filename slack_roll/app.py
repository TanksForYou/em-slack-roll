#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
EM Slack Roll module: slack_roll.app.

    - Flask server configuration

Copyright (c) 2015-2016 Erin Morelli

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.
"""

from flask import redirect, render_template, request
import slack_roll.auth as auth
import slack_roll.roll as roll
from slack_roll import APP, PROJECT_INFO, ALLOWED_COMMANDS, report_event


@APP.route('/', methods=['GET', 'POST'])
def home():
    """Render app homepage template."""
    if request.method == 'POST':
        report_event('post_request', request.form.to_dict())
        return roll.make_roll(request.form.to_dict())

    else:
        return render_template(
            'index.html',
            project=PROJECT_INFO,
            allowed_commands=ALLOWED_COMMANDS
        )


@APP.route('/authenticate')
def authenticate():
    """Redirect to generated Slack authentication url."""
    return redirect(auth.get_redirect())


@APP.route('/validate')
def validate():
    """Validate the returned values from authentication."""
    return redirect(auth.validate_return(request.args.to_dict()))
