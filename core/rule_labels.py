RULE_LABELS = {
    "equals": "Igual a",
    "not_equals": "Distinto de",
    "greater": "Mayor que",
    "less": "Menor que",
    "between": "Entre",
    "contains": "Contiene texto",
    "starts_with": "Empieza con",
    "ends_with": "Termina con",
    "before": "Antes de (fecha)",
    "after": "Después de (fecha)"
}

# Inverso (para convertir de UI → lógica)
RULE_LABELS_INV = {v: k for k, v in RULE_LABELS.items()}