# -*- coding: utf-8 -*-
"""
    flask.ext.celery
    ~~~~~~~~~~~~~~~~

    Celery integration for Flask.

    :copyright: (c) 2010-2011 Ask Solem <ask@celeryproject.org>
    :license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import argparse

from celery.app import App, AppPickler, current_app as current_celery
from celery.loaders import default as _default
from celery.utils import get_full_cls_name

from werkzeug import cached_property

from flask.ext import script


class FlaskLoader(_default.Loader):

    def read_configuration(self):
        config = self.app.flask_app.config
        settings = self.setup_settings(config)
        self.configured = True
        return settings


class FlaskAppPickler(AppPickler):

    def build_kwargs(self, flask_app, *args):
        kwargs = self.build_standard_kwargs(*args)
        kwargs["flask_app"] = flask_app
        return kwargs


class Celery(App):
    Pickler = FlaskAppPickler
    flask_app = None
    loader_cls = get_full_cls_name(FlaskLoader)

    def __init__(self, flask_app=None, *args, **kwargs):
        self.flask_app = flask_app
        super(Celery, self).__init__(*args, **kwargs)

    def __reduce_args__(self):
        return (self.flask_app, ) + super(Celery, self).__reduce_args__()



def to_Option(option, typemap={"int": int, "float": float, "string": str}):
    kwargs = vars(option)

    # convert type strings to real types.
    type_ = kwargs["type"]
    kwargs["type"] = typemap.get(type_) or type_

    # callback not supported by argparse, must use type|action instead.
    cb = kwargs.pop("callback", None)
    cb_args = kwargs.pop("callback_args", None) or ()
    cb_kwargs = kwargs.pop("callback_kwargs", None) or {}

    # action specific conversions
    action = kwargs["action"]
    if action == "store_true":
        map(kwargs.pop, ("const", "type", "nargs", "metavar", "choices"))
    elif action == "store":
        kwargs.pop("nargs")

    if kwargs["default"] == ("NO", "DEFAULT"):
        kwargs["default"] = None

    if action == "callback":

        class _action_cls(argparse.Action):

            def __call__(self, parser, namespace, values, option_string=None):
                return cb(*cb_args, **cb_kwargs)

        kwargs["action"] = _action_cls
        kwargs.setdefault("nargs", 0)

    args = kwargs.pop("_short_opts") + kwargs.pop("_long_opts")
    return script.Option(*args, **kwargs)


class Command(script.Command):

    def __init__(self, app):
        self.app = app
        super(Command, self).__init__()


class celeryd(Command):
    """Runs a Celery worker node."""

    def get_options(self):
        return filter(None, map(to_Option, self.worker.get_options()))

    def run(self, **kwargs):
        for arg_name, arg_value in kwargs.items():
            if isinstance(arg_value, list) and arg_value:
                kwargs[arg_name] = arg_value[0]
        self.worker.run(**kwargs)

    @cached_property
    def worker(self):
        from celery.bin.celeryd import WorkerCommand
        return WorkerCommand(app=current_celery())


class celerybeat(Command):
    """Runs the Celery periodic task scheduler."""

    def get_options(self):
        return filter(None, map(to_Option, self.beat.get_options()))

    def run(self, **kwargs):
        self.beat.run(**kwargs)

    @cached_property
    def beat(self):
        from celery.bin.celerybeat import BeatCommand
        return BeatCommand(app=current_celery())


class celeryev(Command):
    """Runs the Celery curses event monitor."""
    command = None

    def get_options(self):
        return filter(None, map(to_Option, self.ev.get_options()))

    def run(self, **kwargs):
        self.ev.run(**kwargs)

    @cached_property
    def ev(self):
        from celery.bin.celeryev import EvCommand
        return EvCommand(app=current_celery())


class celeryctl(Command):

    def get_options(self):
        return ()

    def handle(self, app, prog, name, remaining_args):
        if not remaining_args:
            remaining_args = ["help"]
        from celery.bin.celeryctl import celeryctl as ctl
        ctl(current_celery()).execute_from_commandline(
                ["%s celeryctl" % prog] + remaining_args)


class camqadm(Command):
    """Runs the Celery AMQP admin shell/utility."""

    def get_options(self):
        return ()

    def handle(self, app, prog, name, remaining_args):
        from celery.bin.camqadm import AMQPAdminCommand
        return AMQPAdminCommand(app=current_celery()).run(*remaining_args)


commands = {"celeryd": celeryd,
            "celerybeat": celerybeat,
            "celeryev": celeryev,
            "celeryctl": celeryctl,
            "camqadm": camqadm}


def install_commands(manager):
    for name, command in commands.items():
        manager.add_command(name, command(manager.app))
