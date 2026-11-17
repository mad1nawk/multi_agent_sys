import time
import chainlit as cl
from langchain_core.messages import HumanMessage
from src.observability import init_tracing, logger, trigger_alert

init_tracing("socrates-study-assistant")

from src.graph import app_graph


@cl.on_chat_start
async def on_chat_start():
    thread_id = cl.user_session.get("id")
    cl.user_session.set("thread_id", thread_id)
    logger.info(f"New chat session started: {thread_id}")
    await cl.Message(
        content="**Assistant** is ready!\nAsk me a math problem, theoretical concept, or self-test quiz."
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 12}

    msg = cl.Message(content="*Routing, solving, and verifying...*")
    await msg.send()

    t0 = time.perf_counter()
    run_graph = cl.make_async(app_graph.invoke)
    result = await run_graph(
        {
            "messages": [HumanMessage(content=message.content)],
            "user_id": "student_01",
        },
        config=config,
    )
    dt = time.perf_counter() - t0

    if dt > 240:
        trigger_alert("HIGH_LATENCY", f"Query took {dt:.1f}s (route={result.get('route')})")

    final_text = result.get("draft") or result["messages"][-1].content
    msg.content = final_text
    await msg.update()
