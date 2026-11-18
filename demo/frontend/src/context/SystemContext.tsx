import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  getApiClient,
  getStoredApiMode,
  getStoredBaseUrl,
  setStoredApiMode,
  setStoredBaseUrl,
} from '../services/api';
import type { ApiClient } from '../services/api/client';
import type { ApiMode, ModelInfo, RuntimeStatus } from '../types/api';

interface SystemContextValue {
  apiMode: ApiMode;
  baseUrl: string;
  apiClient: ApiClient;
  models: ModelInfo[];
  runtime: RuntimeStatus | null;
  isLoadingRuntime: boolean;
  isSwitchingModel: boolean;
  switchModelMessage: string | null;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  setApiMode: (mode: ApiMode) => void;
  setBaseUrl: (url: string) => void;
  refreshRuntime: () => Promise<void>;
  triggerLoadModel: (modelKey: string) => Promise<void>;
}

const SystemContext = createContext<SystemContextValue | null>(null);

export function SystemProvider({ children }: { children: React.ReactNode }) {
  const [apiMode, setApiModeState] = useState<ApiMode>(() => getStoredApiMode());
  const [baseUrl, setBaseUrlState] = useState<string>(() => getStoredBaseUrl());
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [isLoadingRuntime, setIsLoadingRuntime] = useState(false);
  const [isSwitchingModel, setIsSwitchingModel] = useState(false);
  const [switchModelMessage, setSwitchModelMessage] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const apiClient = getApiClient(apiMode);

  const refreshRuntime = useCallback(async () => {
    setIsLoadingRuntime(true);
    try {
      const client = getApiClient(apiMode);
      const [modelsResp, runtimeResp] = await Promise.all([
        client.getModels(),
        client.getRuntime(),
      ]);
      setModels(modelsResp);
      setRuntime(runtimeResp);
    } catch (err) {
      setRuntime((prev) =>
        prev
          ? { ...prev, connected: false, last_error: String(err) }
          : {
              connected: false,
              loaded_model_key: null,
              intended_model_key: null,
              worker_busy: false,
              current_task: null,
              ranking_ready: false,
              last_error: err instanceof Error ? err.message : String(err),
              limits: { max_title_chars: 400, max_abstract_chars: 4000, estimated_max_tokens: 1024 },
            }
      );
    } finally {
      setIsLoadingRuntime(false);
    }
  }, [apiMode]);

  useEffect(() => {
    refreshRuntime();
  }, [refreshRuntime, baseUrl]);

  const setApiMode = useCallback((mode: ApiMode) => {
    setStoredApiMode(mode);
    setApiModeState(mode);
  }, []);

  const setBaseUrl = useCallback((url: string) => {
    setStoredBaseUrl(url);
    setBaseUrlState(url);
  }, []);

  const triggerLoadModel = useCallback(
    async (modelKey: string) => {
      setIsSwitchingModel(true);
      setSwitchModelMessage(`Đang gửi yêu cầu nạp ${modelKey}...`);
      try {
        const client = getApiClient(apiMode);
        const res = await client.loadModel(modelKey);
        setSwitchModelMessage(`Đang nạp ${modelKey}...`);

        // Poll job until finished
        let done = false;
        while (!done) {
          await new Promise((r) => setTimeout(r, 350));
          const job = await client.getJob(res.job_id);
          setSwitchModelMessage(job.stage_label);
          if (job.status === 'completed') {
            done = true;
          } else if (job.status === 'failed') {
            throw new Error(job.error?.message || 'Nạp model thất bại.');
          }
        }
        await refreshRuntime();
      } finally {
        setIsSwitchingModel(false);
        setSwitchModelMessage(null);
      }
    },
    [apiMode, refreshRuntime]
  );

  return (
    <SystemContext.Provider
      value={{
        apiMode,
        baseUrl,
        apiClient,
        models,
        runtime,
        isLoadingRuntime,
        isSwitchingModel,
        switchModelMessage,
        drawerOpen,
        setDrawerOpen,
        setApiMode,
        setBaseUrl,
        refreshRuntime,
        triggerLoadModel,
      }}
    >
      {children}
    </SystemContext.Provider>
  );
}

export function useSystem(): SystemContextValue {
  const ctx = useContext(SystemContext);
  if (!ctx) {
    throw new Error('useSystem must be used inside SystemProvider');
  }
  return ctx;
}
