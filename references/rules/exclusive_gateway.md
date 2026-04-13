# Elementregeln: Exclusive Gateway (XOR)

**Hierarchie-Ebene:** gateway / subtype: exclusive

**Uebergeordnete Regeln:** Es gelten zusaetzlich die Regeln aus [flow_object.md](flow_object.md)

---

| rule_id | level | element_type | subtype | where_clause | assertion | description | message_template | spec_reference | spec_verified | personal |
|---------|-------|-------------|---------|-------------|-----------|-------------|-----------------|----------------|---------------|----------|
| XOR-001 | spec_v2 | gateway | exclusive | gateway_direction == diverging | COUNT(outgoing_flows) >= 2 | Ein Exclusive Gateway mit gateway_direction=diverging muss mindestens 2 ausgehende Sequence Flows haben. | Gateway {element_id} has less than 2 outgoing sequence flows | | no | |
| XOR-002 | spec_v2 | gateway | exclusive | gateway_direction == converging | COUNT(incoming_flows) >= 2 | Ein Exclusive Gateway mit gateway_direction=converging muss mindestens 2 eingehende Sequence Flows haben. | Gateway {element_id} has less than 2 incoming sequence flows | | no | |
| XOR-003 | spec_v2 | gateway | exclusive | gateway_direction == diverging | FOR_EACH outgoing_flows: is_default == true OR condition_expression != null | Bei einem divergierenden Exclusive Gateway muessen alle ausgehenden Sequence Flows (ausser dem optionalen Default Flow) eine Condition Expression haben. | Sequence Flow {flow_id} on Gateway {element_id} missing condition expression | | no | |
| XOR-004 | best_practice | gateway | exclusive | gateway_direction == diverging | EXISTS outgoing_flows: is_default == true | Ein divergierendes Exclusive Gateway sollte einen Default Flow haben, um sicherzustellen, dass immer mindestens ein Pfad genommen wird. | Gateway {element_id} has no default flow | | no | |
