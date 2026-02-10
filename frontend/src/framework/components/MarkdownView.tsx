/**
 * MarkdownView — Rendu Markdown pour les réponses des agents.
 *
 * Usage:
 *   import { MarkdownView } from 'framework/components';
 *   <MarkdownView content="# Hello **world**" />
 */

import React from 'react';
import { Box, Typography } from '@mui/material';

interface MarkdownViewProps {
  /** Contenu markdown à rendre */
  content: string;
}

/**
 * Rendu simplifié du Markdown.
 * Supporte: bold, italic, code, code blocks, headers, lists, links.
 */
export const MarkdownView: React.FC<MarkdownViewProps> = ({ content }) => {
  const renderContent = (text: string) => {
    // Split par blocs de code
    const parts = text.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      // Code block
      if (part.startsWith('```') && part.endsWith('```')) {
        const code = part.slice(3, -3).replace(/^\w*\n/, '');
        return (
          <Box
            key={index}
            component="pre"
            sx={{
              bgcolor: 'grey.100',
              p: 2,
              borderRadius: 1,
              overflow: 'auto',
              fontSize: '0.85rem',
              fontFamily: 'monospace',
              my: 1,
            }}
          >
            <code>{code}</code>
          </Box>
        );
      }

      // Regular text — render inline markdown
      return (
        <Typography
          key={index}
          component="div"
          variant="body1"
          sx={{ '& p': { m: 0 }, lineHeight: 1.7 }}
          dangerouslySetInnerHTML={{ __html: renderInlineMarkdown(part) }}
        />
      );
    });
  };

  return <Box>{renderContent(content)}</Box>;
};

function renderInlineMarkdown(text: string): string {
  let html = text
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Headers
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    // Bold & Italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code style="background:#f5f5f5;padding:2px 6px;border-radius:3px;font-size:0.9em">$1</code>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    // Unordered lists
    .replace(/^[*-] (.+)$/gm, '<li>$1</li>')
    // Line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>');

  // Wrap lists
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
  // Wrap in paragraphs
  html = `<p>${html}</p>`;

  return html;
}
