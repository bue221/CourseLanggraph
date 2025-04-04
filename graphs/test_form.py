from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Optional, List
from typing_extensions import TypedDict
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, AIMessage, ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition, InjectedState
from langgraph.types import Command

load_dotenv()


class FuelType(str, Enum):
    GASOLINE = "gasolina"
    DIESEL = "diesel"
    ELECTRIC = "eléctrico"
    HYBRID = "híbrido"
    GAS = "gas"


class TransmissionType(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automática"
    SEMI_AUTOMATIC = "semi-automática"


class MotorCycle(BaseModel):
    brand: Optional[str] = Field(None, description="Marca de la motocicleta")
    model: Optional[str] = Field(None, description="Modelo de la motocicleta")
    year: Optional[int] = Field(
        None, description="Año de fabricación (entre 1900 y el año actual)"
    )
    color: Optional[str] = Field(None, description="Color de la motocicleta")
    plate: Optional[str] = Field(
        None, description="Placa de la motocicleta (formato: XXX-000)"
    )
    engine_number: Optional[str] = Field(None, description="Número de motor")
    chassis_number: Optional[str] = Field(None, description="Número de chasis")
    type: Optional[str] = Field(
        None, description="Tipo de motocicleta (deportiva, crucero, etc.)"
    )
    type_of_use: Optional[str] = Field(
        None, description="Tipo de uso (personal, comercial, etc.)"
    )
    type_of_fuel: Optional[FuelType] = Field(None, description="Tipo de combustible")
    type_of_transmission: Optional[TransmissionType] = Field(
        None, description="Tipo de transmisión"
    )
    type_of_drive: Optional[str] = Field(None, description="Tipo de tracción")

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        if v is not None:
            import datetime

            current_year = datetime.datetime.now().year
            if v < 1900 or v > current_year:
                raise ValueError(f"El año debe estar entre 1900 y {current_year}")
        return v

    @field_validator("plate")
    @classmethod
    def validate_plate(cls, v):
        if v is not None:
            import re

            if not re.match(r"^[A-Z]{3}-\d{3}$", v):
                raise ValueError("La placa debe tener el formato XXX-000")
        return v


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    wa_number: Optional[str] = None
    form: Optional[MotorCycle] = None


@tool
def save_data_in_db(
    tool_call_id: Annotated[str, InjectedToolCallId],
    form: Annotated[MotorCycle, InjectedState("form")],
):
    """Guarda los datos en la base de datos una vez que el formulario esté completo.

    Args:
        tool_call_id: El ID del comando de la herramienta.
        form: El formulario actual.

    Returns:
        El estado actualizado del formulario.
    """
    print("Guardando en BD:", form.model_dump())
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="Datos guardados en la base de datos",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


@tool
def update_state(
    tool_call_id: Annotated[str, InjectedToolCallId],
    data: MotorCycle,
    form: Annotated[MotorCycle, InjectedState("form")],
):
    """Actualiza el estado del formulario usando el formulario actual y los datos proporcionados.

    Args:
        tool_call_id: El ID del comando de la herramienta.
        data: Los datos proporcionados por el usuario.
        form: El formulario actual.

    Returns:
        El estado actualizado del formulario.
    """
    # Obtener el formulario actual o crear uno nuevo si no existe
    current_form = form or MotorCycle.model_construct()

    # Convertir current_form a diccionario si es un objeto MotorCycle
    if isinstance(current_form, MotorCycle):
        current_form_dict = current_form.model_dump()
    else:
        current_form_dict = {}

    # Obtener solo los campos proporcionados con valores no nulos
    data_dict = data.model_dump()
    non_none_data = {k: v for k, v in data_dict.items() if v is not None}

    # Actualizar solo los campos proporcionados que no son None
    updated_form_dict = {**current_form_dict, **non_none_data}

    # Crear un nuevo objeto MotorCycle con los datos actualizados
    try:
        updated_form = MotorCycle.model_validate(updated_form_dict)
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Error de validación: {str(e)}",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    return Command(
        # this is the state update
        update={
            "form": updated_form,
            "messages": [
                ToolMessage(
                    content="Formulario actualizado correctamente",
                    tool_call_id=tool_call_id,
                )
            ],
        }
        # this is a replacement for an edge
    )


