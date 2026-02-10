/**
 * DataTable — Tableau de données pour les agents.
 *
 * Wrapper autour de MUI qui fournit une API simplifiée.
 *
 * Usage:
 *   import { DataTable } from '@framework/components';
 *   <DataTable
 *     columns={[
 *       { key: 'name', label: 'Nom' },
 *       { key: 'email', label: 'Email' },
 *     ]}
 *     rows={data}
 *   />
 */

import React from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

interface Column {
  /** Clé dans l'objet row */
  key: string;
  /** Label affiché dans le header */
  label: string;
  /** Largeur optionnelle */
  width?: number | string;
  /** Alignement */
  align?: 'left' | 'center' | 'right';
  /** Render custom */
  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
}

interface DataTableProps {
  /** Définition des colonnes */
  columns: Column[];
  /** Données du tableau */
  rows: Record<string, unknown>[];
  /** Message si vide */
  emptyMessage?: string;
  /** Taille compacte */
  dense?: boolean;
}

export const DataTable: React.FC<DataTableProps> = ({
  columns,
  rows,
  emptyMessage = 'Aucune donnée',
  dense = false,
}) => {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size={dense ? 'small' : 'medium'}>
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell
                key={col.key}
                align={col.align || 'left'}
                sx={{ fontWeight: 'bold', width: col.width }}
              >
                {col.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} align="center">
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  {emptyMessage}
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row, index) => (
              <TableRow key={index} hover>
                {columns.map((col) => (
                  <TableCell key={col.key} align={col.align || 'left'}>
                    {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? '')}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};
