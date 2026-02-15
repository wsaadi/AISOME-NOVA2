/**
 * Agent View Registry — Auto-discovers agent custom frontend views.
 *
 * Any directory under ./agents/ with an index.tsx is automatically registered.
 * Directories starting with _ are excluded (e.g. _template).
 *
 * Uses webpack require.context in 'lazy' mode for automatic code-splitting:
 * each agent's view is loaded on demand when the user navigates to it.
 *
 * To add a new agent view:
 *   1. Create a directory: frontend/src/agents/{slug}/
 *   2. Add index.tsx exporting a React.FC<AgentViewProps> as default
 *   3. Rebuild the frontend — it will be auto-discovered
 *
 * No manual editing of this file is needed.
 */

import { lazy, ComponentType } from 'react';
import { AgentViewProps } from 'framework/types';

type AgentViewComponent = ComponentType<AgentViewProps>;

// Auto-discover all agent views at build time.
// 'lazy' mode enables code-splitting: each agent view is a separate chunk.
const agentModules = require.context(
  './',
  true,
  /^\.\/[^_][^/]+\/index\.tsx$/,
  'lazy'
);

const agentViews: Record<string, React.LazyExoticComponent<AgentViewComponent>> = {};

agentModules.keys().forEach((key: string) => {
  const match = key.match(/^\.\/([^/]+)\/index\.tsx$/);
  if (match) {
    const slug = match[1];
    agentViews[slug] = lazy(
      () => agentModules(key) as Promise<{ default: AgentViewComponent }>
    );
  }
});

export default agentViews;
