import type { ApiMode } from '../../types/api';
import type { ApiClient } from './client';
import { HttpApiClient } from './httpClient';
import { MockApiClient } from './mockClient';

const STORAGE_MODE_KEY = 'ds300_api_mode';
const STORAGE_URL_KEY = 'ds300_api_base_url';

export function getStoredApiMode(): ApiMode {
  const saved = localStorage.getItem(STORAGE_MODE_KEY);
  if (saved === 'mock' || saved === 'http') return saved;
  const envMode = import.meta.env.VITE_API_MODE;
  return envMode === 'http' ? 'http' : 'mock';
}

export function setStoredApiMode(mode: ApiMode): void {
  localStorage.setItem(STORAGE_MODE_KEY, mode);
}

export function getStoredBaseUrl(): string {
  const saved = localStorage.getItem(STORAGE_URL_KEY);
  if (saved) return saved;
  return import.meta.env.VITE_API_BASE_URL || '/api/v1';
}

export function setStoredBaseUrl(url: string): void {
  localStorage.setItem(STORAGE_URL_KEY, url);
}

const mockClient = new MockApiClient();
const httpClient = new HttpApiClient(() => getStoredBaseUrl());

export function getApiClient(mode?: ApiMode): ApiClient {
  const activeMode = mode || getStoredApiMode();
  return activeMode === 'http' ? httpClient : mockClient;
}
