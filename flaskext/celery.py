# -*- coding: utf-8 -*-
"""
    flaskext.celery
    ~~~~~~~~~~~~~~~

    Celery integration for Flask.

    :copyright: (c) 2010 Ask Solem <ask@celeryproject.org>
    :license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import os

from functools import partial

from celery.datastructures import AttributeDict
from celery.loaders import default as _default
from celery.utils import get_full_cls_name


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
                kwargs["defaults"] = conf
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
        return Worker(loglevel="INFO", **kwargs)
