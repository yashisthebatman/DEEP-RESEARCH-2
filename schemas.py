# schemas.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union

class ResearchRequest(BaseModel):
    area: str

class ChartDataset(BaseModel):
    label: str
    data: List[Union[int, float]]
    backgroundColor: Optional[Union[str, List[str]]] = None
    borderColor: Optional[Union[str, List[str]]] = None

class ChartData(BaseModel):
    type: str
    labels: List[str]
    datasets: List[ChartDataset]
    title: Optional[str] = None
    source: Optional[str] = None

class ReportResponse(BaseModel):
    report_id: str
    area_name: str
    full_report_markdown: str
    charts: List[ChartData] = []
    full_text_for_follow_up: str

class QuestionRequest(BaseModel):
    report_id: str
    question: str
    report_context: str

class AnswerResponse(BaseModel):
    answer: str

# Removed PDFExportRequest schema
# class PDFExportRequest(BaseModel):
#     html_content: str
#     area_name: str