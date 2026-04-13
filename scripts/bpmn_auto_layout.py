"""Auto-layout for BPMN diagrams with pool/lane support.

Computes element positions and generates BPMNShape/BPMNEdge diagram interchange
elements. Supports both flat processes and processes with pools and lanes.

Uses center coordinates (cx, cy) internally and converts to top-left (x, y)
for dc:Bounds output.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from dataclasses import dataclass, field

BPMN_NS: str = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS: str = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS: str = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS: str = "http://www.omg.org/spec/DD/20100524/DI"

# Element dimensions
TASK_W: int = 120
TASK_H: int = 80
GATEWAY_SIZE: int = 50
EVENT_SIZE: int = 36

# Spacing between element centers
H_SPACING: int = 190
V_SPACING: int = 120

# Simple layout (no pools/lanes)
SIMPLE_START_X: int = 100
SIMPLE_CENTER_Y: float = 250.0

# Pool / Lane geometry
POOL_HEADER_W: int = 30
LANE_HEADER_W: int = 30
POOL_MARGIN_X: int = 50
POOL_MARGIN_Y: int = 50
LANE_PAD_Y: int = 50
ELEMENT_PAD_X: int = 60
MIN_LANE_H: int = 150

# Edge routing
BACK_EDGE_MARGIN: int = 60
VERTICAL_OFFSET_THRESHOLD: int = 30

EVENT_TAGS: frozenset[str] = frozenset({
    "startEvent", "endEvent", "intermediateThrowEvent",
    "intermediateCatchEvent", "boundaryEvent",
})
GATEWAY_TAGS: frozenset[str] = frozenset({
    "exclusiveGateway", "parallelGateway", "inclusiveGateway",
    "eventBasedGateway", "complexGateway",
})

# Tags to skip during element parsing (not layout-relevant)
SKIP_TAGS: frozenset[str] = frozenset({"dataObject", "laneSet"})


@dataclass
class PoolLayoutInfo:
    """Pool information needed for diagram layout."""

    xml_id: str
    name: str


@dataclass
class LaneLayoutInfo:
    """Lane information needed for diagram layout."""

    xml_id: str
    name: str
    element_xml_ids: list[str] = field(default_factory=list)


class BpmnAutoLayout:
    """Computes layout positions and generates BPMN DI elements for a process.

    Supports both flat processes (no pools/lanes) and processes with
    pool and lane structures. Uses a BFS-based layered layout algorithm
    with left-to-right flow direction.
    """

    def generate_diagram(
        self,
        root: ET.Element,
        process_id: str,
        pool_info: PoolLayoutInfo | None = None,
        lane_infos: list[LaneLayoutInfo] | None = None,
    ) -> None:
        """Add a BPMNDiagram element with auto-layout to the definitions root.

        Args:
            root: The <bpmn:definitions> root element.
            process_id: The id attribute of the <bpmn:process> element.
            pool_info: Pool information if the process has a pool.
            lane_infos: Lane information if the process has lanes.
        """
        process_elem: ET.Element | None = root.find(f"{{{BPMN_NS}}}process")
        if process_elem is None:
            return

        elements: dict[str, dict[str, str | int]] = {}
        flows: list[dict[str, str]] = []

        for child in process_elem:
            tag: str = child.tag.replace(f"{{{BPMN_NS}}}", "")
            elem_id: str | None = child.get("id")
            if elem_id is None:
                continue

            if tag == "sequenceFlow":
                src: str | None = child.get("sourceRef")
                tgt: str | None = child.get("targetRef")
                if src is not None and tgt is not None:
                    name_attr: str | None = child.get("name")
                    flow_name: str = name_attr if name_attr is not None else ""
                    flows.append({
                        "id": elem_id, "source": src, "target": tgt, "name": flow_name,
                    })
                continue

            if tag in SKIP_TAGS:
                continue

            w: int
            h: int
            w, h = self._get_element_size(tag)
            elements[elem_id] = {"tag": tag, "w": w, "h": h}

        if not elements:
            return

        lane_bounds: list[tuple[float, float, float, float]] | None = None
        pool_bounds: tuple[float, float, float, float] | None = None

        if lane_infos is not None and len(lane_infos) > 0:
            positions, lane_bounds, pool_bounds = self._compute_positions_with_lanes(
                elements, flows, lane_infos,
            )
        else:
            positions = self._compute_positions_simple(elements, flows)

        self._build_diagram_xml(
            root, process_id, elements, positions, flows,
            pool_info, lane_infos, lane_bounds, pool_bounds,
        )

    def _get_element_size(self, tag: str) -> tuple[int, int]:
        """Return (width, height) for a BPMN element based on its XML tag."""
        if tag in EVENT_TAGS:
            return (EVENT_SIZE, EVENT_SIZE)
        if tag in GATEWAY_TAGS:
            return (GATEWAY_SIZE, GATEWAY_SIZE)
        return (TASK_W, TASK_H)

    def _assign_layers(
        self,
        elements: dict[str, dict[str, str | int]],
        flows: list[dict[str, str]],
    ) -> dict[str, int]:
        """Assign BFS layer indices to elements.

        Uses BFS from start nodes (startEvent or elements with no predecessors).
        Detects back-edges for cycle awareness.

        Args:
            elements: Map of element_id to element info dict.
            flows: List of flow dicts with source/target.

        Returns:
            Map of element_id to layer index.
        """
        successors: dict[str, list[str]] = defaultdict(list)
        predecessors: dict[str, list[str]] = defaultdict(list)
        for f in flows:
            src: str = f["source"]
            tgt: str = f["target"]
            if src in elements and tgt in elements:
                successors[src].append(tgt)
                predecessors[tgt].append(src)

        start_nodes: list[str] = [
            eid for eid, el in elements.items()
            if el["tag"] == "startEvent"
            or (not predecessors[eid] and el["tag"] != "endEvent")
        ]
        if not start_nodes:
            start_nodes = [next(iter(elements))]

        layers: dict[str, int] = {}
        visited: set[str] = set()
        queue: deque[str] = deque()

        for s in start_nodes:
            layers[s] = 0
            visited.add(s)
            queue.append(s)

        while queue:
            node: str = queue.popleft()
            for succ in successors[node]:
                if succ not in visited:
                    layers[succ] = layers[node] + 1
                    visited.add(succ)
                    queue.append(succ)

        max_layer: int = max(layers.values(), default=0)
        for eid in elements:
            if eid not in layers:
                max_layer += 1
                layers[eid] = max_layer

        return layers

    def _compute_positions_simple(
        self,
        elements: dict[str, dict[str, str | int]],
        flows: list[dict[str, str]],
    ) -> dict[str, tuple[float, float]]:
        """Compute center positions for a flat process (no lanes).

        Args:
            elements: Map of element_id to element info.
            flows: List of flow dicts.

        Returns:
            Map of element_id to (cx, cy) center position.
        """
        layers: dict[str, int] = self._assign_layers(elements, flows)

        layer_groups: dict[int, list[str]] = defaultdict(list)
        for eid, layer in layers.items():
            layer_groups[layer].append(eid)

        positions: dict[str, tuple[float, float]] = {}
        for layer_idx in sorted(layer_groups.keys()):
            group: list[str] = layer_groups[layer_idx]
            cx: float = SIMPLE_START_X + layer_idx * H_SPACING
            n: int = len(group)
            for i, eid in enumerate(group):
                cy: float = SIMPLE_CENTER_Y + (i - (n - 1) / 2) * V_SPACING
                positions[eid] = (cx, cy)

        return positions

    def _compute_positions_with_lanes(
        self,
        elements: dict[str, dict[str, str | int]],
        flows: list[dict[str, str]],
        lane_infos: list[LaneLayoutInfo],
    ) -> tuple[
        dict[str, tuple[float, float]],
        list[tuple[float, float, float, float]],
        tuple[float, float, float, float],
    ]:
        """Compute positions with lane-aware layout.

        Elements are positioned within their assigned lane's vertical band.
        Pool and lane bounds are computed for diagram shapes.

        Args:
            elements: Map of element_id to element info.
            flows: List of flow dicts.
            lane_infos: Lane definitions with element assignments.

        Returns:
            Tuple of (positions, lane_bounds, pool_bounds) where:
            - positions: element_id -> (cx, cy)
            - lane_bounds: list of (x, y, w, h) for each lane
            - pool_bounds: (x, y, w, h) for the pool
        """
        layers: dict[str, int] = self._assign_layers(elements, flows)
        max_layer: int = max(layers.values(), default=0)

        # Build per-lane element sets (intersect with actual elements)
        lane_element_sets: list[set[str]] = []
        for lane in lane_infos:
            lane_element_sets.append(set(lane.element_xml_ids) & set(elements.keys()))

        # Compute required height for each lane
        lane_heights: list[float] = []
        for lane_elems in lane_element_sets:
            if not lane_elems:
                lane_heights.append(float(MIN_LANE_H))
                continue

            layer_counts: dict[int, int] = defaultdict(int)
            for eid in lane_elems:
                layer_counts[layers[eid]] += 1

            max_in_layer: int = max(layer_counts.values(), default=1)
            needed: float = max_in_layer * (TASK_H + V_SPACING) - V_SPACING + 2 * LANE_PAD_Y
            lane_heights.append(max(float(MIN_LANE_H), needed))

        # Pool and lane geometry
        element_area_w: float = (max_layer + 1) * H_SPACING + ELEMENT_PAD_X * 2
        pool_w: float = POOL_HEADER_W + LANE_HEADER_W + element_area_w
        pool_h: float = sum(lane_heights)
        pool_x: float = float(POOL_MARGIN_X)
        pool_y: float = float(POOL_MARGIN_Y)

        lane_bounds: list[tuple[float, float, float, float]] = []
        current_y: float = pool_y
        for lh in lane_heights:
            lx: float = pool_x + POOL_HEADER_W
            lw: float = pool_w - POOL_HEADER_W
            lane_bounds.append((lx, current_y, lw, lh))
            current_y += lh

        pool_bounds: tuple[float, float, float, float] = (pool_x, pool_y, pool_w, pool_h)

        # Position elements within their lanes
        elem_start_x: float = pool_x + POOL_HEADER_W + LANE_HEADER_W + ELEMENT_PAD_X

        positions: dict[str, tuple[float, float]] = {}
        for lane_idx, lane_elems in enumerate(lane_element_sets):
            _, ly, _, lh = lane_bounds[lane_idx]

            lane_layer_groups: dict[int, list[str]] = defaultdict(list)
            for eid in lane_elems:
                lane_layer_groups[layers[eid]].append(eid)

            for layer_idx_val, group in lane_layer_groups.items():
                cx: float = elem_start_x + layer_idx_val * H_SPACING
                n: int = len(group)
                lane_cy: float = ly + lh / 2
                effective_spacing: float = min(float(V_SPACING), lh / (n + 1))
                for i, eid in enumerate(group):
                    cy: float = lane_cy + (i - (n - 1) / 2) * effective_spacing
                    positions[eid] = (cx, cy)

        # Place unassigned elements below the pool
        all_assigned: set[str] = set()
        for s in lane_element_sets:
            all_assigned |= s
        unassigned: set[str] = set(elements.keys()) - all_assigned
        if unassigned:
            below_y: float = pool_y + pool_h + 100
            for eid in sorted(unassigned):
                cx_val: float = elem_start_x + layers[eid] * H_SPACING
                positions[eid] = (cx_val, below_y)
                below_y += V_SPACING

        return positions, lane_bounds, pool_bounds

    def _build_diagram_xml(
        self,
        root: ET.Element,
        process_id: str,
        elements: dict[str, dict[str, str | int]],
        positions: dict[str, tuple[float, float]],
        flows: list[dict[str, str]],
        pool_info: PoolLayoutInfo | None,
        lane_infos: list[LaneLayoutInfo] | None,
        lane_bounds: list[tuple[float, float, float, float]] | None,
        pool_bounds: tuple[float, float, float, float] | None,
    ) -> None:
        """Build the BPMNDiagram XML subtree and append it to root.

        Generates pool/lane shapes, element shapes with labels and markers,
        and edges with waypoints and labels.
        """
        diagram: ET.Element = ET.SubElement(root, f"{{{BPMNDI_NS}}}BPMNDiagram")
        diagram.set("id", f"BPMNDiagram_{process_id}")

        plane: ET.Element = ET.SubElement(diagram, f"{{{BPMNDI_NS}}}BPMNPlane")
        plane.set("id", f"BPMNPlane_{process_id}")

        if pool_info is not None:
            plane.set("bpmnElement", "Collaboration_1")
        else:
            plane.set("bpmnElement", process_id)

        # Pool shape
        if pool_info is not None and pool_bounds is not None:
            self._add_horizontal_shape(plane, pool_info.xml_id, pool_bounds)

        # Lane shapes
        if lane_infos is not None and lane_bounds is not None:
            for lane, bounds in zip(lane_infos, lane_bounds):
                self._add_horizontal_shape(plane, lane.xml_id, bounds)

        # Element shapes
        self._add_element_shapes(plane, elements, positions)

        # Edges
        self._add_edges(plane, elements, positions, flows)

    def _add_horizontal_shape(
        self,
        plane: ET.Element,
        xml_id: str,
        bounds_tuple: tuple[float, float, float, float],
    ) -> None:
        """Add a horizontal BPMNShape (pool or lane) to the diagram plane."""
        x: float
        y: float
        w: float
        h: float
        x, y, w, h = bounds_tuple

        shape: ET.Element = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape")
        shape.set("id", f"{xml_id}_di")
        shape.set("bpmnElement", xml_id)
        shape.set("isHorizontal", "true")

        bounds: ET.Element = ET.SubElement(shape, f"{{{DC_NS}}}Bounds")
        bounds.set("x", f"{x:.0f}")
        bounds.set("y", f"{y:.0f}")
        bounds.set("width", f"{w:.0f}")
        bounds.set("height", f"{h:.0f}")

    def _add_element_shapes(
        self,
        plane: ET.Element,
        elements: dict[str, dict[str, str | int]],
        positions: dict[str, tuple[float, float]],
    ) -> None:
        """Add BPMNShape elements for all positioned process elements."""
        for eid, el in elements.items():
            if eid not in positions:
                continue

            cx: float
            cy: float
            cx, cy = positions[eid]
            w: int = int(el["w"])
            h: int = int(el["h"])
            x: float = cx - w / 2
            y: float = cy - h / 2
            tag: str = str(el["tag"])

            shape: ET.Element = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape")
            shape.set("id", f"{eid}_di")
            shape.set("bpmnElement", eid)

            if tag in GATEWAY_TAGS:
                shape.set("isMarkerVisible", "true")

            bounds: ET.Element = ET.SubElement(shape, f"{{{DC_NS}}}Bounds")
            bounds.set("x", f"{x:.0f}")
            bounds.set("y", f"{y:.0f}")
            bounds.set("width", str(w))
            bounds.set("height", str(h))

            # Label below shape for events and gateways (task labels are inside)
            if tag in EVENT_TAGS or tag in GATEWAY_TAGS:
                label: ET.Element = ET.SubElement(shape, f"{{{BPMNDI_NS}}}BPMNLabel")
                label_x: float = (x - 10) if w < 40 else x
                label_w: int = 80 if w < 40 else w
                label_bounds: ET.Element = ET.SubElement(label, f"{{{DC_NS}}}Bounds")
                label_bounds.set("x", f"{label_x:.0f}")
                label_bounds.set("y", f"{y + h + 5:.0f}")
                label_bounds.set("width", str(label_w))
                label_bounds.set("height", "27")

    def _add_edges(
        self,
        plane: ET.Element,
        elements: dict[str, dict[str, str | int]],
        positions: dict[str, tuple[float, float]],
        flows: list[dict[str, str]],
    ) -> None:
        """Add BPMNEdge elements with routed waypoints and optional labels."""
        for flow in flows:
            src: str = flow["source"]
            tgt: str = flow["target"]
            if src not in positions or tgt not in positions:
                continue

            sx: float
            sy: float
            sx, sy = positions[src]
            tx: float
            ty: float
            tx, ty = positions[tgt]
            sw: int = int(elements[src]["w"])
            sh: int = int(elements[src]["h"])
            tw: int = int(elements[tgt]["w"])
            th: int = int(elements[tgt]["h"])

            edge: ET.Element = ET.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNEdge")
            edge.set("id", f"{flow['id']}_di")
            edge.set("bpmnElement", flow["id"])

            label_pos: tuple[float, float]
            if tx < sx - 20:
                label_pos = self._route_back_edge(edge, sx, sy, sw, sh, tx, ty, tw, th)
            elif abs(ty - sy) > VERTICAL_OFFSET_THRESHOLD:
                label_pos = self._route_offset_edge(edge, sx, sy, sw, sh, tx, ty, tw, th)
            else:
                label_pos = self._route_forward_edge(edge, sx, sy, sw, sh, tx, ty, tw, th)

            # Edge label for named flows
            flow_name: str = flow["name"]
            if flow_name:
                self._add_edge_label(edge, label_pos)

    def _add_waypoint(self, edge: ET.Element, x: float, y: float) -> None:
        """Add a di:waypoint to an edge element."""
        wp: ET.Element = ET.SubElement(edge, f"{{{DI_NS}}}waypoint")
        wp.set("x", f"{x:.0f}")
        wp.set("y", f"{y:.0f}")

    def _route_forward_edge(
        self,
        edge: ET.Element,
        sx: float, sy: float, sw: int, _sh: int,
        tx: float, ty: float, tw: int, _th: int,
    ) -> tuple[float, float]:
        """Route a straight left-to-right edge: source right -> target left.

        Returns:
            (label_x, label_y) center position for an optional edge label.
        """
        x1: float = sx + sw / 2
        x2: float = tx - tw / 2
        self._add_waypoint(edge, x1, sy)
        self._add_waypoint(edge, x2, ty)
        return ((x1 + x2) / 2, (sy + ty) / 2 - 10)

    def _route_back_edge(
        self,
        edge: ET.Element,
        sx: float, sy: float, _sw: int, sh: int,
        tx: float, ty: float, _tw: int, th: int,
    ) -> tuple[float, float]:
        """Route a back-edge (loop) below the elements with 4 waypoints.

        Returns:
            (label_x, label_y) center position for an optional edge label.
        """
        route_y: float = max(sy + sh / 2, ty + th / 2) + BACK_EDGE_MARGIN
        self._add_waypoint(edge, sx, sy + sh / 2)
        self._add_waypoint(edge, sx, route_y)
        self._add_waypoint(edge, tx, route_y)
        self._add_waypoint(edge, tx, ty + th / 2)
        # Label centered on the horizontal bottom segment
        return ((sx + tx) / 2, route_y - 10)

    def _route_offset_edge(
        self,
        edge: ET.Element,
        sx: float, sy: float, sw: int, _sh: int,
        tx: float, ty: float, tw: int, _th: int,
    ) -> tuple[float, float]:
        """Route an edge with vertical offset using a Z-shaped 4-waypoint path.

        Returns:
            (label_x, label_y) center position for an optional edge label.
        """
        mid_x: float = (sx + sw / 2 + tx - tw / 2) / 2
        self._add_waypoint(edge, sx + sw / 2, sy)
        self._add_waypoint(edge, mid_x, sy)
        self._add_waypoint(edge, mid_x, ty)
        self._add_waypoint(edge, tx - tw / 2, ty)
        # Label next to the vertical segment
        return (mid_x + 10, (sy + ty) / 2)

    def _add_edge_label(
        self,
        edge: ET.Element,
        label_pos: tuple[float, float],
    ) -> None:
        """Add a BPMNLabel to a named edge at the given position."""
        lx: float
        ly: float
        lx, ly = label_pos
        label: ET.Element = ET.SubElement(edge, f"{{{BPMNDI_NS}}}BPMNLabel")
        label_bounds: ET.Element = ET.SubElement(label, f"{{{DC_NS}}}Bounds")
        label_bounds.set("x", f"{lx - 30:.0f}")
        label_bounds.set("y", f"{ly - 7:.0f}")
        label_bounds.set("width", "60")
        label_bounds.set("height", "14")
