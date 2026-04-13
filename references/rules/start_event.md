# Elementregeln: Start-Event

**Hierarchie-Ebene:** event / subtype: start

**Uebergeordnete Regeln:** Es gelten zusaetzlich die Regeln aus [flow_object.md](flow_object.md)

---

| rule_id | level | element_type | subtype | where_clause | assertion | description | message_template | spec_reference | spec_verified | personal |
|---------|-------|-------------|---------|-------------|-----------|-------------|-----------------|----------------|---------------|----------|
| SRT-001 | spec_v2 | event | start | | COUNT(incoming_flows) == 0 | Ein Start-Event darf keine eingehenden Sequence Flows besitzen. | Start-Event {element_id} has incoming sequence flows | BPMN 2.0.2, Section 10.5.2 | no | |
| SRT-002 | spec_v2 | event | start | | COUNT(outgoing_flows) >= 1 | Ein Start-Event muss mindestens einen ausgehenden Sequence Flow haben. | Start-Event {element_id} has no outgoing sequence flows | BPMN 2.0.2, Section 10.5.2 | no | |
