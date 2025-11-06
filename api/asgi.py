#!/usr/bin/env python3
#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
ASGI entry point for RAGFlow server to run with Uvicorn.
This module wraps the Flask WSGI app as ASGI.
"""

import logging
import os
import signal
import sys
import threading
import time
import uuid

from plugin import GlobalPluginManager

logging.basicConfig(level=logging.INFO)
logging.info("RAGFlow server starting...")

from api import settings
from api.apps import app, smtp_mail_server
from api.db.runtime_config import RuntimeConfig
from api.db.services.document_service import DocumentService
from api.utils import show_configs
from api.versions import get_ragflow_version
from rag.settings import print_rag_settings
from rag.utils.mcp_tool_call_conn import shutdown_all_mcp_sessions
from rag.utils.redis_conn import RedisDistributedLock

from api.db.db_models import init_database_tables as init_web_db
from api.db.init_data import init_web_data

stop_event = threading.Event()


def update_progress():
    lock_value = str(uuid.uuid4())
    redis_lock = RedisDistributedLock("update_progress", lock_value=lock_value, timeout=60)
    logging.info(f"update_progress lock_value: {lock_value}")
    while not stop_event.is_set():
        try:
            if redis_lock.acquire():
                DocumentService.update_progress()
                redis_lock.release()
        except Exception:
            logging.exception("update_progress exception")
        finally:
            try:
                redis_lock.release()
            except Exception:
                logging.exception("update_progress exception")
            stop_event.wait(6)


def signal_handler(sig, frame):
    logging.info("Received interrupt signal, shutting down...")
    shutdown_all_mcp_sessions()
    stop_event.set()
    time.sleep(1)
    sys.exit(0)


# Initialize application
logging.info(r"""
    ____   ___    ______ ______ __
   / __ \ /   |  / ____// ____// /____  _      __
  / /_/ // /| | / / __ / /_   / // __ \| | /| / /
 / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ /
/_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/

""")
logging.info(f'RAGFlow version: {get_ragflow_version()}')

from api import utils
logging.info(f'project base: {utils.file_utils.get_project_base_directory()}')
show_configs()
settings.init_settings()
print_rag_settings()

# Check for debugpy
RAGFLOW_DEBUGPY_LISTEN = int(os.environ.get('RAGFLOW_DEBUGPY_LISTEN', "0"))
if RAGFLOW_DEBUGPY_LISTEN > 0:
    logging.info(f"debugpy listen on {RAGFLOW_DEBUGPY_LISTEN}")
    try:
        import debugpy
        debugpy.listen(("0.0.0.0", RAGFLOW_DEBUGPY_LISTEN))
    except ImportError:
        logging.warning("debugpy not installed")

# Initialize database
init_web_db()
init_web_data()

# Initialize runtime config
RuntimeConfig.DEBUG = False  # Always False for Uvicorn
RuntimeConfig.init_env()
RuntimeConfig.init_config(JOB_SERVER_HOST=settings.HOST_IP, HTTP_PORT=settings.HOST_PORT)

# Load plugins
GlobalPluginManager.load_plugins()

# Setup signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Start update_progress thread
def delayed_start_update_progress():
    logging.info("Starting update_progress thread (delayed)")
    t = threading.Thread(target=update_progress, daemon=True)
    t.start()

threading.Timer(1.0, delayed_start_update_progress).start()

# Initialize SMTP server if configured
if settings.SMTP_CONF:
    app.config["MAIL_SERVER"] = settings.MAIL_SERVER
    app.config["MAIL_PORT"] = settings.MAIL_PORT
    app.config["MAIL_USE_SSL"] = settings.MAIL_USE_SSL
    app.config["MAIL_USE_TLS"] = settings.MAIL_USE_TLS
    app.config["MAIL_USERNAME"] = settings.MAIL_USERNAME
    app.config["MAIL_PASSWORD"] = settings.MAIL_PASSWORD
    app.config["MAIL_DEFAULT_SENDER"] = settings.MAIL_DEFAULT_SENDER
    smtp_mail_server.init_app(app)

# Create ASGI wrapper
logging.info("Creating ASGI wrapper for Flask app...")
try:
    from asgiref.wsgi import WsgiToAsgi
    asgi_app = WsgiToAsgi(app)
    logging.info("Using asgiref.wsgi.WsgiToAsgi")
except ImportError:
    try:
        from a2wsgi import WSGIMiddleware
        asgi_app = WSGIMiddleware(app)
        logging.info("Using a2wsgi.WSGIMiddleware")
    except ImportError:
        logging.error("Neither asgiref nor a2wsgi found. Cannot create ASGI wrapper.")
        raise ImportError("Please install asgiref or a2wsgi: pip install asgiref")

logging.info("RAGFlow ASGI application ready")