tools = [save_data_in_db, update_state]
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)


def welcome_node(state: State):
    if state.get("form") is None:
        state["form"] = MotorCycle()

    return state


def get_field_description(field_name):
    """Obtiene la descripción de un campo del modelo MotorCycle."""
    field_info = MotorCycle.model_fields.get(field_name)
    if field_info and field_info.description:
        return field_info.description
    return field_name


def get_field_options(field_name):
    """Obtiene las opciones disponibles para campos tipo Enum."""
    if field_name == "type_of_fuel":
        return [f"{e.value}" for e in FuelType]
    elif field_name == "type_of_transmission":
        return [f"{e.value}" for e in TransmissionType]
    return None


def assistant_form(state: State):
    if state.get("form") is None:
        state["form"] = MotorCycle()

    # Obtener el estado actual del formulario
    current_form = state.get("form", None)

    # Crear un mensaje con el estado actual
    form_status = ""
    if current_form:
        # Convertir el formulario a diccionario si es un objeto MotorCycle
        if isinstance(current_form, MotorCycle):
            form_dict = current_form.model_dump()
        else:
            form_dict = current_form

        # Mostrar campos completados y faltantes
        completed_fields = []
        missing_fields = []

        all_fields = [
            "brand",
            "model",
            "year",
            "color",
            "plate",
            "engine_number",
            "chassis_number",
            "type",
            "type_of_use",
            "type_of_fuel",
            "type_of_transmission",
            "type_of_drive",
        ]

        for field in all_fields:
            field_desc = get_field_description(field)
            if field in form_dict and form_dict[field]:
                completed_fields.append(f"- {field_desc}: {form_dict[field]}")
            else:
                options = get_field_options(field)
                field_info = f"{field_desc}"
                if options:
                    field_info += f" (opciones: {', '.join(options)})"
                missing_fields.append(f"- {field_info}")

        form_status = (
            "Datos ya proporcionados:\n" + "\n".join(completed_fields) + "\n\n"
        )

        if missing_fields:
            form_status += (
                "Datos que faltan por proporcionar:\n"
                + "\n".join(missing_fields)
                + "\n\n"
            )
        else:
            form_status += "¡Todos los datos han sido proporcionados!\n\n"
    else:
        form_status = "No se ha proporcionado ningún dato todavía.\n\n"

    prompt = f"""
    Actúa como un asistente de registro de motocicletas amigable y eficiente. Tu objetivo es recopilar todos los datos necesarios para el registro completo de una motocicleta de manera conversacional.

    Estado actual del formulario:
    {form_status}
    
    Instrucciones específicas:
    1. Pregunta al usuario por los datos faltantes, entre 1-2 a la vez, manteniendo un tono conversacional.
    2. Para campos con valores específicos como type_of_fuel y type_of_transmission, indica las opciones disponibles.
    3. Valida los datos mientras los recopilas:
       - El año debe estar entre 1900 y el año actual
       - La placa debe tener el formato XXX-000 (tres letras, guion, tres números)
    4. Si el usuario proporciona información inválida, explica amablemente el formato correcto.
    5. No solicites datos que ya hayan sido proporcionados.
    6. Una vez completado el formulario, confirma todos los datos con el usuario y utiliza save_data_in_db.
    
    Para actualizar el formulario con la información del usuario, usa la herramienta update_state con un objeto MotorCycle que contenga solo los campos nuevos mencionados por el usuario.
    
    Recuerda no mencionar explícitamente los nombres técnicos de los campos en la conversación con el usuario, usa términos más amigables y naturales.
    """
    response = llm_with_tools.invoke(state["messages"] + [AIMessage(content=prompt)])
    return {"messages": [response]}


# Construcción del grafo
canvas = StateGraph(State)

canvas.add_node("welcome", welcome_node)
canvas.add_node("assistant_form", assistant_form)
canvas.add_node("tools_assistant", ToolNode(tools))

canvas.add_edge(START, "welcome")
canvas.add_edge("welcome", "assistant_form")
canvas.add_conditional_edges(
    "assistant_form",
    tools_condition,
    {
        "tools": "tools_assistant",
        END: END,
    },
)
canvas.add_edge("tools_assistant", "assistant_form")
canvas.add_edge("assistant_form", END)

graph = canvas.compile()


# Test
def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)
