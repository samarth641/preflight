"use client"

import { createContext, useContext, useState, ReactNode } from "react"

// ─── Types for cached results ───
// Each page stores its result + form state so returning to the page restores everything

interface MLDurationState {
  result: unknown
  formState: unknown
}

interface PreTrainingState {
  result: unknown
  formState: unknown
}

interface DatasetState {
  result: unknown
  formState: unknown
}

interface GPUState {
  result: unknown
  formState: unknown
}

interface PageResultsContextType {
  mlDuration: MLDurationState | null
  preTraining: PreTrainingState | null
  dataset: DatasetState | null
  gpu: GPUState | null
  setMLDuration: (state: MLDurationState) => void
  setPreTraining: (state: PreTrainingState) => void
  setDataset: (state: DatasetState) => void
  setGPU: (state: GPUState) => void
}

const PageResultsContext = createContext<PageResultsContextType | null>(null)

export function PageResultsProvider({ children }: { children: ReactNode }) {
  const [mlDuration, setMLDuration] = useState<MLDurationState | null>(null)
  const [preTraining, setPreTraining] = useState<PreTrainingState | null>(null)
  const [dataset, setDataset] = useState<DatasetState | null>(null)
  const [gpu, setGPU] = useState<GPUState | null>(null)

  return (
    <PageResultsContext.Provider value={{
      mlDuration, preTraining, dataset, gpu,
      setMLDuration, setPreTraining, setDataset, setGPU,
    }}>
      {children}
    </PageResultsContext.Provider>
  )
}

export function usePageResults() {
  const ctx = useContext(PageResultsContext)
  if (!ctx) throw new Error("usePageResults must be used within PageResultsProvider")
  return ctx
}
