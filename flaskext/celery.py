from __future__ import absolute_import

import os

from flask import g

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
        conf = self.conf

        class BaseFlaskTask(Task):
            abstract = True
            app = self.app
            ignore_result = conf.IGNORE_RESULT
            serializer = conf.TASK_SERIALIZER
            rate_limit = conf.DEFAULT_RATE_LIMIT
            track_started = conf.TRACK_STARTED
            acks_late = conf.ACKS_LATE
            backend = get_backend_cls(conf.RESULT_BACKEND)()

            @classmethod
            def apply_async(self, *args, **kwargs):
                if not kwargs.get("connection") or kwargs.get("publisher"):
                    kwargs["connection"] = self.establish_connection(
                            connect_timeout=kwargs.get("connect_timeout"))
                return super(BaseFlaskTask, self).apply_async(*args, **kwargs)

            @classmethod
            def establish_connection(self, *args, **kwargs):
                from celery.messaging import establish_connection
                kwargs["defaults"] = conf
                return establish_connection(*args, **kwargs)

        return BaseFlaskTask

    def task(self, *args, **kwargs):
        from celery.decorators import task
        kwargs.setdefault("base", self.create_task_cls())
        return task(*args, **kwargs)

    def Worker(self, **kwargs):
        from celery.bin.celeryd import Worker
        kwargs["defaults"] = self.conf
        return Worker(loglevel="INFO", **kwargs)
