---
name: frontend-premerge-check
description: Verify build, lint, tests, and accessibility invariants before merging frontend changes to main.
---

## Objetivo

Validar que los cambios en frontend/ no regresan en build, lint, pruebas unitarias, tamaño de bundle, accesibilidad y rendimiento. Se ejecuta en una copia temporal sin node_modules para garantizar aislamiento.

## Inputs

- Rama: feature/agent-skills (actual)
- Directorio: frontend/
- Repositorio: 4GeeksAcademy/hnandrade_ai-eng-financial-dashboard-context-project

## Pasos

1. Copiar frontend/ a /tmp/frontend-test sin node_modules.
2. En la copia: npm ci, npm run build, npm run lint, npm run test.
3. Verificar tamaño del chunk index y presencia de chunks lazy.
4. Validar invariantes a11y en index.html y src/ (grep).
5. Ejecutar script de smoke test en navegador (si frontend/e2e existe).
6. Generar tabla de criterios de aceptación.

## Output esperado

Tabla: Criterio | Comando | Resultado | Marca

Ejemplo:
| AC1 | npm run build | Exit 0, warnings: 0 | ✅ |
| AC2 | npm run lint | Exit 0 | ✅ |
| AC3 | npm run test | 5 tests OK | ✅ |
| AC4 | grep "Financial Overview" index.html | Encontrado | ✅ |
| AC5 | /tmp/pw/bin/python frontend/e2e/dashboard_smoke.py | Exit 0 | ✅ |

Veredicto: LISTO si todos los ACs pasan; NO LISTO si alguno falla.

## Criterios de aceptación

- **AC1**: `npm run build` en /tmp/frontend-test exit 0 con 0 warnings (grep -ci "warning" en stdout/stderr).
- **AC2**: `npm run lint` exit 0.
- **AC3**: `npm run test` (vitest run) muestra "5 passed" o similar.
- **AC4**: Chunk index < 200 kB (verificar dist/index-*.js).
- **AC5**: Chunks lazy para gráficos existen (verificar dist/*-chart-*.js).
- **AC6**: Título "Financial Overview" en index.html.
- **AC7**: Meta description presente en index.html.
- **AC8**: Un único h1 en src/App.tsx (grep -c "<h1" o CardTitle).
- **AC9**: Tablas sr-only con caption en IncomeOutcomeChart y ProfitPercentChart.
- **AC10**: aria-busy en carga, aria-label en sections, role="alert" lang="es" en error.
- **AC11**: Sin animaciones en Skeleton (grep "animation:" src/components/).
- **AC12**: Foco visible con outline en gráficos (grep "outline" src/components/).
- **AC13**: `/tmp/pw/bin/python frontend/e2e/dashboard_smoke.py` exit 0.

## No hacer

- Modificar backend/, package.json, package-lock.json, index.html, ni .agents/.
- Ejecutar npm install (usar npm ci).
- Usar node_modules del workspace (usar copia temporal en /tmp).
- Cambiar ramas ni hacer push.
- Verificar solo con npm run build sin revisar warnings.

