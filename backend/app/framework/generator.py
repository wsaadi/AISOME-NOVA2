"""
Agent Template Generator — Génère le squelette d'un nouvel agent.

Crée un package agent complet et conforme au framework.
Tout agent démarre depuis ce template, que ce soit par un dev, Claude Code ou le générateur.

Usage:
    python -m app.framework.generator mon-agent "Mon Super Agent" "Description de l'agent"

Résultat:
    backend/app/agents/mon-agent/
    ├── manifest.json
    ├── agent.py
    └── prompts/
        └── system.md
    frontend/src/agents/mon-agent/
    ├── index.tsx
    ├── components/
    └── styles.ts
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Racines des agents
BACKEND_AGENTS_ROOT = Path(__file__).parent.parent / "agents"
FRONTEND_AGENTS_ROOT = Path(__file__).parent.parent.parent.parent / "frontend" / "src" / "agents"


def slugify(name: str) -> str:
    """Convertit un nom en slug kebab-case."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def pascal_case(slug: str) -> str:
    """Convertit un slug en PascalCase."""
    return "".join(word.capitalize() for word in slug.split("-"))


def generate_manifest(slug: str, name: str, description: str, author: str = "") -> str:
    """Génère le contenu de manifest.json."""
    manifest = {
        "name": name,
        "slug": slug,
        "version": "1.0.0",
        "description": description,
        "author": author,
        "icon": "smart_toy",
        "category": "general",
        "tags": [],
        "dependencies": {"tools": [], "connectors": []},
        "triggers": [{"type": "user_message", "config": {}}],
        "capabilities": ["streaming"],
        "min_platform_version": "1.0.0",
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False)


def generate_agent_py(slug: str, name: str, description: str) -> str:
    """Génère le contenu de agent.py."""
    class_name = pascal_case(slug) + "Agent"
    return f'''"""
Agent: {name}
Description: {description}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from app.framework.base import BaseAgent
from app.framework.schemas import (
    AgentManifest,
    AgentResponse,
    AgentResponseChunk,
    UserMessage,
)

if TYPE_CHECKING:
    from app.framework.runtime.context import AgentContext


class {class_name}(BaseAgent):
    """
    {description}

    Workflow:
        1. Reçoit le message de l'utilisateur
        2. Envoie au LLM avec le system prompt
        3. Retourne la réponse
    """

    @property
    def manifest(self) -> AgentManifest:
        """Retourne le manifeste de l'agent."""
        import json
        from pathlib import Path

        manifest_path = Path(__file__).parent / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)
        return AgentManifest(**data)

    async def handle_message(
        self, message: UserMessage, context: AgentContext
    ) -> AgentResponse:
        """
        Traite un message utilisateur.

        Args:
            message: Message de l'utilisateur
            context: Contexte d'exécution framework

        Returns:
            AgentResponse avec la réponse de l'agent
        """
        # Charger le system prompt
        from pathlib import Path

        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = system_prompt_path.read_text()

        # Appeler le LLM via le context
        response = await context.llm.chat(
            prompt=message.content,
            system_prompt=system_prompt,
        )

        return AgentResponse(content=response)

    async def handle_message_stream(
        self, message: UserMessage, context: AgentContext
    ) -> AsyncIterator[AgentResponseChunk]:
        """
        Traite un message en mode streaming.

        Args:
            message: Message de l'utilisateur
            context: Contexte d'exécution framework

        Yields:
            AgentResponseChunk avec les tokens au fur et à mesure
        """
        from pathlib import Path

        system_prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = system_prompt_path.read_text()

        async for token in context.llm.stream(
            prompt=message.content,
            system_prompt=system_prompt,
        ):
            yield AgentResponseChunk(content=token)

        yield AgentResponseChunk(content="", is_final=True)
'''


def generate_system_prompt(name: str, description: str) -> str:
    """Génère le contenu de prompts/system.md."""
    return f"""# {name}

{description}

## Instructions

Tu es l'agent "{name}". Réponds de manière claire, concise et utile.

## Règles

- Sois précis et factuel
- Si tu ne sais pas, dis-le
- Respecte le contexte de la conversation
"""


def generate_index_tsx(slug: str, name: str) -> str:
    """Génère le contenu de frontend/index.tsx."""
    component_name = pascal_case(slug) + "View"
    return f"""/**
 * Agent: {name}
 * Frontend entry point
 */

import React, {{ useState }} from 'react';
import {{ ChatPanel, ActionButton }} from '@framework/components';
import {{ useAgent }} from '@framework/hooks';
import {{ AgentViewProps }} from '@framework/types';

const {component_name}: React.FC<AgentViewProps> = ({{ agent, sessionId }}) => {{
  const {{ sendMessage, messages, isLoading, streamingContent }} = useAgent(agent.slug, sessionId);

  return (
    <div style={{{{ display: 'flex', flexDirection: 'column', height: '100%' }}}}>
      <ChatPanel
        messages={{messages}}
        onSendMessage={{sendMessage}}
        isLoading={{isLoading}}
        streamingContent={{streamingContent}}
        placeholder="Écrivez votre message..."
      />
    </div>
  );
}};

export default {component_name};
"""


def generate_styles_ts(slug: str) -> str:
    """Génère le contenu de frontend/styles.ts."""
    return """/**
 * Agent styles — Custom styles for this agent.
 *
 * Import framework theme utilities:
 *   import { useTheme } from '@framework/hooks';
 */

export const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
  },
};
"""


def create_agent(
    slug: str,
    name: str,
    description: str,
    author: str = "",
) -> Path:
    """
    Crée un package agent complet.

    Args:
        slug: Slug de l'agent (kebab-case)
        name: Nom d'affichage
        description: Description
        author: Auteur

    Returns:
        Path du dossier backend créé

    Raises:
        FileExistsError: Si l'agent existe déjà
    """
    # Valider le slug
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
        slug = slugify(name) if not slug else slugify(slug)

    backend_dir = BACKEND_AGENTS_ROOT / slug
    frontend_dir = FRONTEND_AGENTS_ROOT / slug

    if backend_dir.exists():
        raise FileExistsError(f"L'agent '{slug}' existe déjà: {backend_dir}")

    # Créer l'arborescence backend
    backend_dir.mkdir(parents=True)
    (backend_dir / "prompts").mkdir()

    (backend_dir / "manifest.json").write_text(
        generate_manifest(slug, name, description, author)
    )
    (backend_dir / "agent.py").write_text(generate_agent_py(slug, name, description))
    (backend_dir / "prompts" / "system.md").write_text(
        generate_system_prompt(name, description)
    )

    # Créer l'arborescence frontend
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "components").mkdir()

    (frontend_dir / "index.tsx").write_text(generate_index_tsx(slug, name))
    (frontend_dir / "styles.ts").write_text(generate_styles_ts(slug))

    logger.info(f"Agent created: {slug} at {backend_dir}")
    return backend_dir


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m app.framework.generator <slug> <name> [description]")
        sys.exit(1)

    agent_slug = sys.argv[1]
    agent_name = sys.argv[2]
    agent_description = sys.argv[3] if len(sys.argv) > 3 else agent_name

    try:
        path = create_agent(agent_slug, agent_name, agent_description)
        print(f"Agent '{agent_slug}' créé avec succès: {path}")
    except FileExistsError as e:
        print(f"Erreur: {e}")
        sys.exit(1)
