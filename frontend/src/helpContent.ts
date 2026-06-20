import helpContent from "../../docs/ui-help.json";

export type TooltipHelp = {
  title?: string;
  summary: string;
  details: string[];
  examples: string[];
};

export type PanelHelp = TooltipHelp;
export type FieldHelp = TooltipHelp;

type HelpContent = {
  panels: Record<string, PanelHelp>;
  fields: Record<string, FieldHelp>;
  definitions: Record<string, TooltipHelp>;
  metrics: Record<string, TooltipHelp>;
  mutationKinds: Record<string, TooltipHelp>;
};

type HelpContext = {
  diseaseName?: string;
  diseaseSummary?: string;
  geneSymbol?: string;
  geneSummary?: string;
  mutationNotation?: string;
  mutationKind?: string;
  mutationSpecific?: string;
  mutationSummary?: string;
  clinvarClassification?: string;
  aminoAcidChange?: string;
  proteinName?: string;
  proteinSummary?: string;
  domainHit?: string;
  pathwayName?: string;
  pathwayDescription?: string;
  pathwaySummary?: string;
  selectedPathwayName?: string;
  selectedPathwayId?: string;
  selectedGene?: string;
  nodeId?: string;
  nodeType?: string;
  nodeActivity?: number;
  nodeBaseline?: number;
  nodeDelta?: number;
  value?: number;
  candidateSummary?: string;
  candidateReasons?: string[];
  candidatePathways?: string[];
  candidateInteractions?: string[];
};

type CandidateLike = {
  symbol: string;
  score?: number;
  summary?: string;
  function_summary?: string;
  reasons?: string[];
  pathways?: string[];
  interactions?: string[];
};

const help = helpContent as unknown as HelpContent;

function cloneHelp(base: TooltipHelp): TooltipHelp {
  return {
    title: base.title,
    summary: base.summary,
    details: [...base.details],
    examples: [...base.examples],
  };
}

function combineHelp(base: TooltipHelp, extra: Partial<TooltipHelp> & { details?: string[]; examples?: string[] }): TooltipHelp {
  return {
    title: extra.title ?? base.title,
    summary: extra.summary ?? base.summary,
    details: [...base.details, ...(extra.details ?? [])].filter(Boolean),
    examples: [...base.examples, ...(extra.examples ?? [])].filter(Boolean),
  };
}

function inferMutationKind(text?: string) {
  const value = (text || "").toLowerCase();
  if (!value) return "unknown";
  if (value.includes("fs") || value.includes("frameshift")) return "frameshift";
  if (value.includes("del")) return "deletion";
  if (value.includes("ins")) return "insertion";
  if (value.includes("dup")) return "duplication";
  if (value.includes("splice")) return "splice";
  if (value.includes("stop") || value.includes("*") || value.includes("ter")) return "nonsense";
  if (/^p\.[a-z]\d+[a-z]$/i.test(value) || /^[a-z]\d+[a-z]$/i.test(value)) return "missense";
  if (value.includes("=") || value.includes("synonymous")) return "synonymous";
  if (value.includes("inframe")) return "inframe";
  return "unknown";
}

function percentText(value?: number) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "unknown";
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

