import logging
import re
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from utils.sessions import ChatSession, get_chat_session
from utils.llm_client import generate_response
from utils.instructor_templates import (
    fitness_instructor_prompt,
    yoga_instructor_prompt,
    boxing_instructor_prompt,
    dance_instructor_prompt,
)

logger = logging.getLogger("instructor_chat")
router = APIRouter()

def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    return text

class ChatMessage(BaseModel):
    role: str
    content: str

class InstructorChatRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = None

def instructor_intent_prompt(query: str) -> str:
    return (
        "Classify the user's intent based on the type of physical instruction they're requesting.\n\n"
        "Possible categories:\n"
        "- fitness: general workouts, push-ups, jumping jacks, burpees\n"
        "- yoga: poses, flows, sun salutations, mindful stretches\n"
        "- boxing: punches, combos, stances, defense drills\n"
        "- dance: choreography, dance moves, rhythm exercises\n\n"
        f"User Message: {query.strip()}\n"
        "Intent:"
    )

@router.post("/query_router")
async def instructor_chat(
    chat_req: InstructorChatRequest,
    request: Request,
    chat_session: ChatSession = Depends(get_chat_session)
):
    user_message = chat_req.query.strip()
    if not user_message:
        logger.warning("No message provided.")
        return JSONResponse(content={"error": "Message is required."}, status_code=422)

    try:
        history = await chat_session.get_history()
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        history = []

    # Step 1: Use LLM to detect intent
    try:
        intent_query = instructor_intent_prompt(user_message)
        intent_response = await generate_response(intent_query)
        intent = intent_response.strip().lower()
        logger.info(f"[Intent Detection] '{user_message}' → Intent: {intent}")
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")
        intent = "fitness"  # fallback default

    # Step 2: Route to appropriate instructor prompt
    if intent == "yoga":
        prompt = yoga_instructor_prompt(user_message)
    elif intent == "boxing":
        prompt = boxing_instructor_prompt(user_message)
    elif intent == "dance":
        prompt = dance_instructor_prompt(user_message)
    else:
        prompt = fitness_instructor_prompt(user_message)

    logger.info(f"Prompt to LLM:\n{prompt}")

    # Step 3: Get LLM response
    try:
        ai_response = await generate_response(prompt)
        ai_response = strip_markdown(ai_response)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        ai_response = "Sorry, I couldn't process your request right now."

    # Step 4: Log chat history
    try:
        await chat_session.add_message("user", user_message)
        await chat_session.add_message("assistant", ai_response)
    except Exception as e:
        logger.error(f"Failed to save chat messages: {e}")

    return JSONResponse(content={
        "answer": ai_response,
        "history": history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ]
    }, status_code=200)
