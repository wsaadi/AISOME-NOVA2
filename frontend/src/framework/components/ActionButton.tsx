/**
 * ActionButton — Bouton d'action standardisé pour les agents.
 *
 * Usage:
 *   import { ActionButton } from '@framework/components';
 *   <ActionButton label="Analyser" icon={<AnalyticsIcon />} onClick={handleAnalyze} />
 */

import React from 'react';
import { Button, ButtonProps, CircularProgress } from '@mui/material';

interface ActionButtonProps extends Omit<ButtonProps, 'onClick'> {
  /** Texte du bouton */
  label: string;
  /** Icône optionnelle */
  icon?: React.ReactNode;
  /** Callback au clic */
  onClick: () => void | Promise<void>;
  /** Afficher un loader */
  loading?: boolean;
}

export const ActionButton: React.FC<ActionButtonProps> = ({
  label,
  icon,
  onClick,
  loading = false,
  variant = 'contained',
  ...buttonProps
}) => {
  return (
    <Button
      variant={variant}
      startIcon={loading ? <CircularProgress size={18} color="inherit" /> : icon}
      onClick={onClick}
      disabled={loading || buttonProps.disabled}
      {...buttonProps}
    >
      {label}
    </Button>
  );
};
