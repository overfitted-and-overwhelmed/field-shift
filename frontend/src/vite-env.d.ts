/// <reference types="vite/client" />
interface ImportMetaEnv {
  /** URL of the explorer JSON (scorer API). Default: /data/explorer.json */
  readonly VITE_EXPLORER_DATA_URL?: string;
}
