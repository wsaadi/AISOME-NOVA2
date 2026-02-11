/**
 * Agent View Registry — Maps agent slugs to their custom frontend views.
 *
 * When an agent has a custom UI (index.tsx in its frontend folder),
 * it must be registered here for the AgentRuntimePage to load it.
 *
 * Agents not listed here will use the default ChatPanel-based view.
 *
 * Usage:
 *   import agentViews from 'agents/registry';
 *   const CustomView = agentViews['agent-slug'];
 */

import { lazy, ComponentType } from 'react';
import { AgentViewProps } from 'framework/types';

type AgentViewComponent = ComponentType<AgentViewProps>;

const agentViews: Record<string, React.LazyExoticComponent<AgentViewComponent>> = {
  'agent-creator': lazy(() => import('./agent-creator')),
};

export default agentViews;
