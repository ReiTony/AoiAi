import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from utils.sessions import ChatSession, get_chat_session
from utils.llm_client import generate_response
from utils.profession_template import (
    pilot_prompt,
    musician_prompt,
    athlete_prompt,
    scientist_prompt,
    businessman_prompt,
)

logger = logging.getLogger("profession_chat")
router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ProfessionChatRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = None


def profession_intent_prompt(user_message: str) -> str:
    return (
        "Classify the user's intent by selecting the correct profession based on their request.\n\n"
        "Possible categories:\n"
        "- pilot: anything about flying, planes, flight instructions\n"
        "- musician: music theory, instruments, performance, rhythm\n"
        "- athlete: workouts, training, sports, performance\n"
        "- scientist: experiments, labs, data, analysis, biology, chemistry\n"
        "- businessman: meetings, presentations, strategy, leadership, workplace\n\n"
        f"User Message: {user_message.strip()}\n"
        "Intent:"
    )


@router.post("/profession_chat")
async def profession_chat(
    chat_req: ProfessionChatRequest,
    request: Request,
    chat_session: ChatSession = Depends(get_chat_session),
):
    user_message = chat_req.query.strip()
    if not user_message:
        return JSONResponse(content={"error": "Message is required."}, status_code=422)

    try:
        history = await chat_session.get_history()
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        history = []

    # Step 1: Classify intent using LLM
    try:
        intent_query = profession_intent_prompt(user_message)
        intent_response = await generate_response(intent_query)
        intent = intent_response.strip().lower()
        logger.info(f"[Profession Intent] '{user_message}' → {intent}")
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")
        intent = "businessman"  # default fallback

    # Step 2: Route to correct prompt
    if intent == "pilot":
        prompt = pilot_prompt(user_message)
    elif intent == "musician":
        prompt = musician_prompt(user_message)
    elif intent == "athlete":
        prompt = athlete_prompt(user_message)
    elif intent == "scientist":
        prompt = scientist_prompt(user_message)
    else:
        prompt = businessman_prompt(user_message)

    logger.info(f"Prompt sent to LLM:\n{prompt}")

    # Step 3: Get AI Response
    try:
        ai_response = await generate_response(prompt)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        ai_response = "Sorry, I couldn't process your request right now."

    # Step 4: Save history
    try:
        await chat_session.add_message("user", user_message)
        await chat_session.add_message("assistant", ai_response)
    except Exception as e:
        logger.error(f"Failed to save messages: {e}")

    return JSONResponse(
        content={
            "answer": ai_response,
            "history": history
            + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": ai_response},
            ],
        },
        status_code=200,
    )
