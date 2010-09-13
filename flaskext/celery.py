# -*- coding: utf-8 -*-
"""
    flaskext.celery
    ~~~~~~~~~~~~~~~

    Celery integration for Flask.

    :copyright: (c) 2010 Ask Solem <ask@celeryproject.org>
    :license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import argparse
import os

from functools import partial, wraps

from celery.datastructures import AttributeDict
from celery.defaults import DefaultApp
from celery.loaders import default as _default
from celery.utils import get_full_cls_name

from flask import current_app
from flaskext import script


class FlaskLoader(_default.Loader):

    def __init__(self, app=None, flask_app=None):
        self.app = app
        self.flask_app = flask_app

    def read_configuration(self):
        self.configured = True
        conf = self.flask_app.config if self.flask_app else {}
        return self.setup_settings(dict(
                        _default.DEFAULT_UNCONFIGURED_SETTINGS, **conf))
os.environ.setdefault("CELERY_LOADER", get_full_cls_name(FlaskLoader))


class FlaskApp(DefaultApp):
    pass


class Celery(object):

    def __init__(self, app):
        self.app = app
        self.app.config.setdefault("CELERY_RESULT_BACKEND", "amqp")
        self.cel = FlaskApp()
        self.cel._loader = FlaskLoader(app=self.cel, flask_app=self.app)

    def create_task_cls(self):
        from celery.task.base import create_task_cls

        class BaseFlaskTask(create_task_cls(self.cel)):
            abstract = True

            @classmethod
            def apply_async(cls, *args, **kwargs):
                if not kwargs.get("connection") or kwargs.get("publisher"):
                    kwargs["connection"] = cls.establish_connection(
                            connect_timeout=kwargs.get("connect_timeout"))
                return super(BaseFlaskTask, cls).apply_async(*args, **kwargs)

        return BaseFlaskTask

    def task(self, *args, **kwargs):
        from celery.decorators import task
        if len(args) == 1 and callable(args[0]):
            return task(base=self.create_task_cls())(*args)
        if "base" not in kwargs:
            kwargs["base"] = self.create_task_cls()
            return task(*args, **kwargs)

    def Worker(self, **kwargs):
        from celery.apps.worker import Worker
        kwargs["app"] = self.cel
        return Worker(**kwargs)

    def Beat(self, **kwargs):
        from celery.apps.beat import Beat
        kwargs["app"] = self.cel
        return Beat(**kwargs)


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


class celeryd(script.Command):
    """Runs a Celery worker node."""

    def get_options(self):
        from celery.bin.celeryd import WorkerCommand
        return filter(None, map(to_Option, WorkerCommand().get_options()))

    def run(self, **kwargs):
        for arg_name, arg_value in kwargs.items():
            if isinstance(arg_value, list) and arg_value:
                kwargs[arg_name] = arg_value[0]
        celery = Celery(current_app)
        celery.Worker(**kwargs).run()


class celerybeat(script.Command):
    """Runs the Celery periodic task scheduler."""

    def get_options(self):
        from celery.bin.celerybeat import BeatCommand
        return filter(None, map(to_Option, BeatCommand().get_options()))

    def run(self, **kwargs):
        celery = Celery(current_app)
        celery.Beat(**kwargs).run()


class celeryev(script.Command):
    """Runs the Celery curses event monitor."""

    def get_options(self):
        from celery.bin.celeryev import OPTION_LIST
        return filter(None, map(to_Option, OPTION_LIST))

    def run(self, **kwargs):
        celery = Celery(current_app)
        from celery.bin.celeryev import run_celeryev
        run_celeryev(**kwargs)


class celeryctl(script.Command):

    def get_options(self):
        return ()

    def handle(self, app, prog, name, remaining_args):
        if not remaining_args:
            remaining_args = ["help"]
        from celery.bin.celeryctl import celeryctl as ctl
        ctl().execute_from_commandline(remaining_args)


class camqadm(script.Command):
    """Runs the Celery AMQP admin shell/utility."""

    def get_options(self):
        from celery.bin.camqadm import OPTION_LIST
        return filter(None, map(to_Option, OPTION_LIST))

    def run(self, *args, **kwargs):
        from celery.bin.camqadm import AMQPAdmin
        return AMQPAdmin(*args, **kwargs).run()


commands = {"celeryd": celeryd(),
            "celerybeat": celerybeat(),
            "celeryev": celeryev(),
            "celeryctl": celeryctl(),
            "camqadm": camqadm()}

def install_commands(manager):
    for name, command in commands.items():
        manager.add_command(name, command)
