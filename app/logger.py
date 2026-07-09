import logging
import json
import uuid
from contextvars import ContextVar
from datetime import datetime

# Context variables for structured logging
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
chat_id_var: ContextVar[str] = ContextVar("chat_id", default="")
uid_var: ContextVar[str] = ContextVar("uid", default="")

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add context vars if present
        req_id = request_id_var.get()
        if req_id: log_obj["request_id"] = req_id
            
        chat_id = chat_id_var.get()
        if chat_id: log_obj["chat_id"] = chat_id
            
        uid = uid_var.get()
        if uid: log_obj["uid"] = uid

        # Add any extra operational metadata passed via `extra={"operational_metadata": {...}}`
        if hasattr(record, "operational_metadata"):
            log_obj.update(record.operational_metadata)
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logging():
    logger = logging.getLogger()
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Silence chatty loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
