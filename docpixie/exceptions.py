"""
Custom exceptions for DocPixie RAG Agent
"""


class DocPixieError(Exception):
    """Base exception for DocPixie errors"""
    pass


class ContextProcessingError(DocPixieError):
    """Error occurred during conversation context processing"""
    pass


class QueryReformulationError(DocPixieError):
    """Error occurred during query reformulation"""
    pass


class QueryClassificationError(DocPixieError):
    """Error occurred during query classification"""
    pass


class TaskPlanningError(DocPixieError):
    """Error occurred during task planning or document selection"""
    pass


class PageSelectionError(DocPixieError):
    """Error occurred during page selection"""
    pass


class TaskAnalysisError(DocPixieError):
    """Error occurred during task analysis"""
    pass


class ResponseSynthesisError(DocPixieError):
    """Error occurred during response synthesis"""
    pass


class DocumentSelectionError(DocPixieError):
    """Error occurred during document selection"""
    pass


class PlanUpdateError(DocPixieError):
    """Error occurred during adaptive plan updates"""
    pass