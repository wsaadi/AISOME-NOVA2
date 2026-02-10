# Bug Guide — AISOME NOVA2

> Référence des bugs rencontrés et corrigés. À consulter avant tout ajout/modification pour ne pas reproduire les mêmes erreurs.

---

## BUG-001 : `@framework/` — Path alias non supporté par CRA

**Date** : 2026-02-10
**Composant** : Frontend (TypeScript / React)
**Symptôme** :
```
TS2307: Cannot find module '@framework/types' or its corresponding type declarations.
```

**Cause racine** :
`react-scripts` (Create React App) ne supporte PAS les `paths` dans `tsconfig.json`. L'option est silencieusement ignorée au build. Les imports `@framework/xxx` ne sont donc pas résolus.

**Solution** :
1. Ajouter `"baseUrl": "src"` dans `tsconfig.json` (supporté nativement par CRA)
2. Utiliser `framework/xxx` au lieu de `@framework/xxx` pour tous les imports

**Imports corrects** :
```tsx
// ✅ CORRECT
import { ChatPanel } from 'framework/components';
import { useAgent } from 'framework/hooks';
import { AgentViewProps } from 'framework/types';

// ❌ INCORRECT — ne compile pas avec CRA
import { ChatPanel } from '@framework/components';
```

**Fichiers impactés** :
- `frontend/tsconfig.json` (ajout `baseUrl`)
- Tous les fichiers frontend qui importent depuis le framework
- `AGENT_FRAMEWORK.md` (documentation)
- `backend/app/framework/generator.py` (template generator)
- `backend/app/agents/_template/frontend/index.tsx` (template)

**Règle à suivre** :
> Dans le frontend, tout import absolu utilise le préfixe `framework/` (sans `@`).
> Le `baseUrl: "src"` dans tsconfig.json permet de résoudre ces imports comme des chemins absolus depuis `src/`.

**Alternative non retenue** :
- `@craco/craco` permettrait d'utiliser `@framework/` mais ajoute une dépendance et de la complexité de build. Rejeté au profit de la solution native CRA.

---

## Règles générales anti-régression

### Frontend
1. **Pas de `@` dans les imports framework** — utiliser `framework/` (baseUrl: src)
2. **Ne pas importer directement MUI, axios, recharts** dans les agents — passer par `framework/components`
3. **Vérifier le build Docker** après tout ajout de fichier frontend : `docker compose build frontend`

### Backend
1. **Les imports dans `agent.py`** doivent utiliser `app.framework.base` et `app.framework.schemas`, jamais de libs externes directement
2. **Pas d'import `os`, `subprocess`, `requests`** dans les agents — le validateur les bloque

### Docker
1. **Toujours ajouter les healthchecks** pour les nouveaux services
2. **Les `depends_on` avec `condition: service_healthy`** évitent les race conditions au démarrage
