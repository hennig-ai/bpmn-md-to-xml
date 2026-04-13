# Elementregeln: Flow-Objekt

**Hierarchie-Ebene:** flow_object (Basisebene fuer alle Flow-Objekte)

**Uebergeordnete Regeln:** keine

---

| rule_id | level | element_type | subtype | where_clause | assertion | description | message_template | spec_reference | spec_verified | personal |
|---------|-------|-------------|---------|-------------|-----------|-------------|-----------------|----------------|---------------|----------|
| FLO-001 | basic | flow_object | | element_type NOT IN (startEvent, endEvent) | COUNT(incoming_flows) + COUNT(outgoing_flows) >= 1 | Jedes Flow-Objekt, das kein Start-Event und kein End-Event ist, muss mindestens einen eingehenden oder einen ausgehenden Sequence Flow besitzen. | Flow-Objekt {element_id} has no sequence flows | VAL-05 | no | |
