# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
from pathlib import Path
from typing import Dict, Any

import requests
from dotenv import load_dotenv
from google.adk.agents import Agent
import google.auth.transport.requests
import google.oauth2.id_token

# Load environment variables from .env file in root directory
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)


class GemmaClient:
    """Client for interacting with the deployed Gemma model using direct HTTP requests."""

    def __init__(self, gemma_url: str):
        self.gemma_url = gemma_url.rstrip('/')
        self.model_name = "gemma3:4b"
        
        # Get authentication headers for Cloud Run service-to-service calls
        self.auth_headers = self._get_auth_headers()

        print("auth headers", self.auth_headers)

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Cloud Run service-to-service calls."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "hackathon-agent/1.0"
        }
        
        # Try to get identity token for authenticated requests
        try:
            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, self.gemma_url)
            headers["Authorization"] = f"Bearer {id_token}"
            print(f"Added Authorization header with identity token")
        except Exception as e:
            print(f"Warning: Could not get identity token: {e}")
            # If authentication fails, proceed without auth header (for local testing)
            pass
            
        return headers

    def query_gemma(self, prompt: str, temperature: float = 0.7) -> str:
        """Query the deployed Gemma model using direct HTTP requests."""
        try:
            print("gemma url", self.gemma_url)
            print("using model", self.model_name)
            
            # Prepare the request payload to match the working curl format
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # Make the HTTP request to the correct Gemma endpoint
            endpoint_url = f"{self.gemma_url}/v1beta/models/{self.model_name}:generateContent"
            response = requests.post(
                endpoint_url,
                headers=self.auth_headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            
            # Parse the response
            response_data = response.json()
            
            # Extract text from response (adjust based on actual Gemma API response format)
            if 'candidates' in response_data and response_data['candidates']:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if parts and 'text' in parts[0]:
                        return parts[0]['text']
            elif 'text' in response_data:
                return response_data['text']
            elif 'response' in response_data:
                return response_data['response']
            
            return "No response from model"
            
        except requests.exceptions.RequestException as e:
            return f"HTTP request error: {str(e)}"
        except json.JSONDecodeError as e:
            return f"JSON decode error: {str(e)}"
        except Exception as e:
            return f"Error querying Gemma: {str(e)}"


# Global Gemma client instance
gemma_client = None


def get_gemma_client() -> GemmaClient:
    """Get or create the Gemma client instance."""
    global gemma_client
    if gemma_client is None:
        gemma_url = os.getenv("GEMMA_URL")
        
        if not gemma_url:
            raise ValueError("GEMMA_URL environment variable is required")
            
        gemma_client = GemmaClient(gemma_url)
    return gemma_client


def ask_gemma(question: str, context: str) -> Dict[str, Any]:
    """Ask a question to the deployed Gemma model.

    Args:
        question (str): The question to ask
        context (str): Optional context to provide with the question

    Returns:
        Dict[str, Any]: Response from Gemma with status information
    """
    try:
        client = get_gemma_client()
        
        # Build the prompt
        if context:
            prompt = f"Context: {context}\n\nQuestion: {question}\n\nPlease provide a helpful and informative answer."
        else:
            prompt = f"Question: {question}\n\nPlease provide a helpful and informative answer."
        
        response = client.query_gemma(prompt, temperature=0.7)
        
        return {
            "status": "success",
            "question": question,
            "answer": response,
            "context_provided": bool(context)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to query Gemma: {str(e)}",
            "question": question
        }


def brainstorm_ideas(topic: str, num_ideas: int) -> Dict[str, Any]:   
    try:
        client = get_gemma_client()
        
        prompt = f"""You are helping a human founder explore early product directions I mentioned in {topic}. Right now, your job is to gather raw input: ideas, rants, screenshots , voice notes, or random thoughts.

        Your role is to:
        - Listen without judgment
        - Highlight possible emotional patterns or tensions
        - Push your co-founders, i.e. me, to think further and deeper

        Do not try to categorize or organize yet. Be light, curious, and supportive. Inspire each other so we can understand better about the current market gaps and potential solutions.

        For the idea, provide:
        1. A clear title
        2. A brief description
        3. Why it would be useful or interesting

        Format your response as a numbered list with clear structure."""
        
        response = client.query_gemma(prompt, temperature=0.8)
        
        return {
            "status": "success",
            "topic": topic,
            "response": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to brainstorm ideas: {str(e)}",
            "topic": topic
        }


def summarize_brainstormideas(topic: str, level: str) -> Dict[str, Any]:
    try:
        client = get_gemma_client()       

        prompt = f"""
        You are a pattern-sensing AI.

        Your job is to summarize the discussion points from the brainstorm session about {topic} into thematic clusters.

        Each theme should have:
        - A short, evocative name (like a startup pitch or TikTok trend)
        - A 1–2 sentence summary of the emotional or behavioral tension
        - A list of linked fragments (quotes or paraphrased inputs)

        Do not suggest product ideas or hypotheses yet.

        Format your response as
       
        **Theme: [Title]**  
        > [Theme summary]  
        Linked items:
        - "Quote A"
        - "Fragment B"

        """
        
        response = client.query_gemma(prompt, temperature=0.6)
        
        return {
            "status": "success",
            "topic": topic,
            "response": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to explain concept: {str(e)}",
            "concept": topic
        }


def shape_hypothesis(topic: str, level: str) -> Dict[str, Any]:
    try:
        client = get_gemma_client()       

        prompt = f"""
        You are a product strategist AI.

        Convert themes to potential product directions. Your goal is to turn this insight into both creative ideas and testable hypotheses.

        Output format:
        ---
        ** Theme: [Title]**  
        > [Short summary of the user tension]

        Ideas:
        - [Product or service idea]
        - [Variation or angle]
        - [Stretch or adjacent take]

        Hypotheses:
        - [Short, testable assumption about user behavior or belief]
        - [Another assumption]
        - [Optional "What if…"]

        """
        
        response = client.query_gemma(prompt, temperature=0.6)
        
        return {
            "status": "success",
            "topic": topic,
            "response": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to explain concept: {str(e)}",
            "concept": topic
        }

def generate_survey(topic: str, level: str) -> Dict[str, Any]:
    try:
        client = get_gemma_client()       

        prompt = f"""
        Input: a list of hypothesis clusters with optional notes.
        Your task is to generate a structured set of user survey questions designed to test each hypothesis thoughtfully and empathetically.

        For each hypothesis:
        1. Include a short intro sentence to explain the context (optional, if needed).
        2. Write 2–3 well-crafted survey questions:
        - Use at least one Likert scale (e.g. 1–5 agreement) or multiple choice format
        - Use language that matches the target user (e.g. teens, Gen Z, parents)
        - Tone should be empathetic, relatable, and non-leading — avoid loaded or judgmental wording
        - Questions should progress from general → specific → emotional/insightful
        - Use conditional follow-ups if relevant (e.g. “If Q2 = strongly agree, then ask Q3: Why?”)

        The overall survey structure must include:
        - A Warm-Up Section at the beginning to understand user context and profile (age, lifestyle, habits)
        - A Section per Hypothesis, each testing one idea cluster with 2–3 questions
        - An optional Closing Section to capture future interest or open ideas

        Your output format:
        - Use Markdown with section headers for each part of the survey
        - Explicitly show any conditional logic using indentation or inline logic tags  
        e.g. `If Q2 = "Yes", then ask Q3`

        Your goal is to help the human founder validate the riskiest assumptions, surface strong signals, and inspire deeper product thinking. Keep total question count manageable (aim for ~12–15 questions total)
        """
        
        response = client.query_gemma(prompt, temperature=0.6)
        
        return {
            "status": "success",
            "topic": topic,
            "response": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to explain concept: {str(e)}",
            "concept": topic
        }

# Create the ADK agent
root_agent = Agent(
    name="hackathon_agent",
    model="gemini-2.5-flash",
    instruction="""
        You are a helpful AI assistant. 

        You can help participants by:
        1. Brainstorming through scattered information, asking questions, and throwing sparks to push the idea forward
        2. Summarizing brainstorm discussion points into thematic clusters, each backed by original user quotes or fragments.
        3. Shaping hypothesis from summarized brainstorm results
        4. Generating a survey to validate the hypothesis

        You have access to a deployed Gemma model through your tools. When users ask questions or request help:

        - Use ask_gemma for general questions - extract and show the "answer" field from the response
        - Use brainstorm_ideas for brainstorming the topic - extract and show the "response" field from the response  
        - Use summarize_brainstormideas for summarizing brainstorm discussion - extract and show the "response" field from the response
        - Use shape_hypothesis for Shaping hypothesis from summarized brainstorm results - extract and show the "response" field from the response
        - Use generate_survey for Generating a survey to validate the hypothesis - extract and show the "response" field from the response

        IMPORTANT: Always extract the actual content from the tool responses and present it directly to the user. Don't just mention that you called a tool - show the user the actual answer, code, ideas, or explanation that was generated.

        If a tool returns an error status, explain what went wrong and try to help in other ways.

        Your tools connect to a deployed Gemma model, so you can provide rich, detailed responses powered by that model while maintaining a conversational interface.""",
    tools=[ask_gemma, brainstorm_ideas,summarize_brainstormideas, shape_hypothesis, generate_survey],
)
