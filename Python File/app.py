from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from groq import Groq
from datetime import datetime
import json
import os

load_dotenv()

app = Flask(__name__)

client = Groq(
    api_key = os.getenv("OPENAI_API_KEY")
)

def extract_context(question):
   date = datetime.now()
   current_period = f"{date.year}-{date.month}"
   with open("extraction_system_information.txt","r",encoding="utf-8") as file:
    sys_info = file.read()

   prompt = f"""
    Current payroll period:
    {current_period}

    Employee question:
    {question}

    Determine:
    1. The intent
    2. The required payroll period
    3. The required HR data domains
    
    Return ONLY a valid JSON object. Do not include markdown code block syntax (like ```json) or any extra conversational filler text.
    Required Output Structure:
    {{
    "intent": "string",
    "periods": [
    {{
        "period": "YYYY-MM",
        "role": "CURRENT | COMPARISON | REQUESTED"
    }}
    ],
    "requiredData": [
    "EMPLOYEE",
    "PAYROLL",
    "LEAVE",
    "ATTENDANCE"
    ]
    }}
    """
   return prompt, sys_info

def get_response(data):
    with open("analysis_system_information.txt","r",encoding="utf-8") as file:
        sys_info = file.read()

    prompt = f"""

    Analyze the following SAP HR ticket.

    The JSON contains:
    - Employee information
    - Ticket/question
    - Context identified by the first AI step
    - Payroll data
    - Leave data
    - Attendance data

    Use the SAP data as the source of truth.
    SAP HR JSON: {json.dumps(data, indent=2)}

    Provide the final answer to the employee's question.
    Return ONLY a valid JSON object. Do not include markdown code block syntax (like ```json) or any extra conversational filler text.
    Required Output Structure:
    {{
    "intent": "string",
    "analysis": "string"
    }}
    """
    
    return prompt, sys_info

@app.route("/analyze-ticket", methods=["POST"])
def analyze_ticket():
    data = request.get_json()
    
    employee_id = data.get("employee_id")
    question = data.get("question")
    type = data.get("analyze_type")

    if type == 'extract':
        prompt, sys_info = extract_context(question)

    else:
        prompt, sys_info = get_response(data)

    # if not ticket_text:
    #     return jsonify({"error": "No ticket text provided"}), 400

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",

        messages=[
            {"role": "system", "content": sys_info},
            {"role": "user", "content": prompt}
        ]
    )

    # analysis_result = response.output[0].content[0].text
    ai_text = response.choices[0].message.content.strip()

    try:
        context_json = json.loads(ai_text)
    except json.JSONDecodeError:
        return jsonify({
            "error":"LLM returned invalid json",
            "raw_response": ai_text
        }), 500

    # return jsonify({
    #     "employee_id": employee_id,
    #     "question": question,
    #     "analysis_result": response.choices[0].message.content
    # })
    return jsonify(context_json)

if __name__ == "__main__":
    cf_port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=cf_port)
