# crew_agent.py
from crewai import Crew, Task, Agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

crew_agent = Agent(
    role="Travel Planner",
    goal="Generate an HTML-based multi-day travel itinerary",
    backstory="You are a helpful AI travel assistant who plans perfect trips based on structured data.",
    verbose=True,
    llm=llm
)

def run_crew_with_data(context_data: dict) -> str:
    task = Task(
        description="Generate a multi-day itinerary in HTML format from structured travel data.",
        expected_output="Return a complete HTML string that includes sections for each day, showing hotels, tours, and attractions.",
        agent=crew_agent,
        context=[context_data]
    )

    crew = Crew(
        agents=[crew_agent],
        tasks=[task],
        verbose=True
    )

    result = crew.kickoff()
    return result
