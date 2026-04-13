"""Element type mapping from MD-based types to BPMN 2.0 XML tag names."""

from basic_framework.proc_frame import log_and_raise


ELEMENT_TYPE_MAPPING: dict[str, str] = {
    "service_task": "serviceTask",
    "user_task": "userTask",
    "script_task": "scriptTask",
    "business_rule_task": "businessRuleTask",
    "call_activity": "callActivity",
    "subprocess": "subProcess",
    "data_object": "dataObject",
    "text_annotation": "textAnnotation",
}

EVENT_TYPE_MAPPING: dict[str, str] = {
    "start": "startEvent",
    "end": "endEvent",
    "intermediate_catch": "intermediateCatchEvent",
    "intermediate_throw": "intermediateThrowEvent",
    "boundary": "boundaryEvent",
}

GATEWAY_TYPE_MAPPING: dict[str, str] = {
    "exclusive": "exclusiveGateway",
    "parallel": "parallelGateway",
    "inclusive": "inclusiveGateway",
    "event_based": "eventBasedGateway",
    "complex": "complexGateway",
}


def resolve_xml_tag(element_type: str, subtype: str | None) -> str:
    """Resolve an MD element type (and optional subtype) to its BPMN 2.0 XML tag name.

    Args:
        element_type: The element type from the MD process model.
        subtype: The subtype for events and gateways (e.g. "start", "exclusive").

    Returns:
        The BPMN 2.0 XML tag name.
    """
    if element_type == "event":
        if subtype is None:
            log_and_raise(ValueError(f"subtype is required for element_type 'event'"))
        if subtype not in EVENT_TYPE_MAPPING:
            log_and_raise(ValueError(
                f"Unknown event subtype '{subtype}'. "
                f"Valid subtypes: {list(EVENT_TYPE_MAPPING.keys())}"
            ))
        return EVENT_TYPE_MAPPING[subtype]

    if element_type == "gateway":
        if subtype is None:
            log_and_raise(ValueError(f"subtype is required for element_type 'gateway'"))
        if subtype not in GATEWAY_TYPE_MAPPING:
            log_and_raise(ValueError(
                f"Unknown gateway subtype '{subtype}'. "
                f"Valid subtypes: {list(GATEWAY_TYPE_MAPPING.keys())}"
            ))
        return GATEWAY_TYPE_MAPPING[subtype]

    if element_type not in ELEMENT_TYPE_MAPPING:
        log_and_raise(ValueError(
            f"Unknown element_type '{element_type}'. "
            f"Valid types: {list(ELEMENT_TYPE_MAPPING.keys())}"
        ))
    return ELEMENT_TYPE_MAPPING[element_type]
