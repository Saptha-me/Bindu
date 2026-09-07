from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from ..llm import get_llm


class InterviewScore(BaseModel):
    fastapi: int = Field(..., description="Score for FastAPI skills out of 10")
    system_design: int = Field(..., description="Score for System Design out of 10")
    security: int = Field(..., description="Score for Security out of 10")
    scalability: int = Field(..., description="Score for Scalability out of 10")
    databases: int = Field(..., description="Score for Databases out of 10")
    error_handling: int = Field(..., description="Score for Error Handling out of 10")
    devops: int = Field(..., description="Score for DevOps out of 10")


class EvaluationAgent:
    """
    Evaluates candidate answers and generates structured interview scores.
    """

    def __init__(self):
        self.llm = get_llm()
        self.parser = PydanticOutputParser(pydantic_object=InterviewScore)

        self.prompt = PromptTemplate(
            template="""
You are a senior technical interviewer.

Evaluate the candidate answers below and score them from 1 to 10 in:

- fastapi
- system_design
- security
- scalability
- databases
- error_handling
- devops

Candidate Answers:
{answers}

{format_instructions}
""",
            input_variables=["answers"],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            },
        )

    def evaluate(self, answers: dict) -> dict:
        text = "\n".join(f"{k}: {v}" for k, v in answers.items())

        chain = self.prompt | self.llm | self.parser
        result: InterviewScore = chain.invoke({"answers": text})

        return result.dict()