export function buildFieldHelp(
  key: keyof HelpContent["fields"],
  context: HelpContext = {},
): FieldHelp {
  const base = cloneHelp(help.fields[key]);
  if (key === "mutation") {
    const kind = inferMutationKind(context.mutationNotation || context.mutationSpecific || context.mutationKind);
    const kindHelp = help.mutationKinds[kind] ?? help.mutationKinds.unknown;
    return combineHelp(base, {
      summary: context.mutationSummary
        ? `You selected ${context.mutationNotation || "this variant"} in ${context.geneSymbol || "the selected gene"}. ${context.mutationSummary}`
        : `You selected ${context.mutationNotation || "this variant"} in ${context.geneSymbol || "the selected gene"}. ${kindHelp.summary}`,
      details: [
        context.mutationNotation ? `Current notation: ${context.mutationNotation}.` : "",
        context.geneSymbol ? `Selected gene: ${context.geneSymbol}.` : "",
        ...kindHelp.details,
      ].filter(Boolean),
      examples: kindHelp.examples,
    });
  }
  if (key === "gene" && context.geneSymbol) {
    return combineHelp(base, {
      summary: context.geneSummary
        ? `You selected ${context.geneSymbol}. ${context.geneSummary}`
        : `You selected ${context.geneSymbol}.`,
      details: [
        context.diseaseName ? `Disease context: ${context.diseaseName}.` : "",
        context.diseaseSummary ? context.diseaseSummary : "",
      ].filter(Boolean),
    });
  }
  if (key === "disease" && context.diseaseName) {
    return combineHelp(base, {
      summary: context.diseaseSummary
        ? `You selected ${context.diseaseName}. ${context.diseaseSummary}`
        : `You selected ${context.diseaseName}.`,
      details: ["This selection sets the biological context for every downstream panel."],
    });
  }
  if (key === "pathway" && context.pathwayName) {
    return combineHelp(base, {
      summary: context.pathwaySummary
        ? `You selected ${context.pathwayName}. ${context.pathwaySummary}`
        : `You selected ${context.pathwayName}.`,
      details: [
        context.selectedPathwayId ? `Selected pathway ID: ${context.selectedPathwayId}.` : "",
        context.pathwayDescription ? context.pathwayDescription : "",
      ].filter(Boolean),
    });
  }
  if (key === "steps") {
    return combineHelp(base, {
      summary: context.value !== undefined
        ? `You selected ${Math.round(context.value)} steps.`
        : base.summary,
      details: context.value !== undefined ? [`The simulation will advance through ${Math.round(context.value)} update cycles.`] : base.details,
    });
  }
  return base;
}

export function buildDefinitionHelp(key: keyof HelpContent["definitions"], context: HelpContext = {}): TooltipHelp {
  const base = cloneHelp(help.definitions[key]);
  if (key === "variant") {
    const kind = inferMutationKind(context.mutationNotation || context.mutationSpecific || context.mutationKind);
    const kindHelp = help.mutationKinds[kind] ?? help.mutationKinds.unknown;
    return combineHelp(base, {
      summary: context.mutationSummary
        ? `You selected ${context.mutationNotation || "this variant"} (${kind}). ${context.mutationSummary}`
        : `You selected ${context.mutationNotation || "this variant"} (${kind}).`,
      details: kindHelp.details,
      examples: kindHelp.examples,
    });
  }
  if (key === "aminoAcidChange" && context.aminoAcidChange) {
    return combineHelp(base, {
      summary: `${context.aminoAcidChange}.`,
      details: context.mutationNotation ? [`Derived from ${context.mutationNotation}.`] : [],
    });
  }
  if (key === "clinvarClassification" && context.clinvarClassification) {
    return combineHelp(base, {
      summary: `You selected ${context.clinvarClassification}.`,
      details: [
        "Pathogenic and likely pathogenic mean stronger disease evidence.",
        "Uncertain significance means the evidence is incomplete.",
        "Benign and likely benign mean the variant is less likely to cause disease.",
      ],
    });
  }
  if (key === "protein") {
    return combineHelp(base, {
      summary: context.proteinName
        ? `You selected ${context.proteinName}. ${context.proteinSummary || ""}`.trim()
        : base.summary,
      details: context.proteinName ? [`This is the protein made by the selected gene.`] : [],
    });
  }
  if (key === "domainHit" && context.domainHit) {
    return combineHelp(base, {
      summary: `The change lands in ${context.domainHit}.`,
      details: ["A domain hit means the mutation touches a functional region that helps the protein do its job."],
    });
  }
  if (key === "selectedReactomePathway" && context.selectedPathwayName) {
    return combineHelp(base, {
      summary: context.pathwayDescription
        ? `You selected ${context.selectedPathwayName}. ${context.pathwayDescription}`
        : `You selected ${context.selectedPathwayName}.`,
      details: context.selectedPathwayId ? [`Reactome ID: ${context.selectedPathwayId}.`] : [],
    });
  }
  if (key === "pathwayNode") {
    return combineHelp(base, {
      summary: context.nodeId
        ? `${context.nodeId.replaceAll("_", " ")} in the pathway graph.`
        : base.summary,
      details: context.nodeType ? [`Node type: ${context.nodeType}.`] : [],
    });
  }
  return base;
}

