# bot/policy_loader.py
import os
import logging

logger = logging.getLogger(__name__)

def load_policy_text() -> str:
    path = os.environ.get("POLICY_DOCX_PATH", "/app/policy/rules.docx")
    if not os.path.exists(path):
        logger.info("Policy docx not found at %s", path)
        return ""
    try:
        from docx import Document
    except Exception:
        logger.exception("python-docx not installed")
        return ""
    try:
        doc = Document(path)
        txt = []
        for p in doc.paragraphs:
            t = p.text.strip()
            if t:
                txt.append(t)
        return "\n".join(txt)
    except Exception:
        logger.exception("Failed to load policy docx %s", path)
        return ""
