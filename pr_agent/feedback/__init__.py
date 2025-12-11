# AGPL-3.0 License

"""
Feedback learning system for PR-Agent.

This module logs user actions and builds preference models
to dynamically tune suggestions based on team feedback.
"""

from pr_agent.feedback.feedback_logger import FeedbackLogger
from pr_agent.feedback.feedback_event import FeedbackEvent, FeedbackEventData
from pr_agent.feedback.preference import Preference

__all__ = [
    "FeedbackLogger",
    "FeedbackEvent",
    "FeedbackEventData",
    "Preference",
]