export function buildMetricHelp(
  key: keyof HelpContent["metrics"],
  value?: number,
  context: HelpContext = {},
): TooltipHelp {
  const base = help.metrics?.[key];
  if (!base) {
    return {
      title: String(key),
      summary: `Normalized score for ${String(key)}.`,
      details: value !== undefined ? [`Current value: ${value.toFixed(2)}.`] : [],
      examples: [],
    };
  }
  const current = typeof value === "number" ? value : context.value;
  const valueLine = typeof current === "number"
    ? `Current value: ${current.toFixed(2)}.`
    : "Current value: not available.";
  const normalizedLine = typeof current === "number"
    ? `The simulator reads that as about ${percentText(current)} of the normalized 0.00 to 1.00 scale.`
    : "This score uses a normalized 0.00 to 1.00 scale.";
  const interpretationMap: Partial<Record<keyof HelpContent["metrics"], string>> = {
    remainingActivity: current !== undefined
      ? `At ${current.toFixed(2)}, the protein keeps ${percentText(current)} of its modeled activity.`
      : "Higher values mean more protein function remains.",
    remainingStability: current !== undefined
      ? `At ${current.toFixed(2)}, the protein keeps ${percentText(current)} of its modeled stability.`
      : "Higher values mean the protein is less likely to misfold.",
    remainingBinding: current !== undefined
      ? `At ${current.toFixed(2)}, the protein keeps ${percentText(current)} of its modeled binding capacity.`
      : "Higher values mean the protein can still bind partners more effectively.",
    lossOfFunctionScore: current !== undefined
      ? `At ${current.toFixed(2)}, the simulator sees a ${percentText(current)} loss-of-function burden.`
      : "Higher values mean a stronger modeled loss of function.",
    proliferation: current !== undefined
      ? `At ${current.toFixed(2)}, the cell is pushed toward ${current >= 0.5 ? "strong" : "weaker"} growth pressure.`
      : "Higher values mean more division pressure.",
    apoptosis: current !== undefined
      ? `At ${current.toFixed(2)}, the cell is pushed toward ${current >= 0.5 ? "more" : "less"} programmed cell death.`
      : "Higher values mean more programmed cell death.",
    repairCapacity: current !== undefined
      ? `At ${current.toFixed(2)}, the cell keeps ${percentText(current)} of its modeled repair ability.`
      : "Higher values mean stronger repair capacity.",
    genomicInstability: current !== undefined
      ? `At ${current.toFixed(2)}, the cell shows ${current >= 0.5 ? "high" : "moderate"} genomic instability.`
      : "Higher values mean more genomic instability.",
    finalMutatedFraction: current !== undefined
      ? `At ${current.toFixed(2)}, roughly ${percentText(current)} of the simulated population is mutated.`
      : "Higher values mean more of the population is mutated.",
    clonalExpansionScore: current !== undefined
      ? `At ${current.toFixed(2)}, the mutated clone is expanding ${current >= 0.5 ? "strongly" : "modestly"}.`
      : "Higher values mean faster clonal expansion.",
    tumorLikeBurden: current !== undefined
      ? `At ${current.toFixed(2)}, the tissue carries ${current >= 0.5 ? "a strong" : "a moderate"} disease burden.`
      : "Higher values mean more disease burden.",
    immuneClearance: current !== undefined
      ? `At ${current.toFixed(2)}, the immune system is clearing ${current >= 0.5 ? "more" : "less"} of the burden.`
      : "Higher values mean stronger immune clearance.",
    inflammation: current !== undefined
      ? `At ${current.toFixed(2)}, inflammatory pressure is ${current >= 0.5 ? "high" : "moderate"}.`
      : "Higher values mean more inflammation.",
    ecosystemRisk: current !== undefined
      ? `At ${current.toFixed(2)}, the broader tissue environment is at ${current >= 0.5 ? "higher" : "moderate"} risk.`
      : "Higher values mean a higher ecosystem risk.",
  };
  return {
    title: base.title,
    summary: interpretationMap[key] ?? valueLine,
    details: [valueLine, normalizedLine, interpretationMap[key] ? "" : base.summary].filter(Boolean),
    examples: [],
  };
}

