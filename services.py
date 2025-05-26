# services.py
import os
import httpx
from dotenv import load_dotenv
import hashlib
import ast
import json
import re

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not PERPLEXITY_API_KEY:
    print("CRITICAL ERROR: PERPLEXITY_API_KEY not found in .env file. Application will not function.")

API_BASE_URL = "https://api.perplexity.ai/chat/completions"
RESEARCH_MODEL_NAME = "sonar-deep-research"
FOLLOW_UP_MODEL_NAME = "sonar"

def generate_report_id(area_name: str) -> str:
    return hashlib.md5(area_name.lower().encode()).hexdigest()[:12]

SECTION_STRUCTURE_GUIDE = {
    "title_page": "Comprehensive Report on Healthcare in {area_name}: Diseases, Emerging Risks, and Government Schemes",
    "table_of_contents": "Contents",
    "introduction": "1. Introduction",
    "major_diseases": "2. Major Diseases in {area_name}",
    "emerging_risks": "3. Emerging Health Risks & Trends in {area_name}",
    "govt_schemes": "4. Government Healthcare Schemes & Initiatives in {area_name}",
    "healthcare_system": "5. Healthcare Infrastructure & System in {area_name}",
    "challenges_recommendations": "6. Key Challenges, Opportunities, and Strategic Recommendations for {area_name}",
    "conclusion": "7. Conclusion",
    "references": "References"
}

def _get_detailed_focus_points_for_prompt(area_name: str) -> dict:
    # Adding hints for more charts within focus points
    return {
        "introduction": [
            f"Provide a comprehensive and detailed overview of **'{area_name}'**, its demographic profile (population size, age structure - *consider a pie/bar chart for age distribution if data is available*, density, urbanization rate), and its broad socio-economic context.",
            f"Give a general introduction to **'{area_name}'s** healthcare system landscape.",
            f"State the main objectives and scope of this report."
        ],
        "major_diseases": [
            f"**Under a subsection titled `### 2.1. Communicable Diseases`:**",
            f"  - Detailed analysis of prevalent communicable diseases in **'{area_name}'**. For each major disease: incidence/prevalence rates (with trends - *consider line charts for trends of 2-3 key diseases*), mortality, affected populations, control programs, challenges.",
            f"**Under a subsection titled `### 2.2. Non-Communicable Diseases (NCDs)`:**",
            f"  - In-depth discussion of major NCDs in **'{area_name}'**. For each NCD group: prevalence rates and trends (*line/bar chart for trends or comparison of prevalence of top 2-3 NCDs*), risk factors, impact, management strategies, screening programs."
        ],
        "emerging_risks": [
            f"**Under a subsection titled `### 3.1. Zoonotic Diseases`:** (Discuss notable emerging zoonotic diseases, potential, surveillance, preparedness.)",
            f"**Under a subsection titled `### 3.2. Antimicrobial Resistance (AMR)`:** (Analyze AMR situation, pathogen resistance patterns - *consider a table or bar chart for resistance levels of key pathogens to common antibiotics*, drivers, action plans.)",
            f"**Under a subsection titled `### 3.3. Environmental Health Risks`:** (Detail impacts of air/water pollution, climate change on health - *if specific data on pollution levels vs health outcomes is found, consider a chart*.)",
            f"**Under a subsection titled `### 3.4. Mental Health`:** (Overview of mental health landscape, prevalence of common disorders - *bar chart comparing prevalence of 2-3 common disorders if data available*, services, stigma, initiatives.)",
            f"**Under a subsection titled `### 3.5. Population Health Trends & Analysis:`** (Analyze demographic shifts - *ageing trend line chart*, nutritional status - *pie/bar chart for malnutrition categories*, lifestyle changes and their health implications. Discuss health equity.)"
        ],
        "govt_schemes": [
            f"**Under a subsection titled `### 4.1. [Major National Scheme 1 for {area_name}]:`** (Extremely detailed analysis: objectives, coverage - *bar chart for beneficiary numbers over years if available*, services, impact, challenges.)",
            f"**Under a subsection titled `### 4.2. [Major National Scheme 2 for {area_name}]:`** (Similar extensive analysis, achievements - *consider a chart for a key performance indicator like IMR/MMR reduction under the scheme if data is directly attributable*.)",
            f"**Under a subsection titled `### 4.3. Other Key Local/Regional Schemes & Public Health Programs:`** (Describe scope, impact.)"
        ],
        "healthcare_system": [
            f"**Under a subsection titled `### 5.1. Healthcare Facilities:`** (Detail availability, distribution, quality of facilities. Quantitative data on numbers, bed strength - *bar chart comparing facility types or beds per 1000 in different regions if feasible*.)",
            f"**Under a subsection titled `### 5.2. Human Resources for Health (HRH):`** (Discuss availability, density, distribution of health workers. Doctor-population ratios, nurse-population ratios - *bar chart comparing HRH density to benchmarks or across regions*.)",
            f"**Under a subsection titled `### 5.3. Health Financing & Expenditure:`** (Describe financing sources. Health expenditure as % of GDP, OOP - *pie chart for health expenditure breakdown by source; line chart for OOP trend*.)",
            f"**Under a subsection titled `### 5.4. Access to Care & Health Equity:`** (Analyze access issues, disparities.)",
            f"**Under a subsection titled `### 5.5. Pharmaceutical Sector & Supply Chain Management:`** (Discuss pharma industry, drug procurement, availability of essential medicines.)",
            f"**Under a subsection titled `### 5.6. Health Information Systems (HIS) & Digital Health Initiatives:`** (Describe state of HIS, use of digital health technologies.)"
        ],
        "challenges_recommendations": [
            f"**Under a subsection titled `### 6.1. Major Health System Challenges:`** (Synthesize and discuss key problems.)",
            f"**Under a subsection titled `### 6.2. Opportunities for Improvement:`** (Identify strengths and potential levers.)",
            f"**Under a subsection titled `### 6.3. Strategic, Actionable, and Evidence-Informed Recommendations:`** (Propose 3-5 recommendations.)"
        ],
        "conclusion": [
            f"Summarize main findings, reiterate key status, challenges, opportunities.",
            f"Offer insightful future outlook for health in **'{area_name}'**."
        ],
        "references": [
            f"Provide a comprehensive list of all cited sources alphabetically."
        ]
    }

