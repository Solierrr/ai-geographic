"""Consulta e apresenta a viabilidade solar sem extrapolar o payload."""

from langchain_core.messages import AIMessage

from src.core.travel.models import ResolvedPlace
from src.infra.external.google_registry.errors import (
    GoogleRegistryError,
    SolarCoverageUnavailableError,
)
from src.infra.external.google_registry.models import SolarViability
from src.infra.external.google_registry.solar import get_roof_viability
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def _number(value: float, language: str) -> str:
    formatted = f"{value:,.1f}"
    if language == "en":
        return formatted
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _solar_answer(data: SolarViability, language: str = "pt-BR") -> str:
    if language == "en":
        parts = [
            f"The provider's analysis, based on imagery from {data.imagery_date}, estimates ",
            f"{_number(data.usable_roof_area_m2, language)} m² of usable roof area, ",
            f"up to {data.max_panel_count} reference panels, and ",
            f"{_number(data.annual_sunshine_hours, language)} annual sunshine hours.",
        ]
    elif language == "es":
        parts = [
            f"El análisis del proveedor, basado en imágenes de {data.imagery_date}, estima ",
            f"{_number(data.usable_roof_area_m2, language)} m² de área útil de tejado, ",
            f"hasta {data.max_panel_count} paneles de referencia y ",
            f"{_number(data.annual_sunshine_hours, language)} horas anuales de sol.",
        ]
    else:
        parts = [
            f"A análise do provedor, baseada em imagem de {data.imagery_date}, estima ",
            f"{_number(data.usable_roof_area_m2, language)} m² de área aproveitável no telhado, ",
            f"até {data.max_panel_count} painéis de referência e ",
            f"{_number(data.annual_sunshine_hours, language)} horas anuais de incidência solar.",
        ]
    if data.roof_segments:
        segments_text = {
            "pt-BR": f" Foram identificados {len(data.roof_segments)} segmentos de telhado.",
            "en": f" The provider identified {len(data.roof_segments)} roof segments.",
            "es": f" El proveedor identificó {len(data.roof_segments)} segmentos de tejado.",
        }
        parts.append(segments_text[language])
    panel_details = []
    if data.panel_capacity_watts is not None:
        label = {"pt-BR": "potência", "en": "capacity", "es": "potencia"}[language]
        panel_details.append(
            f"{label} {_number(data.panel_capacity_watts, language)} W"
        )
    if data.panel_width_meters is not None and data.panel_height_meters is not None:
        panel_details.append(
            f"{_number(data.panel_width_meters, language)} × {_number(data.panel_height_meters, language)} m"
        )
    if panel_details:
        prefix = {
            "pt-BR": " O painel de referência possui ",
            "en": " The reference panel has ",
            "es": " El panel de referencia tiene ",
        }[language]
        parts.append(prefix + " / ".join(panel_details) + ".")
    if data.panel_configs:
        panel_word = {"pt-BR": "painéis", "en": "panels", "es": "paneles"}[language]
        yearly_unit = {"pt-BR": "kWh/ano DC", "en": "DC kWh/year", "es": "kWh/año DC"}[
            language
        ]
        configs = "; ".join(
            f"{item.panels_count} {panel_word}: {_number(item.yearly_energy_dc_kwh, language)} {yearly_unit}"
            for item in data.panel_configs[:3]
        )
        prefix = {
            "pt-BR": " Configurações candidatas informadas: ",
            "en": " Candidate configurations reported: ",
            "es": " Configuraciones candidatas informadas: ",
        }[language]
        parts.append(f"{prefix}{configs}.")
    carbon = _number(data.carbon_offset_factor_kg_mwh, language)
    parts.append(
        {
            "pt-BR": f" O fator de compensação informado é de {carbon} kg de CO₂ por MWh.",
            "en": f" The reported carbon offset factor is {carbon} kg of CO₂ per MWh.",
            "es": f" El factor de compensación informado es de {carbon} kg de CO₂ por MWh.",
        }[language]
    )
    parts.append(
        {
            "pt-BR": " Esses valores são estimativas do provedor e não substituem vistoria, dimensionamento ou projeto técnico de instalação.",
            "en": " These figures are provider estimates and do not replace an inspection, system sizing, or a final installation design.",
            "es": " Estas cifras son estimaciones del proveedor y no sustituyen una inspección, dimensionamiento o proyecto técnico de instalación.",
        }[language]
    )
    return "".join(parts)


async def solar_node(state: GraphState, config=None) -> dict:
    result = {"turn_agents": append_turn_agent(state, "solar")}
    language = state.get("trip_request", {}).get("response_language", "pt-BR")
    place = ResolvedPlace.model_validate(state["resolved_destination"])
    try:
        viability = await get_roof_viability(place.coordinate)
    except SolarCoverageUnavailableError:
        no_coverage = {
            "pt-BR": "Não há cobertura de dados solares para essa localização. Isso não significa que o imóvel seja inviável; apenas que o provedor não possui dados para analisá-lo.",
            "en": "Solar data coverage is unavailable for this location. This does not mean the property is unsuitable; the provider simply has no data to analyze it.",
            "es": "No hay cobertura de datos solares para esta ubicación. Esto no significa que el inmueble no sea apto; el proveedor simplemente no tiene datos para analizarlo.",
        }[language]
        return {
            **result,
            "flow_status": "respond",
            "provider_issue": "solar_coverage_unavailable",
            "messages": [AIMessage(content=no_coverage)],
        }
    except GoogleRegistryError as exc:
        unavailable = {
            "pt-BR": "A análise solar está temporariamente indisponível. Tente novamente em instantes.",
            "en": "The solar analysis is temporarily unavailable. Please try again shortly.",
            "es": "El análisis solar no está disponible temporalmente. Inténtalo de nuevo en unos instantes.",
        }[language]
        return {
            **result,
            "flow_status": "respond",
            "provider_issue": exc.kind,
            "messages": [AIMessage(content=unavailable)],
        }
    return {
        **result,
        "flow_status": "respond",
        "solar_result": viability.model_dump(mode="json"),
        "messages": [AIMessage(content=_solar_answer(viability, language))],
    }
