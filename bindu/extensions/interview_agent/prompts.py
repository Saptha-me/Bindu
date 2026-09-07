# prompts.py

QUESTION_PROMPT = """
You are a senior technical interviewer.

Candidate Resume:
{resume}

Target Role:
{role}

Previous Questions:
{previous_questions}

Previous Answers:
{previous_answers}

Difficulty Level:
{difficulty}

Generate ONE high-quality technical interview question.
Rules:
- Must be role relevant
- Progressive difficulty
- Real-world scenario based
- No trivial questions

Return only the question text.
"""

EVALUATION_PROMPT = """
You are a senior interviewer evaluating candidate responses.

Question:
{question}

Candidate Answer:
{answer}

Evaluate based on:
- Technical correctness (0-10)
- Clarity (0-10)
- Depth (0-10)

Return valid JSON only:

{{
  "correctness": <int>,
  "clarity": <int>,
  "depth": <int>,
  "feedback": "<brief improvement feedback>"
}}
"""

FINAL_FEEDBACK_PROMPT = """
You are a senior hiring manager.

Full Interview Log:
{history}

Generate:
1. Overall score (0-100)
2. Strengths
3. Weaknesses
4. Learning roadmap
5. Hiring recommendation

Make it professional, structured, and actionable.
"""