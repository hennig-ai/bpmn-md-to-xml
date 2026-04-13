"""Core BPMN XML exporter - generates BPMN 2.0 XML files from process model data.

Supports pools (collaboration/participant) and lanes (laneSet/lane) in addition
to standard BPMN flow elements. Produces XML compatible with bpmn.io.
"""

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from basic_framework.proc_frame import log_msg, log_and_raise
from bpmn_lib.navigator import BPMNHierarchyNavigator, OutgoingSequenceFlowInfo
from element_type_mapping import resolve_xml_tag
from bpmn_auto_layout import (
    BpmnAutoLayout, PoolLayoutInfo, LaneLayoutInfo,
    BPMNDI_NS, DC_NS, DI_NS,
)

BPMN_NAMESPACE: str = "http://www.omg.org/spec/BPMN/20100524/MODEL"
XSI_NAMESPACE: str = "http://www.w3.org/2001/XMLSchema-instance"
TARGET_NAMESPACE: str = "http://bpmn.io/schema/bpmn"


class BpmnXmlExporter:
    """Exports BPMN process model data to BPMN 2.0 XML files."""

    def __init__(self, navigator: BPMNHierarchyNavigator) -> None:
        self._navigator: BPMNHierarchyNavigator = navigator
        self._auto_layout: BpmnAutoLayout = BpmnAutoLayout()
        ET.register_namespace("bpmn", BPMN_NAMESPACE)
        ET.register_namespace("xsi", XSI_NAMESPACE)
        ET.register_namespace("bpmndi", BPMNDI_NS)
        ET.register_namespace("dc", DC_NS)
        ET.register_namespace("di", DI_NS)

    def export(self, output_dir: Path) -> list[Path]:
        """Export all processes to BPMN XML files in the given directory.

        Args:
            output_dir: Directory where .bpmn files will be written.

        Returns:
            List of paths to the created files.
        """
        if not output_dir.is_dir():
            log_and_raise(FileNotFoundError(f"Output directory does not exist: {output_dir}"))

        written_files: list[Path] = []
        table = self._navigator.get_table("bpmn_process")
        iterator = table.create_iterator()
        while not iterator.is_empty():
            process_id: int = iterator.value("bpmn_process_id")
            process_name: str = iterator.value("name")
            is_executable: bool = iterator.value("is_executable")
            root: ET.Element = self._build_process_xml(process_id, process_name, is_executable)
            filename: str = f"{process_id}_{self._sanitize_name(process_name)}.bpmn"
            file_path: Path = output_dir / filename
            ET.indent(root)
            ET.ElementTree(root).write(str(file_path), encoding="UTF-8", xml_declaration=True)
            written_files.append(file_path)
            log_msg(f"Exported: {file_path}")
            iterator.pp()
        return written_files

    def _build_process_xml(
        self, process_id: int, process_name: str, is_executable: bool
    ) -> ET.Element:
        """Build the XML tree for a single BPMN process.

        Handles collaboration/participant if pools exist, and laneSet/lane
        if lanes are defined.

        Args:
            process_id: The numeric process ID.
            process_name: The human-readable process name.
            is_executable: Whether the process is executable.

        Returns:
            The root <bpmn:definitions> element.
        """
        root: ET.Element = ET.Element(f"{{{BPMN_NAMESPACE}}}definitions")
        root.set("id", f"Definitions_{process_id}")
        root.set("targetNamespace", TARGET_NAMESPACE)
        root.set("exporter", "process_this_bpmn_export")

        process_id_str: str = str(process_id)

        # Query pool/lane structure
        pool_data: tuple[str, str] | None = self._query_pool_for_process(process_id_str)

        pool_info: PoolLayoutInfo | None = None
        lane_infos: list[LaneLayoutInfo] | None = None

        if pool_data is not None:
            pool_element_id: str
            pool_name: str
            pool_element_id, pool_name = pool_data
            participant_xml_id: str = f"Participant_{pool_element_id}"

            collab: ET.Element = ET.SubElement(root, f"{{{BPMN_NAMESPACE}}}collaboration")
            collab.set("id", "Collaboration_1")
            participant: ET.Element = ET.SubElement(collab, f"{{{BPMN_NAMESPACE}}}participant")
            participant.set("id", participant_xml_id)
            participant.set("name", pool_name)
            participant.set("processRef", f"Process_{process_id}")

            pool_info = PoolLayoutInfo(xml_id=participant_xml_id, name=pool_name)
            lane_infos = self._query_lanes_for_pool(pool_element_id)

        # Process element
        process_elem: ET.Element = ET.SubElement(root, f"{{{BPMN_NAMESPACE}}}process")
        process_elem.set("id", f"Process_{process_id}")
        process_elem.set("name", process_name)
        process_elem.set("isExecutable", str(is_executable).lower())

        # Add laneSet if lanes exist
        if lane_infos is not None and len(lane_infos) > 0:
            lane_set: ET.Element = ET.SubElement(process_elem, f"{{{BPMN_NAMESPACE}}}laneSet")
            lane_set.set("id", f"LaneSet_{process_id}")
            for lane in lane_infos:
                lane_elem: ET.Element = ET.SubElement(lane_set, f"{{{BPMN_NAMESPACE}}}lane")
                lane_elem.set("id", lane.xml_id)
                lane_elem.set("name", lane.name)
                for elem_xml_id in lane.element_xml_ids:
                    flow_node_ref: ET.Element = ET.SubElement(
                        lane_elem, f"{{{BPMN_NAMESPACE}}}flowNodeRef"
                    )
                    flow_node_ref.text = elem_xml_id

        # First pass: collect flow metadata
        element_ids: list[str] = self._navigator.get_process_elements(process_id_str)
        flow_names: dict[str, str] = {}
        element_entries: list[tuple[str, str]] = []
        collected_flows: list[tuple[str, OutgoingSequenceFlowInfo]] = []
        default_flows: dict[str, str] = {}

        for element_id in element_ids:
            element_type: str = self._navigator.get_element_attribute(element_id, "element_type")

            if element_type == "sequence_flow":
                name = self._navigator.get_element_attribute(element_id, "name")
                if name is not None:
                    flow_names[str(element_id)] = str(name)
                continue

            if element_type in ("data_association", "pool", "lane"):
                continue

            element_entries.append((element_id, element_type))

            for flow_info in self._navigator.get_outgoing_sequence_flows(element_id):
                collected_flows.append((element_id, flow_info))
                if flow_info.is_default is True:
                    default_flows[element_id] = f"Flow_{flow_info.sequence_flow_id}"

        # Second pass: create XML elements
        for element_id, element_type in element_entries:
            elem: ET.Element = self._create_element_xml(element_id, element_type)

            if element_type == "gateway" and element_id in default_flows:
                elem.set("default", default_flows[element_id])

            process_elem.append(elem)

        # Sequence flows
        for source_element_id, flow_info in collected_flows:
            self._add_sequence_flow_xml(process_elem, source_element_id, flow_info, flow_names)

        # Auto-layout with pool/lane awareness
        self._auto_layout.generate_diagram(
            root, f"Process_{process_id}", pool_info, lane_infos,
        )

        return root

    def _query_pool_for_process(self, process_id: str) -> tuple[str, str] | None:
        """Find the pool for a given process.

        Args:
            process_id: The process ID to look up.

        Returns:
            Tuple of (pool_bpmn_element_id, pool_name) or None if no pool exists.
        """
        pool_table = self._navigator.get_table("pool")
        pool_iter = pool_table.create_iterator()
        while not pool_iter.is_empty():
            pool_process_id: str = str(pool_iter.value("bpmn_process_id"))
            if pool_process_id == process_id:
                pool_element_id: str = str(pool_iter.value("bpmn_element_id"))
                name = self._navigator.get_element_attribute(pool_element_id, "name")
                if name is None:
                    log_and_raise(ValueError(
                        f"Pool element {pool_element_id} has no name attribute"
                    ))
                return (pool_element_id, str(name))
            pool_iter.pp()
        return None

    def _query_lanes_for_pool(self, pool_element_id: str) -> list[LaneLayoutInfo]:
        """Query lanes and their element assignments for a given pool.

        Args:
            pool_element_id: The bpmn_element_id of the pool.

        Returns:
            List of LaneLayoutInfo with element assignments.
        """
        # Build lane_bpmn_id -> [element_bpmn_ids] from lane_element table
        lane_element_table = self._navigator.get_table("lane_element")
        le_iter = lane_element_table.create_iterator()
        lane_to_elements: dict[str, list[str]] = defaultdict(list)
        while not le_iter.is_empty():
            lane_bpmn_id: str = str(le_iter.value("lane_bpmn_element_id"))
            elem_bpmn_id: str = str(le_iter.value("bpmn_element_id"))
            lane_to_elements[lane_bpmn_id].append(elem_bpmn_id)
            le_iter.pp()

        # Get lanes belonging to this pool
        lane_table = self._navigator.get_table("lane")
        lane_iter = lane_table.create_iterator()
        lane_infos: list[LaneLayoutInfo] = []
        while not lane_iter.is_empty():
            if str(lane_iter.value("pool_id")) == pool_element_id:
                lane_bpmn_id = str(lane_iter.value("bpmn_element_id"))
                name = self._navigator.get_element_attribute(lane_bpmn_id, "name")
                if name is None:
                    log_and_raise(ValueError(
                        f"Lane element {lane_bpmn_id} has no name attribute"
                    ))
                element_bpmn_ids: list[str] = lane_to_elements[lane_bpmn_id]
                element_xml_ids: list[str] = [
                    f"Element_{eid}" for eid in element_bpmn_ids
                ]
                lane_infos.append(LaneLayoutInfo(
                    xml_id=f"Lane_{lane_bpmn_id}",
                    name=str(name),
                    element_xml_ids=element_xml_ids,
                ))
            lane_iter.pp()

        return lane_infos

    def _create_element_xml(self, element_id: str, element_type: str) -> ET.Element:
        """Create an XML element for a BPMN element.

        Handles subtype resolution, gateway direction, incoming/outgoing refs,
        multi-instance characteristics, and data associations.

        Args:
            element_id: The element's unique ID.
            element_type: The element type from the process model.

        Returns:
            The created XML element.
        """
        subtype: str | None = None
        if element_type == "event":
            subtype = self._navigator.get_element_attribute(element_id, "event_type")
        elif element_type == "gateway":
            subtype = self._navigator.get_element_attribute(element_id, "gateway_type")

        xml_tag: str = resolve_xml_tag(element_type, subtype)
        id_prefix: str = "DataObject_" if element_type == "data_object" else "Element_"
        elem: ET.Element = ET.Element(f"{{{BPMN_NAMESPACE}}}{xml_tag}")
        elem.set("id", f"{id_prefix}{element_id}")

        name: str | None = self._navigator.get_element_attribute(element_id, "name")

        # Gateway: only label decision gateways (diverging exclusive/inclusive/event-based).
        # Parallel gateways and all converging gateways carry no decision —
        # their symbol already communicates their purpose.
        if element_type == "gateway":
            direction = self._navigator.get_element_attribute(element_id, "gateway_direction")
            if direction is not None:
                elem.set("gatewayDirection", str(direction).capitalize())
            is_decision_gateway: bool = (
                subtype in ("exclusive", "inclusive", "event_based")
                and str(direction).lower() == "diverging"
            )
            if name is not None and is_decision_gateway:
                elem.set("name", name)
        elif name is not None:
            elem.set("name", name)

        for flow_info in self._navigator.get_incoming_sequence_flows(element_id):
            incoming: ET.Element = ET.SubElement(elem, f"{{{BPMN_NAMESPACE}}}incoming")
            incoming.text = f"Flow_{flow_info.sequence_flow_id}"

        for outgoing_info in self._navigator.get_outgoing_sequence_flows(element_id):
            outgoing: ET.Element = ET.SubElement(elem, f"{{{BPMN_NAMESPACE}}}outgoing")
            outgoing.text = f"Flow_{outgoing_info.sequence_flow_id}"

        if element_type in (
            "service_task", "user_task", "script_task", "business_rule_task",
            "call_activity", "subprocess",
        ):
            self._add_multi_instance_characteristics(elem, element_id)

        data_inputs: list[str] | None = self._navigator.get_data_inputs(element_id)
        if data_inputs is not None:
            for data_input_id in data_inputs:
                assoc: ET.Element = ET.SubElement(elem, f"{{{BPMN_NAMESPACE}}}dataInputAssociation")
                source: ET.Element = ET.SubElement(assoc, f"{{{BPMN_NAMESPACE}}}sourceRef")
                source.text = f"DataObject_{data_input_id}"

        data_outputs: list[str] | None = self._navigator.get_data_outputs(element_id)
        if data_outputs is not None:
            for data_output_id in data_outputs:
                assoc = ET.SubElement(elem, f"{{{BPMN_NAMESPACE}}}dataOutputAssociation")
                target: ET.Element = ET.SubElement(assoc, f"{{{BPMN_NAMESPACE}}}targetRef")
                target.text = f"DataObject_{data_output_id}"

        return elem

    def _add_multi_instance_characteristics(
        self, xml_element: ET.Element, element_id: str
    ) -> None:
        """Add multiInstanceLoopCharacteristics if the element is multi-instance.

        Args:
            xml_element: The parent XML element to add the characteristics to.
            element_id: The element's unique ID.
        """
        is_multi_instance_raw: str | bool | None = self._navigator.get_element_attribute(
            element_id, "is_multi_instance"
        )
        if is_multi_instance_raw is None or str(is_multi_instance_raw).lower() != "true":
            return

        loop_type: str = self._navigator.get_element_attribute(element_id, "loop_type")
        if loop_type == "multi_instance_parallel":
            is_sequential: str = "false"
        elif loop_type == "multi_instance_sequential":
            is_sequential = "true"
        else:
            log_and_raise(ValueError(f"Unknown loop_type: {loop_type} for element {element_id}"))

        ET.SubElement(
            xml_element, f"{{{BPMN_NAMESPACE}}}multiInstanceLoopCharacteristics"
        ).set("isSequential", is_sequential)

    def _add_sequence_flow_xml(
        self,
        process_element: ET.Element,
        source_element_id: str,
        flow_info: OutgoingSequenceFlowInfo,
        flow_names: dict[str, str],
    ) -> None:
        """Add a standalone <bpmn:sequenceFlow> element to the process.

        Args:
            process_element: The <bpmn:process> parent element.
            source_element_id: The source element's ID.
            flow_info: The outgoing sequence flow information.
            flow_names: Map of sequence_flow_id to flow name.
        """
        flow_elem: ET.Element = ET.SubElement(
            process_element, f"{{{BPMN_NAMESPACE}}}sequenceFlow"
        )
        flow_elem.set("id", f"Flow_{flow_info.sequence_flow_id}")
        flow_elem.set("sourceRef", f"Element_{source_element_id}")
        flow_elem.set("targetRef", f"Element_{flow_info.target_element_id}")

        # Only label conditional flows and default flows (BPMN best practice:
        # regular flows are self-explanatory, labels would just add clutter)
        has_condition: bool = flow_info.condition_expression is not None
        is_default: bool = flow_info.is_default is True
        if has_condition or is_default:
            sf_id_str: str = str(flow_info.sequence_flow_id)
            if sf_id_str in flow_names:
                flow_elem.set("name", flow_names[sf_id_str])

        if has_condition:
            condition: ET.Element = ET.SubElement(
                flow_elem, f"{{{BPMN_NAMESPACE}}}conditionExpression"
            )
            condition.set(f"{{{XSI_NAMESPACE}}}type", "bpmn:tFormalExpression")
            condition.text = flow_info.condition_expression

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a process name for use as a filename.

        Args:
            name: The original process name.

        Returns:
            A sanitized filename-safe string.
        """
        result: str = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        result = re.sub(r"_+", "_", result)
        result = result.strip("_")
        return result
