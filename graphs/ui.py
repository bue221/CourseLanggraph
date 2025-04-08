from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import HumanMessage
from test_form import graph
from db_utils import (
    save_message,
    get_conversation_history,
    format_messages_for_context,
)

import chainlit as cl


@cl.on_message
async def on_message(msg: cl.Message):
    session_id = cl.context.session.id

    # Guardar el mensaje del usuario en la base de datos
    save_message(session_id, "human", msg.content)

    # Obtener historial de conversación para contexto (excluyendo el mensaje actual)
    history = get_conversation_history(session_id)

    # Remover el último mensaje (que acabamos de guardar) para evitar duplicados
    if history and len(history) > 0:
        history = history[:-1]

    context = format_messages_for_context(history) if history else ""

    # Añadir contexto al mensaje del usuario
    message_with_context = f"{context}Nueva pregunta: {msg.content}"

    # Configuración para el grafo
    config = {"configurable": {"thread_id": session_id}}
    cb = cl.LangchainCallbackHandler()
    final_answer = cl.Message(content="")

    for msg_response, metadata in graph.stream(
        {"messages": [HumanMessage(content=message_with_context)]},
        stream_mode="messages",
        config=RunnableConfig(callbacks=[cb], **config),
    ):
        if (
            msg_response.content
            and not isinstance(msg_response, HumanMessage)
            # and metadata["langgraph_node"] == "final"
        ):
            await final_answer.stream_token(msg_response.content)

    # Guardar la respuesta en la base de datos
    save_message(session_id, "ai", final_answer.content)

    await final_answer.send()
