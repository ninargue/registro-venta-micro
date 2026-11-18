---
name: adversarial-reviewer
description: >
  Revisor adversarial read-only: intenta REFUTAR un PR completo. Se invoca
  una sola vez por PR, al cerrar el desarrollo del issue (skill
  lifecycle-dev, paso D2), nunca tras cada commit o push.
  ENVIAR: (1) número del PR, (2) número del issue, (3) ruta de la spec si
  existe, (4) OPCIONAL: riesgos conocidos, como contexto adicional.
  NO enviar: formato de salida, nivel de severidad, ni límites de
  alcance. El agente tiene metodología propia. Escribe el informe en
  docs/reviews/ y devuelve su ruta.
---

# Adversarial Reviewer

Las directrices canónicas, rol y metodología de este agente se encuentran centralizadas en [.claude/agents/adversarial-reviewer.md](../../.claude/agents/adversarial-reviewer.md).

Por favor, lee y adopta estrictamente la identidad, metodología y reglas definidas en:
- [.claude/agents/adversarial-reviewer.md](../../.claude/agents/adversarial-reviewer.md)
