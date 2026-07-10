import { createContext, useContext, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import type { DigitalTwinResult, EvolutionResult, InterventionResult, SelectedEntity, SimulationResult, TwinInterventionScenario } from "./types";
import type { SimulatorTab } from "./SimulatorUI";

const DEFAULT_DISEASE: SelectedEntity = { id: "EFO_0000311", label: "cancer" };
const DEFAULT_GENE: SelectedEntity = { id: "TP53", label: "TP53" };
const DEFAULT_VARIANT: SelectedEntity = { id: "p.R175H", label: "p.R175H", meta: { notation: "p.R175H" } };

type Setter<T> = Dispatch<SetStateAction<T>>;
export type SharedBiologicalContext = {
  diseaseName: string;
  diseaseId: string;
  geneSymbol: string;
  ensemblGeneId: string;
  uniprotAccession: string;
  proteinName: string;
  mutation: string;
  hgvsNotation: string;
  clinvarVariationId: string;
  rsid: string;
  reactomePathwayId: string;
  pathwayName: string;
  patientProfile: Record<string, unknown> | null;
};

const DEFAULT_SHARED_CONTEXT: SharedBiologicalContext = {
  diseaseName: "cancer",
  diseaseId: "EFO_0000311",
  geneSymbol: "TP53",
  ensemblGeneId: "",
  uniprotAccession: "",
  proteinName: "",
  mutation: "p.R175H",
  hgvsNotation: "p.R175H",
  clinvarVariationId: "",
  rsid: "",
  reactomePathwayId: "",
  pathwayName: "",
  patientProfile: null,
};

type SimulationContextValue = {
  activeTab: SimulatorTab; setActiveTab: Setter<SimulatorTab>;
  disease: SelectedEntity | null; setDisease: Setter<SelectedEntity | null>;
  gene: SelectedEntity | null; setGene: Setter<SelectedEntity | null>;
  variant: SelectedEntity | null; setVariant: Setter<SelectedEntity | null>;
  pathway: SelectedEntity | null; setPathway: Setter<SelectedEntity | null>;
  protein: SelectedEntity | null; setProtein: Setter<SelectedEntity | null>;
  sharedContext: SharedBiologicalContext; setSharedContext: Setter<SharedBiologicalContext>;
  steps: number; setSteps: Setter<number>;
  useExternal: boolean; setUseExternal: Setter<boolean>;
  result: SimulationResult | null; setResult: Setter<SimulationResult | null>;
  evolutionResult: EvolutionResult | null; setEvolutionResult: Setter<EvolutionResult | null>;
  personalizedResult: DigitalTwinResult | null; setPersonalizedResult: Setter<DigitalTwinResult | null>;
  interventionScenario: TwinInterventionScenario | null; setInterventionScenario: Setter<TwinInterventionScenario | null>;
  interventionResult: InterventionResult | null; setInterventionResult: Setter<InterventionResult | null>;
};

const SimulationContext = createContext<SimulationContextValue | null>(null);

export function SimulationProvider({ children }: { children: ReactNode }) {
  const [activeTab, setActiveTab] = useState<SimulatorTab>("bioscale");
  const [disease, setDisease] = useState<SelectedEntity | null>(DEFAULT_DISEASE);
  const [gene, setGene] = useState<SelectedEntity | null>(DEFAULT_GENE);
  const [variant, setVariant] = useState<SelectedEntity | null>(DEFAULT_VARIANT);
  const [pathway, setPathway] = useState<SelectedEntity | null>(null);
  const [protein, setProtein] = useState<SelectedEntity | null>(null);
  const [sharedContext, setSharedContext] = useState<SharedBiologicalContext>(DEFAULT_SHARED_CONTEXT);
  const [steps, setSteps] = useState(60);
  const [useExternal, setUseExternal] = useState(true);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [evolutionResult, setEvolutionResult] = useState<EvolutionResult | null>(null);
  const [personalizedResult, setPersonalizedResult] = useState<DigitalTwinResult | null>(null);
  const [interventionScenario, setInterventionScenario] = useState<TwinInterventionScenario | null>(null);
  const [interventionResult, setInterventionResult] = useState<InterventionResult | null>(null);
  return <SimulationContext.Provider value={{ activeTab, setActiveTab, disease, setDisease, gene, setGene, variant, setVariant,
    pathway, setPathway, protein, setProtein, sharedContext, setSharedContext, steps, setSteps, useExternal, setUseExternal,
    result, setResult, evolutionResult, setEvolutionResult, personalizedResult, setPersonalizedResult,
    interventionScenario, setInterventionScenario, interventionResult, setInterventionResult }}>{children}</SimulationContext.Provider>;
}

export function useSimulationContext() {
  const context = useContext(SimulationContext);
  if (!context) throw new Error("useSimulationContext must be used inside SimulationProvider");
  return context;
}
