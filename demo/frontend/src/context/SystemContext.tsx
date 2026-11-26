import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  apiClient,
  getDefaultBaseUrl,
  getStoredBaseUrl,
  setStoredBaseUrl,
} from '../services/api';
import type { ApiClient } from '../services/api/client';
import type {
  ConferenceRankingMethod,
  ModelInfo,
  PaperRankingMethod,
  RuntimeStatus,
} from '../types/api';

export type ExploreEmbeddingModel = 'bert-base' | 'tfidf';

interface SystemContextValue {
  baseUrl: string;
  apiClient: ApiClient;
  models: ModelInfo[];
  runtime: RuntimeStatus | null;
  isLoadingRuntime: boolean;
  isSwitchingModel: boolean;
  switchModelMessage: string | null;
  drawerOpen: boolean;
  exploreEmbedding: ExploreEmbeddingModel;
  setExploreEmbedding: (emb: ExploreEmbeddingModel) => void;
  explorePaperMethod: PaperRankingMethod;
  setExplorePaperMethod: (m: PaperRankingMethod) => void;
  exploreConfMethod: ConferenceRankingMethod;
  setExploreConfMethod: (m: ConferenceRankingMethod) => void;
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
  const [exploreEmbedding, setExploreEmbeddingState] = useState<ExploreEmbeddingModel>(() => {
    const saved = localStorage.getItem('facetrec_explore_embedding');
    return saved === 'tfidf' || saved === 'bert-base' ? saved : 'bert-base';
  });
  const [explorePaperMethod, setExplorePaperMethodState] = useState<PaperRankingMethod>(() => {
    const saved = localStorage.getItem('facetrec_explore_paper_method');
    return saved === 'whole_text' || saved === 'equal_facets' || saved === 'weighted_facets'
      ? saved
      : 'weighted_facets';
  });
  const [exploreConfMethod, setExploreConfMethodState] = useState<ConferenceRankingMethod>(() => {
    const saved = localStorage.getItem('facetrec_explore_conf_method');
    return saved === 'whole_text_knn' || saved === 'flat_facet_knn' || saved === 'gated_knn'
      ? saved
      : 'gated_knn';
  });

  const setExploreEmbedding = useCallback((emb: ExploreEmbeddingModel) => {
    setExploreEmbeddingState(emb);
    localStorage.setItem('facetrec_explore_embedding', emb);
  }, []);

  const setExplorePaperMethod = useCallback((m: PaperRankingMethod) => {
    setExplorePaperMethodState(m);
    localStorage.setItem('facetrec_explore_paper_method', m);
  }, []);

  const setExploreConfMethod = useCallback((m: ConferenceRankingMethod) => {
    setExploreConfMethodState(m);
    localStorage.setItem('facetrec_explore_conf_method', m);
  }, []);

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
        exploreEmbedding,
        setExploreEmbedding,
        explorePaperMethod,
        setExplorePaperMethod,
        exploreConfMethod,
        setExploreConfMethod,
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
