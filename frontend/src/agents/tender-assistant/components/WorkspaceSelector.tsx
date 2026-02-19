/**
 * WorkspaceSelector — Sélecteur d'espace de travail collaboratif.
 *
 * Affiché avant la vue principale de l'agent pour permettre à l'utilisateur
 * de choisir ou créer un workspace partagé. Tous les membres d'un workspace
 * partagent les mêmes documents et données de projet.
 */

import React, { useEffect, useState, useCallback } from 'react';
import api from '../../../services/api';

interface Workspace {
  id: string;
  name: string;
  description: string | null;
  agent_slug: string;
  members: { id: string; user_id: string; username: string; role: string }[];
  created_at: string;
  updated_at: string;
}

interface WorkspaceSelectorProps {
  agentSlug: string;
  onSelect: (workspaceId: string) => void;
}

const WorkspaceSelector: React.FC<WorkspaceSelectorProps> = ({ agentSlug, onSelect }) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');

  const fetchWorkspaces = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/workspaces?agent_slug=${agentSlug}`);
      setWorkspaces(res.data);
    } catch {
      // API not ready yet or no workspaces
    } finally {
      setLoading(false);
    }
  }, [agentSlug]);

  useEffect(() => { fetchWorkspaces(); }, [fetchWorkspaces]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await api.post('/api/workspaces', {
        name: newName.trim(),
        description: newDesc.trim() || null,
        agent_slug: agentSlug,
      });
      onSelect(res.data.id);
    } catch {
      // handle error
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <p style={loadingText}>Chargement des espaces de travail...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={headerStyle}>
          <span style={headerIcon}>&#128193;</span>
          <div>
            <h2 style={titleStyle}>Espace de travail</h2>
            <p style={subtitleStyle}>
              Choisissez un espace existant ou créez-en un nouveau.
              Les documents et travaux sont partagés entre tous les membres.
            </p>
          </div>
        </div>

        {/* Existing workspaces */}
        {workspaces.length > 0 && (
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Vos espaces de travail</h3>
            <div style={listStyle}>
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  style={workspaceItemStyle}
                  onClick={() => onSelect(ws.id)}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = '#1976d2';
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#f5f9ff';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = '#e0e0e0';
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#fff';
                  }}
                >
                  <div style={wsHeaderStyle}>
                    <span style={wsNameStyle}>{ws.name}</span>
                    <span style={wsMembersStyle}>
                      {ws.members.length} membre{ws.members.length > 1 ? 's' : ''}
                    </span>
                  </div>
                  {ws.description && (
                    <p style={wsDescStyle}>{ws.description}</p>
                  )}
                  <div style={wsFooterStyle}>
                    <span style={wsDateStyle}>
                      Mis à jour le {new Date(ws.updated_at).toLocaleDateString('fr-FR')}
                    </span>
                    <span style={wsArrowStyle}>&#8594;</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Create new workspace */}
        <div style={sectionStyle}>
          <h3 style={sectionTitleStyle}>
            {workspaces.length > 0 ? 'Ou créer un nouvel espace' : 'Créer votre premier espace de travail'}
          </h3>
          <div style={formStyle}>
            <input
              style={inputStyle}
              placeholder="Nom de l'espace (ex: AO Mairie de Paris 2026)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <input
              style={inputStyle}
              placeholder="Description (optionnel)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <button
              style={{
                ...btnStyle,
                ...(creating || !newName.trim() ? btnDisabledStyle : {}),
              }}
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
            >
              {creating ? 'Création...' : 'Créer l\'espace de travail'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Styles
// ============================================================================

const containerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  padding: 24,
  background: 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)',
};

const cardStyle: React.CSSProperties = {
  maxWidth: 560,
  width: '100%',
  backgroundColor: '#fff',
  borderRadius: 12,
  padding: 32,
  boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 16,
  marginBottom: 28,
};

const headerIcon: React.CSSProperties = {
  fontSize: 32,
};

const titleStyle: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 700,
  color: '#1a1a1a',
  margin: 0,
};

const subtitleStyle: React.CSSProperties = {
  fontSize: 13,
  color: '#666',
  margin: '6px 0 0',
  lineHeight: 1.5,
};

const sectionStyle: React.CSSProperties = {
  marginBottom: 24,
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: '#555',
  margin: '0 0 12px',
  textTransform: 'uppercase',
  letterSpacing: '0.3px',
};

const listStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
};

const workspaceItemStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  padding: 16,
  borderRadius: 8,
  border: '1px solid #e0e0e0',
  backgroundColor: '#fff',
  cursor: 'pointer',
  textAlign: 'left',
  transition: 'all 0.15s ease',
  width: '100%',
};

const wsHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginBottom: 4,
};

const wsNameStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: '#1a1a1a',
};

const wsMembersStyle: React.CSSProperties = {
  fontSize: 11,
  color: '#888',
  padding: '2px 8px',
  borderRadius: 10,
  backgroundColor: '#f0f0f0',
};

const wsDescStyle: React.CSSProperties = {
  fontSize: 12,
  color: '#666',
  margin: '4px 0 0',
  lineHeight: 1.4,
};

const wsFooterStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginTop: 8,
};

const wsDateStyle: React.CSSProperties = {
  fontSize: 11,
  color: '#aaa',
};

const wsArrowStyle: React.CSSProperties = {
  fontSize: 16,
  color: '#1976d2',
};

const formStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
};

const inputStyle: React.CSSProperties = {
  padding: '10px 14px',
  fontSize: 13,
  border: '1px solid #ddd',
  borderRadius: 6,
  outline: 'none',
  color: '#333',
};

const btnStyle: React.CSSProperties = {
  padding: '10px 20px',
  fontSize: 13,
  fontWeight: 600,
  borderRadius: 6,
  border: 'none',
  backgroundColor: '#1976d2',
  color: '#fff',
  cursor: 'pointer',
  transition: 'opacity 0.15s',
};

const btnDisabledStyle: React.CSSProperties = {
  opacity: 0.5,
  cursor: 'not-allowed',
};

const loadingText: React.CSSProperties = {
  fontSize: 14,
  color: '#666',
  textAlign: 'center',
  padding: 40,
};

export default WorkspaceSelector;
