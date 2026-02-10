/**
 * SettingsPanel — Panneau de paramètres pour les agents.
 *
 * Fournit des contrôles standardisés (sliders, selects, toggles)
 * pour configurer le comportement d'un agent.
 *
 * Usage:
 *   import { SettingsPanel } from '@framework/components';
 *   <SettingsPanel
 *     settings={[
 *       { key: 'temperature', label: 'Température', type: 'slider', min: 0, max: 1, step: 0.1 },
 *       { key: 'language', label: 'Langue', type: 'select', options: ['fr', 'en', 'es'] },
 *     ]}
 *     values={settings}
 *     onChange={setSettings}
 *   />
 */

import React from 'react';
import {
  Box,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Switch,
  TextField,
  Typography,
} from '@mui/material';

interface SettingDefinition {
  /** Clé unique */
  key: string;
  /** Label affiché */
  label: string;
  /** Type de contrôle */
  type: 'slider' | 'select' | 'toggle' | 'text' | 'number';
  /** Description */
  description?: string;
  /** Pour slider */
  min?: number;
  max?: number;
  step?: number;
  /** Pour select */
  options?: Array<string | { value: string; label: string }>;
}

interface SettingsPanelProps {
  /** Définitions des paramètres */
  settings: SettingDefinition[];
  /** Valeurs actuelles */
  values: Record<string, unknown>;
  /** Callback de modification */
  onChange: (values: Record<string, unknown>) => void;
  /** Titre du panneau */
  title?: string;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  values,
  onChange,
  title = 'Paramètres',
}) => {
  const handleChange = (key: string, value: unknown) => {
    onChange({ ...values, [key]: value });
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>

      {settings.map((setting) => (
        <Box key={setting.key} sx={{ mb: 3 }}>
          {setting.type === 'slider' && (
            <Box>
              <Typography variant="body2" gutterBottom>
                {setting.label}: {String(values[setting.key] ?? setting.min ?? 0)}
              </Typography>
              <Slider
                value={Number(values[setting.key] ?? setting.min ?? 0)}
                min={setting.min ?? 0}
                max={setting.max ?? 100}
                step={setting.step ?? 1}
                onChange={(_, val) => handleChange(setting.key, val)}
                valueLabelDisplay="auto"
              />
            </Box>
          )}

          {setting.type === 'select' && (
            <FormControl fullWidth size="small">
              <InputLabel>{setting.label}</InputLabel>
              <Select
                value={String(values[setting.key] ?? '')}
                label={setting.label}
                onChange={(e) => handleChange(setting.key, e.target.value)}
              >
                {(setting.options || []).map((opt) => {
                  const value = typeof opt === 'string' ? opt : opt.value;
                  const label = typeof opt === 'string' ? opt : opt.label;
                  return (
                    <MenuItem key={value} value={value}>
                      {label}
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>
          )}

          {setting.type === 'toggle' && (
            <FormControlLabel
              control={
                <Switch
                  checked={Boolean(values[setting.key])}
                  onChange={(e) => handleChange(setting.key, e.target.checked)}
                />
              }
              label={setting.label}
            />
          )}

          {setting.type === 'text' && (
            <TextField
              fullWidth
              size="small"
              label={setting.label}
              value={String(values[setting.key] ?? '')}
              onChange={(e) => handleChange(setting.key, e.target.value)}
            />
          )}

          {setting.type === 'number' && (
            <TextField
              fullWidth
              size="small"
              type="number"
              label={setting.label}
              value={Number(values[setting.key] ?? 0)}
              onChange={(e) => handleChange(setting.key, Number(e.target.value))}
            />
          )}

          {setting.description && (
            <Typography variant="caption" color="text.secondary">
              {setting.description}
            </Typography>
          )}
        </Box>
      ))}
    </Box>
  );
};
