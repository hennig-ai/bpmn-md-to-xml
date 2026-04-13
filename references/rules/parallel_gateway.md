# Elementregeln: Parallel Gateway (AND)

**Hierarchie-Ebene:** gateway / subtype: parallel

**Uebergeordnete Regeln:** Es gelten zusaetzlich die Regeln aus [flow_object.md](flow_object.md)

---

| rule_id | level | element_type | subtype | where_clause | assertion | description | message_template | spec_reference | spec_verified | personal |
|---------|-------|-------------|---------|-------------|-----------|-------------|-----------------|----------------|---------------|----------|
| AND-001 | spec_v2 | gateway | parallel | gateway_direction == diverging | COUNT(outgoing_flows) >= 2 | Ein Parallel Gateway mit gateway_direction=diverging (Fork) muss mindestens 2 ausgehende Sequence Flows haben. | Gateway {element_id} has less than 2 outgoing sequence flows | | no | |
| AND-002 | spec_v2 | gateway | parallel | gateway_direction == converging | COUNT(incoming_flows) >= 2 | Ein Parallel Gateway mit gateway_direction=converging (Join) muss mindestens 2 eingehende Sequence Flows haben. | Gateway {element_id} has less than 2 incoming sequence flows | | no | |
| AND-003 | spec_v2 | gateway | parallel | | FOR_EACH outgoing_flows: condition_expression == null | Bei einem Parallel Gateway duerfen die ausgehenden Sequence Flows keine Condition Expression haben. Alle Pfade werden immer parallel ausgefuehrt. | Sequence Flow {flow_id} on Gateway {element_id} has condition expression | BPMN 2.0.2 — All outgoing Sequence Flows of a Parallel Gateway MUST NOT have condition expressions. | no | |