async def get_perplexity_response(prompt_content: str, model_name: str, system_prompt_content: str = None, max_tokens: int = 8192, temperature: float = 0.3) -> str:
    if not PERPLEXITY_API_KEY:
        return "Error: API Key is not configured on the server."

    if system_prompt_content is None:
        # UPDATED System Prompt
        system_prompt_content = (
            "You are an AI report writing machine. Your SOLE function is to produce the report text EXACTLY as requested by the user's prompt structure. "
            "DO NOT include ANY conversational phrases, introductory remarks, summaries of your understanding, self-corrections, or ANY text whatsoever that is not part of the direct report content. "
            "If you have any internal planning, thoughts, or meta-commentary about the generation process, you MUST enclose this information in <think>Your thought here</think> tags. These tags and their content will be programmatically removed and MUST NOT appear in the final report body. "
            "Your final output, after these <think> tags are notionally removed, MUST begin *EXACTLY* with the specified report title (e.g., 'Comprehensive Report on Healthcare in...')."
        )
    
    messages = [{"role": "system", "content": system_prompt_content}, {"role": "user", "content": prompt_content}]
    payload = {"model": model_name, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json", "Accept": "application/json"}
    timeout_duration = 900.0 # 15 minutes

    try:
        async with httpx.AsyncClient(timeout=timeout_duration) as client:
            print(f"Sending prompt to Perplexity (model: {model_name}, prompt length: {len(prompt_content)} chars). Expecting a long response.")
            response = await client.post(API_BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()

        if response_data.get("choices") and response_data["choices"][0].get("message"):
            raw_content = response_data["choices"][0]["message"]["content"]
            print(f"Raw response received from {model_name} (length: {len(raw_content)} chars).")

            # STAGE 1: Remove <think>...</think> blocks
            # Using re.DOTALL to ensure newlines within <think> tags are matched, and re.IGNORECASE
            content_without_thoughts = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL | re.IGNORECASE).strip()
            # .strip() here is important to remove any leading/trailing whitespace left by the removal
            print(f"Content after stripping <think> tags (length: {len(content_without_thoughts)} chars).")

            # STAGE 2: Find the report start marker in the *cleaned* content and remove any preceding text
            report_start_marker = "Comprehensive Report on Healthcare in" 
            
            # Find the marker, ignoring case for robustness
            actual_start_index = content_without_thoughts.lower().find(report_start_marker.lower())

            if actual_start_index == 0: 
                # Ideal case: report starts exactly as expected after thought removal and stripping leading/trailing whitespace.
                cleaned_content = content_without_thoughts
                print(f"Report starts correctly after <think> tag removal. Final content length: {len(cleaned_content)} chars.")
            elif actual_start_index > 0: 
                # Report title found, but there's some preamble *after* <think> tag removal.
                # This means the AI put some text (not in <think> tags) before the title. Strip it.
                print(f"WARNING: Untagged preamble detected before report title AFTER <think> tag removal. Stripping it. Original start index in thought-stripped content: {actual_start_index}")
                cleaned_content = content_without_thoughts[actual_start_index:]
                print(f"Preamble stripped. Final cleaned content length: {len(cleaned_content)} chars.")
            else: # actual_start_index == -1; marker not found
                # This is a more problematic case. The AI didn't start with the title.
                print(f"CRITICAL WARNING: Report start marker ('{report_start_marker}') NOT FOUND in AI response AFTER <think> tag removal. AI did not follow crucial instructions. Returning the <think>-stripped content as is, but it's likely malformed or incomplete.")
                cleaned_content = content_without_thoughts 
                # You might want to return an error string or the raw (but thought-stripped) content for debugging.
                # For now, returning what we have, which might be the AI's attempt at the report without the proper title.

            return cleaned_content.strip() # Final strip for safety
        else:
            error_msg = response_data.get("error", {}).get("message", "Unknown API response format.")
            print(f"API Error (model: {model_name}): {error_msg} Full response: {json.dumps(response_data, indent=2)}")
            return f"Error: AI API returned an error: {error_msg}"
    except httpx.HTTPStatusError as http_err:
        error_content = "Unknown error"
        try:
            error_details = http_err.response.json()
            error_content = error_details.get("error", {}).get("message", http_err.response.text)
        except json.JSONDecodeError: error_content = http_err.response.text
        print(f"HTTP error (model: {model_name}): {http_err} - Details: {error_content}")
        return f"Error: AI API request failed (HTTP {http_err.response.status_code}). Details: {error_content}"
    except httpx.TimeoutException:
        print(f"API request timed out for model {model_name} after {timeout_duration}s.")
        return "Error: The AI API request timed out. This can happen with very long report requests. Please try a more focused area or try again later."
    except httpx.RequestError as req_err:
        print(f"Request error (model: {model_name}): {req_err}")
        return f"Error: AI API request failed due to a network issue: {str(req_err)}"
    except Exception as e:
        print(f"Generic error in get_perplexity_response (model: {model_name}): {e.__class__.__name__} - {e}")
        import traceback; traceback.print_exc()
        return f"Error: An unexpected error occurred: {str(e)}"


def _build_single_document_prompt_from_structure(area_name: str) -> str:
    from datetime import datetime
    current_date_str = datetime.now().strftime("%B %Y")
    focus_points_map = _get_detailed_focus_points_for_prompt(area_name)

    # UPDATED prompt_start
    prompt_start = f"""**CRITICAL INSTRUCTION: YOUR ENTIRE RESPONSE MUST BE ONLY THE REPORT CONTENT. START *EXACTLY* WITH THE FOLLOWING TITLE AND DATE, THEN THE "Contents" HEADING. DO NOT ADD ANY OTHER TEXT BEFORE THIS.**
**If you have any internal planning, thoughts, or self-correction steps during generation, you MUST enclose them in <think>...</think> tags. These tags and their content will be programmatically removed and MUST NOT appear in the final report body.**

## Comprehensive Report on Healthcare in {area_name}: Diseases, Emerging Risks, and Government Schemes
{current_date_str}

## Contents
*(You will generate the list of sections here, like "1. Introduction", "  1.1. Subsection X", etc. DO NOT include page numbers in the Table of Contents. Ensure each main section from the guide below has an entry.)*

---
"""
    # UPDATED prompt_body_instructions
    prompt_body_instructions = f"""
**MAIN REPORT BODY INSTRUCTIONS:**
Following the Table of Contents (which you will generate based on the H2 and H3 headings below), proceed to generate the full report content.
The report MUST be AT LEAST **5000 WORDS** (or as extensively detailed as possible for '{area_name}').
Use ONLY certified and official sources of data. AIM TO INCLUDE SEVERAL RELEVANT CHARTS THROUGHOUT THE REPORT AS GUIDED.
**Remember to use <think>...</think> for any internal thought processes or meta-commentary that are not part of the report itself. These will be stripped out.**

**Overall Markdown Formatting:**
- Main sections MUST use H2 Markdown headings (e.g., `## 1. Introduction`).
- Subsections within main sections MUST use H3 Markdown headings (e.g., `### 1.1. Overview of {area_name}'s Demographics`).
- **FOR EACH SUBSECTION, provide THOROUGH and IN-DEPTH analysis, discussion, and detailed information. Do not be brief. Elaborate extensively, drawing on multiple data points and explaining their significance.**

**Detailed Content Guide for Each Section:**
"""

    for section_key, section_title_template in SECTION_STRUCTURE_GUIDE.items():
        actual_section_title = section_title_template.format(area_name=area_name)
        if section_key == "title_page" or section_key == "table_of_contents":
            continue
        prompt_body_instructions += f"\n## {actual_section_title}\n"
        if section_key in focus_points_map:
            for point in focus_points_map[section_key]:
                if point.strip().startswith("**Under a subsection titled"):
                    h3_match = re.search(r"`(### .*?)`", point)
                    if h3_match:
                        h3_title = h3_match.group(1)
                        prompt_body_instructions += f"{h3_title}\n"
                        instruction_for_h3 = point.split("`:**", 1)[-1].strip()
                        prompt_body_instructions += f"- {instruction_for_h3}\n"
                    else:
                        prompt_body_instructions += f"- {point}\n"
                else:
                    prompt_body_instructions += f"- {point}\n"
        else:
            prompt_body_instructions += f"- (Provide comprehensive information for this section: {actual_section_title})\n"

    # UPDATED prompt_end_rules
    prompt_end_rules = f"""
**General Content Style:**
- Provide EXTREMELY IN-DEPTH analysis, not just lists. Explain data significance. Aim for a total report length of AT LEAST 5000 WORDS.
- Integrate statistics smoothly and extensively.
- Use bullet points (`* item`) for lists where appropriate, but main content should be detailed prose.

**Tables:**
- Include data in Markdown tables where relevant. Caption *above* table: "Table X: Description for {area_name}."

**Charts and Graphs (Data Provision - INCLUDE PLENTY OF RELEVANT CHARTS):**
- Actively look for opportunities to include charts to visualize data, trends, and comparisons. The more relevant charts, the better.
- For EACH chart, provide data ON ITS OWN LINE, immediately after the paragraph discussing it:
    `CHART_DATA: TYPE=[bar|line|pie|doughnut] TITLE="Chart Title for {area_name}" LABELS=["L1","L2"] DATA=[V1,V2] SOURCE="(Source, Year)"`
    *(For multi-series charts, you can provide multiple data arrays, e.g., DATA_SERIES_1=[V1,V2] DATA_SERIES_2=[V3,V4] and adjust LABELS accordingly, but single series per CHART_DATA is simpler for now unless data naturally calls for comparison in one chart).*
- Chart data arrays (LABELS, DATA) should be concise (3-10 points).

**Citations:**
- ALL data/claims MUST be attributed in-text: `(Author/Organization, Year)`.

**Final Section - References:**
- The last H2 section of the report MUST be `## References`.
- List all cited sources alphabetically with full details.

**ABSOLUTELY NO TEXT, THOUGHTS, PLANNING, OR PREFATORY REMARKS BEFORE THE MAIN REPORT TITLE. YOUR RESPONSE IS ONLY THE REPORT CONTENT AS SPECIFIED. All internal thoughts or meta-commentary MUST be in <think>...</think> tags.**
"""
    full_prompt = prompt_start + prompt_body_instructions + prompt_end_rules
    return full_prompt

async def conduct_deep_research(area_name: str):
    print(f"Starting COMPREHENSIVE HEALTH ANALYSIS (Single Doc Prompt) for area: {area_name} using {RESEARCH_MODEL_NAME}")
    report_id = generate_report_id(area_name)

    report_data = {
        "report_id": report_id,
        "area_name": area_name,
        "full_report_markdown": "",
        "charts": [],
        "full_text_for_follow_up": ""
    }

    mega_prompt = _build_single_document_prompt_from_structure(area_name)

    estimated_tokens = len(mega_prompt) / 3.7 
    print(f"Structured Single Prompt Estimated length: ~{len(mega_prompt)} chars, ~{estimated_tokens:.0f} tokens.")

    full_report_markdown_content = await get_perplexity_response(
        prompt_content=mega_prompt,
        model_name=RESEARCH_MODEL_NAME,
        max_tokens=8192, # Sufficient for ~5000+ words
        temperature=0.3 
    )

    report_data["full_report_markdown"] = full_report_markdown_content
    report_data["full_text_for_follow_up"] = full_report_markdown_content # This will be the cleaned version

    if full_report_markdown_content.startswith("Error:"):
        print(f"Report generation failed for {area_name}. API Error: {full_report_markdown_content}")
        return report_data
    
    # Chart parsing logic remains the same, operating on the cleaned full_report_markdown_content
    chart_pattern_str = r'CHART_DATA:\s*TYPE=(?P<type>\w+)\s*TITLE="(?P<title>[^"]+)"\s*LABELS=(?P<labels>\[[^\]]*\])\s*DATA=(?P<data>\[[^\]]*\])(?:\s*SOURCE="(?P<source>[^"]+)")?'
    chart_matches = re.finditer(chart_pattern_str, full_report_markdown_content)
    temp_charts_list = []
    for match_idx_chart, chart_match_item in enumerate(chart_matches):
        try:
            chart_dict = chart_match_item.groupdict()
            chart_type = chart_dict['type'].lower()
            chart_title = re.sub(r'[^\w\s\-\(\)%]', '', chart_dict['title']).strip()
            labels_str = chart_dict['labels']
            data_str = chart_dict['data']
            chart_source = chart_dict.get('source')

            try: labels = json.loads(labels_str)
            except json.JSONDecodeError: labels = ast.literal_eval(labels_str)
            
            try: raw_data_points = json.loads(data_str)
            except json.JSONDecodeError: raw_data_points = ast.literal_eval(data_str)

            if not (isinstance(labels, list) and isinstance(raw_data_points, list) and len(labels) == len(raw_data_points) and len(labels) > 0):
                print(f"Chart data format/length mismatch for '{chart_title}' (Match {match_idx_chart}). Labels: {len(labels)}, Data: {len(raw_data_points)}. Skipping.")
                continue
            
            if len(labels) > 12: 
                print(f"Warning: Chart '{chart_title}' has {len(labels)} data points, truncating to 12 for display.")
                labels = labels[:12]
                raw_data_points = raw_data_points[:12]

            numeric_data_points = []
            valid_points = True
            for point_idx, point in enumerate(raw_data_points):
                try:
                    val_str = str(point).strip().replace('%', '')
                    cleaned_val_str = re.sub(r'[^\d\.\-eE]', '', val_str) if isinstance(val_str, str) else str(point)
                    if cleaned_val_str: numeric_data_points.append(float(cleaned_val_str))
                    elif isinstance(point, (int, float)): numeric_data_points.append(float(point))
                    else: raise ValueError(f"Non-convertible point: '{point}'")
                except (ValueError, TypeError) as e_conv:
                    print(f"Could not convert chart data point '{point}' for '{chart_title}'. Error: {e_conv}. Skipping chart.")
                    valid_points = False; break
            
            if valid_points and numeric_data_points:
                if len(labels) == len(numeric_data_points):
                    chart_dataset_label = chart_title 
                    if chart_source:
                        chart_dataset_label += f" (Source: {chart_source})"

                    temp_charts_list.append({
                        "type": chart_type, "title": chart_title, "labels": [str(l) for l in labels],
                        "datasets": [{"label": chart_dataset_label, "data": numeric_data_points}],
                        "source": chart_source
                    })
                    print(f"Successfully parsed chart: '{chart_title}' for {area_name}")
                else:
                    print(f"Data point conversion/truncation led to mismatch for chart '{chart_title}'. Skipping.")
            elif not numeric_data_points and valid_points:
                 print(f"Chart '{chart_title}' for {area_name} had no numeric data after parsing. Skipping.")
        except Exception as e_chart_parse:
            print(f"Error parsing CHART_DATA (Match {match_idx_chart}): {e_chart_parse}. Raw: {chart_match_item.group(0)}")
    
    report_data["charts"] = temp_charts_list
    print(f"Total charts parsed and ready for rendering: {len(report_data['charts'])}")
    
    print(f"Finished COMPREHENSIVE HEALTH ANALYSIS for area: {area_name}.")
    return report_data


async def answer_follow_up_question(question: str, report_context: str) -> str:
    system_prompt_content = (
        "You are a helpful AI assistant. The user is asking a follow-up question about a detailed health report they just reviewed. "
        "Base your answer ONLY on the information contained within the provided report context. "
        "If the answer isn't in the report, clearly state that the information is not available in the provided document. "
        "Do not use external knowledge."
    )
    
    user_prompt_content = (
        f"Here is the health report content:\n"
        f"--- BEGIN REPORT CONTEXT ---\n{report_context}\n--- END REPORT CONTEXT ---\n\n"
        f"My question is: {question}\n\n"
        f"Based on the report, what is the answer? If it's not mentioned, please say so."
    )
    
    print(f"Answering follow-up with {FOLLOW_UP_MODEL_NAME}: '{question[:100]}...'")
    
    # For follow-up, we don't need the <think> tag system, as it's for direct Q&A.
    # We can use the default system prompt for `get_perplexity_response` or a simpler one.
    # Reusing the more elaborate system prompt used for report generation is fine, but we can simplify it.
    return await get_perplexity_response(
        prompt_content=user_prompt_content,
        model_name=FOLLOW_UP_MODEL_NAME,
        system_prompt_content=system_prompt_content, # This is specific to the follow-up
        max_tokens=1024,
        temperature=0.3
    )