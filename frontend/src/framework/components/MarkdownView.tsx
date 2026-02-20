/**
 * MarkdownView — Rendu Markdown pour les réponses des agents.
 *
 * Usage:
 *   import { MarkdownView } from 'framework/components';
 *   <MarkdownView content="# Hello **world**" />
 */

import React, { useEffect, useRef, useId } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Box } from '@mui/material';
import mermaid from 'mermaid';

// Initialize mermaid once
mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });

interface MarkdownViewProps {
  /** Contenu markdown à rendre */
  content: string;
}

const markdownStyles = {
  '& h1': { fontSize: '1.4rem', fontWeight: 700, mt: 2, mb: 1 },
  '& h2': { fontSize: '1.2rem', fontWeight: 700, mt: 2, mb: 1 },
  '& h3': { fontSize: '1.05rem', fontWeight: 600, mt: 1.5, mb: 0.5 },
  '& h4': { fontSize: '0.95rem', fontWeight: 600, mt: 1, mb: 0.5 },
  '& p': { my: 0.5, lineHeight: 1.7 },
  '& ul, & ol': { pl: 3, my: 0.5 },
  '& li': { mb: 0.3, lineHeight: 1.6 },
  '& a': { color: 'primary.main', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } },
  '& code': {
    bgcolor: 'grey.100',
    px: 0.8,
    py: 0.2,
    borderRadius: 0.5,
    fontSize: '0.88em',
    fontFamily: '"Fira Code", "Consolas", monospace',
  },
  '& pre': {
    bgcolor: 'grey.100',
    p: 2,
    borderRadius: 1,
    overflow: 'auto',
    my: 1,
    '& code': { bgcolor: 'transparent', p: 0, fontSize: '0.85rem' },
  },
  '& blockquote': {
    borderLeft: '3px solid',
    borderColor: 'primary.main',
    pl: 2,
    ml: 0,
    my: 1,
    color: 'text.secondary',
    fontStyle: 'italic',
  },
  '& hr': {
    border: 'none',
    borderTop: '1px solid',
    borderColor: 'divider',
    my: 2,
  },
  '& table': {
    width: '100%',
    borderCollapse: 'collapse',
    my: 1.5,
    fontSize: '0.9rem',
  },
  '& thead': {
    bgcolor: 'grey.100',
  },
  '& th': {
    border: '1px solid',
    borderColor: 'divider',
    px: 1.5,
    py: 1,
    fontWeight: 600,
    textAlign: 'left',
    fontSize: '0.85rem',
  },
  '& td': {
    border: '1px solid',
    borderColor: 'divider',
    px: 1.5,
    py: 0.8,
    verticalAlign: 'top',
  },
  '& tr:nth-of-type(even)': {
    bgcolor: 'grey.50',
  },
  '& img': { maxWidth: '100%', borderRadius: 1 },
  '& strong': { fontWeight: 600 },
};

/**
 * Mermaid code block renderer.
 * Renders mermaid diagrams (graph TD, sequenceDiagram, etc.)
 */
const MermaidBlock: React.FC<{ code: string }> = ({ code }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const id = `mermaid-${useId().replace(/:/g, '')}`;

  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;

    (async () => {
      try {
        const { svg } = await mermaid.render(id, code);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch {
        // If mermaid fails, show raw code
        if (!cancelled && containerRef.current) {
          containerRef.current.textContent = code;
        }
      }
    })();

    return () => { cancelled = true; };
  }, [code, id]);

  return (
    <Box
      ref={containerRef}
      sx={{ my: 2, display: 'flex', justifyContent: 'center', overflow: 'auto' }}
    />
  );
};

export const MarkdownView: React.FC<MarkdownViewProps> = ({ content }) => {
  return (
    <Box sx={{ lineHeight: 1.7, fontSize: '0.9rem', ...markdownStyles }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const lang = match?.[1];
            const codeStr = String(children).replace(/\n$/, '');

            if (lang === 'mermaid') {
              return <MermaidBlock code={codeStr} />;
            }

            // Inline code (no language class) vs block code
            if (!className) {
              return <code {...props}>{children}</code>;
            }

            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </Box>
  );
};
