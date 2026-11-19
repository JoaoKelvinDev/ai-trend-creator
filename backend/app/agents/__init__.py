"""Agentes LLM da aplicação."""

from backend.app.agents.trend_analyst import TrendAnalyst, assess_cluster_trends, TREND_ANALYST_PROMPT_V1
from backend.app.agents.content_strategist import ContentStrategist, create_content_plan_use_case, CONTENT_STRATEGIST_PROMPT_V1
from backend.app.agents.scriptwriter import Scriptwriter, write_script_use_case, SCRIPTWRITER_PROMPT_V1
from backend.app.agents.storyboarder import Storyboarder, create_storyboard_use_case, STORYBOARDER_PROMPT_V1

__all__ = [
    "TrendAnalyst",
    "assess_cluster_trends",
    "TREND_ANALYST_PROMPT_V1",
    "ContentStrategist",
    "create_content_plan_use_case",
    "CONTENT_STRATEGIST_PROMPT_V1",
    "Scriptwriter",
    "write_script_use_case",
    "SCRIPTWRITER_PROMPT_V1",
    "Storyboarder",
    "create_storyboard_use_case",
    "STORYBOARDER_PROMPT_V1",
]