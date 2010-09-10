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
from celery.loaders import default as _default
from celery.utils import get_full_cls_name

from flask import current_app
from flaskext import script


class FlaskLoader(_default.Loader):

    def read_configuration(self):
        self.configured = True
        return self.setup_settings(_default.DEFAULT_UNCONFIGURED_SETTINGS)
os.environ.setdefault("CELERY_LOADER", get_full_cls_name(FlaskLoader))


class Celery(object):

    def __init__(self, app):
        self.app = app
        self.conf = AttributeDict()
        self.app.config.setdefault("CELERY_RESULT_BACKEND", "amqp")

        from celery.conf import prepare
        prepare(self.conf, AttributeDict(self.app.config))

    def create_task_cls(self):
        from celery.backends import default_backend, get_backend_cls
        from celery.task.base import Task
        defaults = self.conf

        class BaseFlaskTask(Task):
            abstract = True
            app = self.app
            ignore_result = defaults.IGNORE_RESULT
            serializer = defaults.TASK_SERIALIZER
            rate_limit = defaults.DEFAULT_RATE_LIMIT
            track_started = defaults.TRACK_STARTED
            acks_late = defaults.ACKS_LATE
            backend = get_backend_cls(defaults.RESULT_BACKEND)()

            @classmethod
            def apply_async(cls, *args, **kwargs):
                if not kwargs.get("connection") or kwargs.get("publisher"):
                    kwargs["connection"] = cls.establish_connection(
                            connect_timeout=kwargs.get("connect_timeout"))
                return super(BaseFlaskTask, cls).apply_async(*args, **kwargs)

            @classmethod
            def establish_connection(cls, *args, **kwargs):
                from celery.messaging import establish_connection
                kwargs["defaults"] = defaults
                return establish_connection(*args, **kwargs)

        return BaseFlaskTask

    def task(self, *args, **kwargs):
        from celery.decorators import task
        if len(args) == 1 and callable(args[0]):
            return task(base=self.create_task_cls())(*args)
        if "base" not in kwargs:
            kwargs["base"] = self.create_task_cls()
            return task(*args, **kwargs)

    def Worker(self, **kwargs):
        from celery.bin.celeryd import Worker
        kwargs["defaults"] = self.conf
        return Worker(**kwargs)

    def Beat(self, **kwargs):
        from celery.bin.celerybeat import Beat
        kwargs["defaults"] = self.conf
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
        from celery.bin.celeryd import OPTION_LIST
        return filter(None, map(to_Option, OPTION_LIST))

    def run(self, **kwargs):
        celery = Celery(current_app)
        celery.Worker(**kwargs).run()


class celerybeat(script.Command):
    """Runs the Celery periodic task scheduler."""

    def get_options(self):
        from celery.bin.celerybeat import OPTION_LIST
        return filter(None, map(to_Option, OPTION_LIST))

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
