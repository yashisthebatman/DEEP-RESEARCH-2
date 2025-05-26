# app.py
from fastapi import FastAPI, Request, HTTPException # Removed Body as it was for PDFExportRequest
from fastapi.responses import HTMLResponse # Removed FileResponse/Response for PDF
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import uvicorn
import os
# Removed tempfile, io, and PDF library imports

from schemas import ResearchRequest, ReportResponse, QuestionRequest, AnswerResponse # Removed PDFExportRequest
from services import conduct_deep_research, answer_follow_up_question, generate_report_id

# Removed WEASYPRINT_AVAILABLE / REPORTLAB_PISA_AVAILABLE flags

load_dotenv()

app = FastAPI(
    title="AI Regional Health Analyzer",
    description="API for conducting extremely detailed regional health analysis using Perplexity AI.",
    version="0.3.2" # Updated version
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

generated_reports_cache = {} 

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/research", response_model=ReportResponse)
async def create_research_report(research_request: ResearchRequest):
    area = research_request.area.strip()
    if not area:
        raise HTTPException(status_code=400, detail="Area cannot be empty.")

    print(f"Received comprehensive health analysis request for area: {area}")
    
    report_id = generate_report_id(area)
    if report_id in generated_reports_cache:
        print(f"Returning cached report for area: {area}, ID: {report_id}")
        return generated_reports_cache[report_id]

    try:
        report_dict_data = await conduct_deep_research(area)
        response_model = ReportResponse(**report_dict_data)
        generated_reports_cache[response_model.report_id] = response_model
        print(f"Comprehensive health analysis complete for: {area}. Report ID: {response_model.report_id}")
        return response_model
    except Exception as e:
        print(f"Error during research for area '{area}': {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to conduct research: {str(e)}")

@app.post("/ask", response_model=AnswerResponse)
async def ask_follow_up(question_request: QuestionRequest):
    report_id = question_request.report_id
    question = question_request.question.strip()
    report_context = question_request.report_context

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not report_context:
        cached_report = generated_reports_cache.get(report_id)
        if not cached_report or not cached_report.full_text_for_follow_up:
             raise HTTPException(status_code=400, detail="Report context is missing and not found in cache.")
        report_context = cached_report.full_text_for_follow_up
        print(f"Used cached report context for report ID: {report_id}")

    print(f"Received follow-up question: '{question}' for report ID: {report_id}")

    try:
        answer_text = await answer_follow_up_question(question, report_context)
        return AnswerResponse(answer=answer_text)
    except Exception as e:
        print(f"Error answering follow-up question: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get answer: {str(e)}")

# Removed the @app.post("/export-pdf") endpoint entirely
# Removed BackgroundTask class if it was only for PDF export

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)