export function buildCandidateHelp(candidate: CandidateLike, diseaseName?: string): TooltipHelp {
  const geneFunction = candidate.function_summary || candidate.summary || `${candidate.symbol} is a disease-linked gene in this simulation.`;
  const diseaseContext = diseaseName ? ` In the context of ${diseaseName}, this gene is ranked because its biology matches the disease pattern.` : "";
  const base = {
    title: candidate.symbol,
    summary: `${geneFunction}${diseaseContext}`,
    details: [] as string[],
    examples: [] as string[],
  };
  const details = [
    candidate.reasons?.length ? `Evidence used for ranking: ${candidate.reasons[0]}` : "",
    candidate.reasons?.length && candidate.reasons.length > 1 ? `Additional evidence: ${candidate.reasons.slice(1, 3).join("; ")}` : "",
    candidate.pathways?.length ? `Linked pathways: ${candidate.pathways.slice(0, 3).join(", ")}.` : "",
    candidate.interactions?.length ? `Known interactions: ${candidate.interactions.slice(0, 3).join(", ")}.` : "",
    diseaseName ? `Shown in the context of ${diseaseName}.` : "",
  ].filter(Boolean);
  return { ...base, details, examples: [] };
}

export function buildPathwayNodeHelp(
  nodeId: string,
  nodeType: string,
  pathwayName?: string,
  geneSymbol?: string,
  geneSummary?: string,
  nodeActivity?: number,
  nodeBaseline?: number,
  nodeDelta?: number,
): TooltipHelp {
  const isGene = geneSymbol && nodeId === geneSymbol;
  const displayName = nodeId.replaceAll("_", " ");
  const direction = typeof nodeDelta === "number"
    ? nodeDelta > 0.1
      ? "up"
      : nodeDelta < -0.1
        ? "down"
        : "stable"
    : "stable";
  const current = typeof nodeActivity === "number" ? nodeActivity.toFixed(2) : "unknown";
  const baselineText = typeof nodeBaseline === "number" ? nodeBaseline.toFixed(2) : "unknown";
  const effectLine = isGene && geneSummary
    ? geneSummary
    : `${displayName} is a ${nodeType.replaceAll("_", " ")} node in this pathway.`;
  const stateLine = `Current activity is ${current}${typeof nodeDelta === "number" ? `, change ${nodeDelta >= 0 ? "+" : ""}${nodeDelta.toFixed(2)} (${direction})` : ""} from a baseline of ${baselineText}.`;
  const roleLine = isGene
    ? "This node is the main molecular target, so its activity shapes the rest of the pathway."
    : nodeType === "process"
      ? "This node summarizes a downstream biological step, so changes here affect the next stage in the pathway."
      : nodeType === "pathway"
        ? "This node acts as a pathway bridge that passes the signal onward."
        : "This node carries signal through the pathway graph.";
  const scopeLine = pathwayName ? `Pathway context: ${pathwayName}.` : "";
  return {
    title: displayName,
    summary: effectLine,
    details: [stateLine, roleLine, scopeLine].filter(Boolean),
    examples: [],
  };
}

export function buildScoreLabelHelp(label: string, value?: number, context: HelpContext = {}): TooltipHelp {
  const keyMap: Record<string, keyof HelpContent["definitions"] | keyof HelpContent["metrics"]> = {
    "Remaining activity": "remainingActivity",
    "Remaining stability": "remainingStability",
    "Remaining binding": "remainingBinding",
    "Loss-of-function score": "lossOfFunctionScore",
    "Loss-of-function": "lossOfFunctionScore",
    "Proliferation": "proliferation",
    "Apoptosis": "apoptosis",
    "Repair capacity": "repairCapacity",
    "Genomic instability": "genomicInstability",
    "Final mutated fraction": "finalMutatedFraction",
    "Clonal expansion score": "clonalExpansionScore",
    "Tumor-like burden": "tumorLikeBurden",
    "Immune clearance": "immuneClearance",
    "Inflammation": "inflammation",
    "Ecosystem risk": "ecosystemRisk",
  };
  const key = keyMap[label];
  if (!key) {
    return {
      title: label,
      summary: label,
      details: [],
      examples: [],
    };
  }
  if (help.metrics && key in help.metrics) {
    return buildMetricHelp(key as keyof HelpContent["metrics"], value, context);
  }
  return buildDefinitionHelp(key as keyof HelpContent["definitions"], context);
}

export { help };
