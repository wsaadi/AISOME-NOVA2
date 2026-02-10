/**
 * Template Agent — Frontend entry point.
 *
 * Interface de chat basique avec streaming.
 * Copiez et adaptez à votre besoin.
 */

import React from 'react';
import { ChatPanel } from 'framework/components';
import { useAgent } from 'framework/hooks';
import { AgentViewProps } from 'framework/types';

const TemplateAgentView: React.FC<AgentViewProps> = ({ agent, sessionId }) => {
  const { sendMessage, messages, isLoading, streamingContent } = useAgent(agent.slug, sessionId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <ChatPanel
        messages={messages}
        onSendMessage={sendMessage}
        isLoading={isLoading}
        streamingContent={streamingContent}
        placeholder="Écrivez votre message..."
      />
    </div>
  );
};

export default TemplateAgentView;
