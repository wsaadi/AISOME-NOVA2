"""
Framework Base Classes — Contrats abstraits que tout agent, tool et connecteur doit implémenter.
"""

from app.framework.base.agent import BaseAgent
from app.framework.base.connector import BaseConnector
from app.framework.base.tool import BaseTool

__all__ = ["BaseAgent", "BaseTool", "BaseConnector"]
