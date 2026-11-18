import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  apiClient,
  getDefaultBaseUrl,
  getStoredBaseUrl,
  setStoredBaseUrl,
} from '../services/api';
import type { ApiClient } from '../services/api/client';
import type { ModelInfo, RuntimeStatus } from '../types/api';

interface SystemContextValue {
  baseUrl: string;
  apiClient: ApiClient;
  models: ModelInfo[];
  runtime: RuntimeStatus | null;
  isLoadingRuntime: boolean;
  isSwitchingModel: boolean;
  switchModelMessage: string | null;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  setBaseUrl: (url: string) => void;
  resetBaseUrl: () => void;
  refreshRuntime: () => Promise<void>;
  triggerLoadModel: (modelKey: string) => Promise<void>;
}

const SystemContext = createContext<SystemContextValue | null>(null);

export function SystemProvider({ children }: { children: React.ReactNode }) {
  const [baseUrl, setBaseUrlState] = useState<string>(() => getStoredBaseUrl());
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [isLoadingRuntime, setIsLoadingRuntime] = useState(false);
  const [isSwitchingModel, setIsSwitchingModel] = useState(false);
  const [switchModelMessage, setSwitchModelMessage] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const refreshRuntime = useCallback(async () => {
    setIsLoadingRuntime(true);
    try {
      const [modelsResp, runtimeResp] = await Promise.all([
        apiClient.getModels(),
        apiClient.getRuntime(),
      ]);
      setModels(modelsResp);
      setRuntime(runtimeResp);
    } catch (err) {
      setModels([]);
      setRuntime({
        connected: false,
        loaded_model_key: null,
        intended_model_key: null,
        worker_busy: false,
        current_task: null,
        ranking_ready: false,
        last_error: err instanceof Error ? err.message : String(err),
        limits: {
          max_title_chars: 400,
          max_abstract_chars: 4000,
          estimated_max_tokens: 1024,
        },
      });
    } finally {
      setIsLoadingRuntime(false);
    }
  }, []);

  useEffect(() => {
    refreshRuntime();
  }, [refreshRuntime, baseUrl]);

  const setBaseUrl = useCallback((url: string) => {
    setStoredBaseUrl(url);
    setBaseUrlState(url);
  }, []);

  const resetBaseUrl = useCallback(() => {
    const def = getDefaultBaseUrl();
    setStoredBaseUrl(def);
    setBaseUrlState(def);
  }, []);

  const triggerLoadModel = useCallback(
    async (modelKey: string) => {
      setIsSwitchingModel(true);
      setSwitchModelMessage(`Đang gửi yêu cầu nạp ${modelKey}...`);
      try {
        const res = await apiClient.loadModel(modelKey);
        setSwitchModelMessage(`Đang nạp ${modelKey}...`);

        let done = false;
        while (!done) {
          await new Promise((r) => setTimeout(r, 500));
          const job = await apiClient.getJob(res.job_id);
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
    [refreshRuntime]
  );

  return (
    <SystemContext.Provider
      value={{
        baseUrl,
        apiClient,
        models,
        runtime,
        isLoadingRuntime,
        isSwitchingModel,
        switchModelMessage,
        drawerOpen,
        setDrawerOpen,
        setBaseUrl,
        resetBaseUrl,
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
