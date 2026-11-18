import type { ApiClient } from './client';
import { HttpApiClient } from './httpClient';

const STORAGE_URL_KEY = 'ds300_api_base_url';

export function getDefaultBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || '/api/v1';
}

export function getStoredBaseUrl(): string {
  const saved = localStorage.getItem(STORAGE_URL_KEY);
  if (saved) return saved;
  return getDefaultBaseUrl();
}

export function setStoredBaseUrl(url: string): void {
  localStorage.setItem(STORAGE_URL_KEY, url);
}

export const apiClient: ApiClient = new HttpApiClient(() => getStoredBaseUrl());
