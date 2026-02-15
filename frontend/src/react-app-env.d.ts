/// <reference types="react-scripts" />

// Webpack require.context — used by agents/registry.ts for auto-discovery
interface WebpackRequireContext {
  keys(): string[];
  <T>(id: string): T;
  resolve(id: string): string;
  id: string;
}

interface NodeRequire {
  context(
    directory: string,
    useSubdirectories?: boolean,
    regExp?: RegExp,
    mode?: string,
  ): WebpackRequireContext;
}
