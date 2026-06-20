import { useEffect, useMemo, useState } from "react";
import type { SimulationResult } from "./types";
import { InfoTooltip } from "./Help";
import { buildScoreLabelHelp } from "./helpContent";

type ProteinEffectResult = SimulationResult["protein_effect"];
type CellPhenotypeResult = SimulationResult["cell_phenotype"];
type PopulationResult = SimulationResult["population_result"];
type EcosystemResult = SimulationResult["ecosystem_result"];

export type CardViewMode = "summary" | "visual";
export type VisualCardKey = "protein" | "cell" | "population" | "ecosystem";

type CardTabBarProps = {
  value: CardViewMode;
  onChange: (value: CardViewMode) => void;
  visualLabel?: string;
};

export function CardTabBar({ value, onChange, visualLabel = "Visual" }: CardTabBarProps) {
  return (
    <div className="cardTabs" role="tablist" aria-label="Card view modes">
      <button
        type="button"
        role="tab"
        aria-selected={value === "summary"}
        className={value === "summary" ? "cardTabButton active" : "cardTabButton"}
        onClick={() => onChange("summary")}
      >
        Summary
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === "visual"}
        className={value === "visual" ? "cardTabButton active" : "cardTabButton"}
        onClick={() => onChange("visual")}
      >
        {visualLabel}
      </button>
    </div>
  );
}

function fmt(value: number) {
  return Number.isFinite(value) ? value.toFixed(2) : "—";
}

function parsePosition(text?: string) {
  if (!text) return null;
  const match = text.match(/(\d+)/);
  return match ? Number(match[1]) : null;
}

function rangeLabel(value: number) {
  if (value >= 0.75) return "high";
  if (value >= 0.45) return "moderate";
  return "low";
}

type CellOrganelle = {
  id: string;
  label: string;
  x: number;
  y: number;
  r: number;
  color: string;
  description: string;
  emphasis: number;
};

type EcosystemZone = {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
  description: string;
  emphasis: number;
};

function inferTissueSite(diseaseName?: string) {
  const text = (diseaseName || "").toLowerCase();
  if (text.includes("liver") || text.includes("hepatic")) {
    return {
      sceneKey: "abdomen",
      sceneTitle: "Abdominal disease site",
      organ: "liver",
      tissue: "hepatic tissue",
      bodyPart: "right upper abdomen",
      context: "hepatocyte and biliary microenvironment",
      corridor: "portal vein, biliary tree, and adjacent hepatic tissue",
      affectedAreas: ["liver", "portal vein", "biliary tree", "adjacent hepatic tissue"],
    };
  }
  if (text.includes("hereditary nonpolyposis colon cancer") || text.includes("lynch") || text.includes("mismatch repair")) {
    return {
      sceneKey: "multisite",
      sceneTitle: "Multi-site disease map",
      organ: "multiple sites",
      tissue: "multi-organ mismatch-repair tissue",
      bodyPart: "colon, endometrium, ovary, stomach, and urinary tract",
      context: "multi-organ cancer predisposition microenvironment",
      corridor: "mucosal and glandular tissues across the body",
      affectedAreas: ["colon", "endometrium", "ovary", "stomach", "urinary tract"],
    };
  }
  if (text.includes("ovarian")) {
    return {
      sceneKey: "pelvis",
      sceneTitle: "Pelvic disease site",
      organ: "ovary",
      tissue: "epithelial ovarian tissue",
      bodyPart: "pelvis",
      context: "hormone-responsive epithelial microenvironment",
      corridor: "pelvic peritoneum and nearby lymphatic channels",
      affectedAreas: ["ovary", "pelvic peritoneum", "lymphatic channels"],
    };
  }
  if (text.includes("breast") || text.includes("mammary")) {
    return {
      sceneKey: "chest",
      sceneTitle: "Chest disease site",
      organ: "breast",
      tissue: "mammary epithelium",
      bodyPart: "chest wall",
      context: "ductal/lobular tissue microenvironment",
      corridor: "adjacent stroma and regional lymph nodes",
      affectedAreas: ["breast ducts and lobules", "chest wall", "regional lymph nodes"],
    };
  }
  if (text.includes("colon") || text.includes("colorectal") || text.includes("bowel") || text.includes("intestinal")) {
    return {
      sceneKey: "abdomen",
      sceneTitle: "Abdominal disease site",
      organ: "colon",
      tissue: "colonic epithelium",
      bodyPart: "abdomen",
      context: "gastrointestinal epithelial niche",
      corridor: "mucosa, submucosa, and mesenteric vessels",
      affectedAreas: ["colon", "mucosa", "submucosa", "mesenteric vessels"],
    };
  }
  if (text.includes("lung") || text.includes("pulmonary")) {
    return {
      sceneKey: "thorax",
      sceneTitle: "Thoracic disease site",
      organ: "lung",
      tissue: "alveolar/bronchial tissue",
      bodyPart: "thorax",
      context: "airway and alveolar microenvironment",
      corridor: "bronchial tissue, pleura, and vasculature",
      affectedAreas: ["lung", "bronchial tissue", "pleura", "vasculature"],
    };
  }
  if (text.includes("prostate")) {
    return {
      sceneKey: "pelvis",
      sceneTitle: "Pelvic disease site",
      organ: "prostate",
      tissue: "glandular prostate tissue",
      bodyPart: "pelvis",
      context: "glandular stromal microenvironment",
      corridor: "stromal tissue and surrounding vasculature",
      affectedAreas: ["prostate", "pelvic tissue", "surrounding vasculature"],
    };
  }
  if (text.includes("brain") || text.includes("gli") || text.includes("neuro") || text.includes("alzheimer") || text.includes("parkinson")) {
    return {
      sceneKey: "head",
      sceneTitle: "Neural disease site",
      organ: "brain",
      tissue: "neural tissue",
      bodyPart: "central nervous system",
      context: "neuronal and glial microenvironment",
      corridor: "neurons, glia, and blood-brain barrier",
      affectedAreas: ["brain", "cortex", "meninges", "blood-brain barrier"],
    };
  }
  if (text.includes("skin") || text.includes("melanoma")) {
    return {
      sceneKey: "skin",
      sceneTitle: "Surface disease site",
      organ: "skin",
      tissue: "epidermal tissue",
      bodyPart: "skin",
      context: "epidermal and dermal interface",
      corridor: "epidermis, dermis, and local vasculature",
      affectedAreas: ["epidermis", "dermis", "subcutis", "local vasculature"],
    };
  }
  return {
    sceneKey: "generic",
    sceneTitle: "Selected site",
    organ: "tissue",
    tissue: "selected disease tissue",
    bodyPart: "selected site",
    context: "disease-specific local microenvironment",
    corridor: "adjacent tissue and vasculature",
    affectedAreas: ["selected tissue", "adjacent tissue", "vasculature", "immune boundary"],
  };
}

type EcosystemArea = {
  id: string;
  label: string;
  value: number;
  description: string;
  emphasis: number;
  kind: "rect" | "ellipse";
  x: number;
  y: number;
  w: number;
  h: number;
  tone: string;
  accent: string;
};

type EcosystemScene = {
  key: string;
  title: string;
  subtitle: string;
  bodyLabel: string;
  bodyNote: string;
  axes: string[];
  areas: EcosystemArea[];
};

function ecosystemMetricSeries(ecosystem: EcosystemResult) {
  return [
    ecosystem.tumor_like_burden,
    ecosystem.inflammation,
    ecosystem.immune_clearance,
    ecosystem.nutrient_stress,
    ecosystem.ecosystem_risk_score,
  ];
}

function multiSiteAreas(labels: string[], ecosystem: EcosystemResult): EcosystemArea[] {
  const metrics = ecosystemMetricSeries(ecosystem);
  const placements = [
    { x: 126, y: 40, w: 156, h: 40, tone: "#d8eee2", accent: "#237457" },
    { x: 96, y: 100, w: 216, h: 40, tone: "#cfe1d5", accent: "#9fcbb8" },
    { x: 114, y: 160, w: 182, h: 40, tone: "#d9e4f4", accent: "#8aa8cf" },
    { x: 84, y: 220, w: 132, h: 40, tone: "#ead9a8", accent: "#b89443" },
    { x: 228, y: 220, w: 132, h: 40, tone: "#f0d6d2", accent: "#c84d4d" },
    { x: 138, y: 280, w: 150, h: 34, tone: "#edf7f1", accent: "#9fcbb8" },
  ];

  return labels.map((label, index) => {
    const placement = placements[index % placements.length];
    const value = metrics[index % metrics.length];
    return {
      id: label.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
      label,
      value,
      description: `${label} is one of the involved body sites in this disease pattern.`,
      emphasis: value,
      kind: "rect",
      x: placement.x,
      y: placement.y,
      w: placement.w,
      h: placement.h,
      tone: placement.tone,
      accent: placement.accent,
    };
  });
}

function buildEcosystemScene(site: ReturnType<typeof inferTissueSite>, ecosystem: EcosystemResult): EcosystemScene {
  const common = {
    subtitle: `${site.organ} in the ${site.bodyPart}`,
    bodyNote: `${site.context}. ${site.corridor}.`,
  };

  if (site.sceneKey === "multisite") {
    const areas = multiSiteAreas(site.affectedAreas || [site.organ], ecosystem);
    return {
      key: site.sceneKey,
      title: "Multi-site disease map",
      subtitle: `${site.affectedAreas?.join(" · ") || site.organ}`,
      bodyLabel: "multiple affected body sites",
      bodyNote: `The disease involves several linked body sites: ${site.affectedAreas?.join(", ") || site.organ}.`,
      axes: site.affectedAreas || [site.organ],
      areas,
    };
  }

  if (site.sceneKey === "head") {
    return {
      key: site.sceneKey,
      title: "Neural body site",
      subtitle: common.subtitle,
      bodyLabel: "brain and surrounding neural tissue",
      bodyNote: common.bodyNote,
      axes: ["brain", "ventricles", "meninges", "blood-brain barrier", "adjacent cortex"],
      areas: [
        {
          id: "lesion",
          label: "Primary neural lesion",
          value: ecosystem.tumor_like_burden,
          description: `The main altered focus in the ${site.tissue}.`,
          emphasis: ecosystem.tumor_like_burden,
          kind: "ellipse",
          x: 145,
          y: 84,
          w: 118,
          h: 118,
          tone: "#d8eee2",
          accent: "#237457",
        },
        {
          id: "cortex",
          label: "Cortex",
          value: ecosystem.inflammation,
          description: "Nearby cortex where signaling and structure are shifted by the lesion.",
          emphasis: ecosystem.inflammation,
          kind: "ellipse",
          x: 114,
          y: 128,
          w: 180,
          h: 86,
          tone: "#cfe1d5",
          accent: "#9fcbb8",
        },
        {
          id: "barrier",
          label: "Blood-brain barrier",
          value: ecosystem.immune_clearance,
          description: "Barrier behavior that limits or permits immune access.",
          emphasis: ecosystem.immune_clearance,
          kind: "rect",
          x: 82,
          y: 248,
          w: 252,
          h: 40,
          tone: "#d9e4f4",
          accent: "#8aa8cf",
        },
        {
          id: "meninges",
          label: "Meninges",
          value: ecosystem.inflammation,
          description: "Protective covering surrounding the central nervous system.",
          emphasis: ecosystem.inflammation,
          kind: "rect",
          x: 60,
          y: 286,
          w: 300,
          h: 34,
          tone: "#f0d6d2",
          accent: "#c84d4d",
        },
      ],
    };
  }

  if (site.sceneKey === "thorax") {
    return {
      key: site.sceneKey,
      title: "Thoracic body site",
      subtitle: common.subtitle,
      bodyLabel: "chest, lungs, and nearby tissue",
      bodyNote: common.bodyNote,
      axes: ["left lung", "primary site", "right lung", "pleura", "regional nodes"],
      areas: [
        {
          id: "left-lung",
          label: "Left lung",
          value: ecosystem.immune_clearance,
          description: "One lung field affected by mass effect and inflammatory pressure.",
          emphasis: ecosystem.immune_clearance,
          kind: "ellipse",
          x: 82,
          y: 70,
          w: 132,
          h: 198,
          tone: "#d9e4f4",
          accent: "#8aa8cf",
        },
        {
          id: "primary",
          label: `${site.organ} lesion`,
          value: ecosystem.tumor_like_burden,
          description: `The disease focus in ${site.tissue}.`,
          emphasis: ecosystem.tumor_like_burden,
          kind: "ellipse",
          x: 180,
          y: 104,
          w: 110,
          h: 144,
          tone: "#d8eee2",
          accent: "#237457",
        },
        {
          id: "pleura",
          label: "Pleura",
          value: ecosystem.inflammation,
          description: "Surface tissues around the lung where irritation is visible.",
          emphasis: ecosystem.inflammation,
          kind: "ellipse",
          x: 46,
          y: 58,
          w: 262,
          h: 222,
          tone: "#f0d6d2",
          accent: "#c84d4d",
        },
        {
          id: "nodes",
          label: "Regional nodes",
          value: ecosystem.ecosystem_risk_score,
          description: "Nearby lymphatic drainage that can be recruited or suppressed.",
          emphasis: ecosystem.ecosystem_risk_score,
          kind: "rect",
          x: 104,
          y: 272,
          w: 168,
          h: 36,
          tone: "#ead9a8",
          accent: "#b89443",
        },
      ],
    };
  }

  if (site.sceneKey === "pelvis") {
    return {
      key: site.sceneKey,
      title: "Pelvic body site",
      subtitle: common.subtitle,
      bodyLabel: `${site.organ} and pelvic surroundings`,
      bodyNote: common.bodyNote,
      axes: ["primary site", "bladder", "pelvic wall", "peritoneum", "lymphatics"],
      areas: [
        {
          id: "primary",
          label: `${site.organ} lesion`,
          value: ecosystem.tumor_like_burden,
          description: `The altered focus in the ${site.tissue}.`,
          emphasis: ecosystem.tumor_like_burden,
          kind: "ellipse",
          x: 154,
          y: 164,
          w: 112,
          h: 102,
          tone: "#d8eee2",
          accent: "#237457",
        },
        {
          id: "pelvic-wall",
          label: "Pelvic wall",
          value: ecosystem.inflammation,
          description: "Supporting tissue around the lesion where swelling and restriction appear.",
          emphasis: ecosystem.inflammation,
          kind: "rect",
          x: 72,
          y: 120,
          w: 250,
          h: 72,
          tone: "#cfe1d5",
          accent: "#9fcbb8",
        },
        {
          id: "bladder",
          label: "Bladder / adjacent organ",
          value: ecosystem.immune_clearance,
          description: "Nearby organ interface that helps show local spread boundaries.",
          emphasis: ecosystem.immune_clearance,
          kind: "ellipse",
          x: 104,
          y: 58,
          w: 172,
          h: 90,
          tone: "#d9e4f4",
          accent: "#8aa8cf",
        },
        {
          id: "lymphatics",
          label: "Lymphatics",
          value: ecosystem.ecosystem_risk_score,
          description: "Channels that reflect local spread potential.",
          emphasis: ecosystem.ecosystem_risk_score,
          kind: "rect",
          x: 116,
          y: 276,
          w: 144,
          h: 34,
          tone: "#f0d6d2",
          accent: "#c84d4d",
        },
      ],
    };
  }

  if (site.sceneKey === "skin") {
    return {
      key: site.sceneKey,
      title: "Cutaneous body site",
      subtitle: common.subtitle,
      bodyLabel: "skin layers and adjacent tissue",
      bodyNote: common.bodyNote,
      axes: ["epidermis", "dermis", "subcutis", "vessels", "immune front"],
      areas: [
        {
          id: "epidermis",
          label: "Epidermis",
          value: ecosystem.inflammation,
          description: "Surface layer where visible change and irritation first appear.",
          emphasis: ecosystem.inflammation,
          kind: "rect",
          x: 58,
          y: 80,
          w: 292,
          h: 38,
          tone: "#d9e4f4",
          accent: "#8aa8cf",
        },
        {
          id: "lesion",
          label: `${site.organ} lesion`,
          value: ecosystem.tumor_like_burden,
          description: "The visible focus of disease in the affected skin.",
          emphasis: ecosystem.tumor_like_burden,
          kind: "ellipse",
          x: 118,
          y: 124,
          w: 136,
          h: 90,
          tone: "#d8eee2",
          accent: "#237457",
        },
        {
          id: "dermis",
          label: "Dermis",
          value: ecosystem.immune_clearance,
          description: "Support layer that contains vessels and immune traffic.",
          emphasis: ecosystem.immune_clearance,
          kind: "rect",
          x: 58,
          y: 214,
          w: 292,
          h: 52,
          tone: "#cfe1d5",
          accent: "#9fcbb8",
        },
        {
          id: "subcutis",
          label: "Subcutis",
          value: ecosystem.ecosystem_risk_score,
          description: "Deeper tissue that can be engaged as disease extends.",
          emphasis: ecosystem.ecosystem_risk_score,
          kind: "rect",
          x: 58,
          y: 274,
          w: 292,
          h: 36,
          tone: "#ead9a8",
          accent: "#b89443",
        },
      ],
    };
  }

  if (site.sceneKey === "abdomen") {
    return {
      key: site.sceneKey,
      title: "Abdominal body site",
      subtitle: common.subtitle,
      bodyLabel: `${site.organ} and surrounding abdominal tissue`,
      bodyNote: common.bodyNote,
      axes: ["primary site", "liver / bowel", "stroma", "portal flow", "adjacent tissue"],
      areas: [
        {
          id: "primary",
          label: `${site.organ} lesion`,
          value: ecosystem.tumor_like_burden,
          description: `The main disease focus in ${site.tissue}.`,
          emphasis: ecosystem.tumor_like_burden,
          kind: "ellipse",
          x: 170,
          y: 104,
          w: 120,
          h: 96,
          tone: "#d8eee2",
          accent: "#237457",
        },
        {
          id: "adjacent",
          label: "Adjacent tissue",
          value: ecosystem.inflammation,
          description: "Nearby tissue that changes as the lesion grows or invades.",
          emphasis: ecosystem.inflammation,
          kind: "rect",
          x: 68,
          y: 76,
          w: 244,
          h: 160,
          tone: "#cfe1d5",
          accent: "#9fcbb8",
        },
        {
          id: "vessels",
          label: "Portal / vascular flow",
          value: ecosystem.nutrient_stress,
          description: "Blood supply and nutrient delivery around the lesion.",
          emphasis: ecosystem.nutrient_stress,
          kind: "rect",
          x: 74,
          y: 248,
          w: 236,
          h: 42,
          tone: "#ead9a8",
          accent: "#b89443",
        },
        {
          id: "corridor",
          label: "Spread corridor",
          value: ecosystem.ecosystem_risk_score,
          description: `Route through ${site.corridor}.`,
          emphasis: ecosystem.ecosystem_risk_score,
          kind: "ellipse",
          x: 214,
          y: 214,
          w: 112,
          h: 82,
          tone: "#f0d6d2",
          accent: "#c84d4d",
        },
      ],
    };
  }

  return {
    key: site.sceneKey,
    title: "Selected site",
    subtitle: common.subtitle,
    bodyLabel: site.bodyPart,
    bodyNote: common.bodyNote,
    axes: ["lesion", "neighboring tissue", "vascular context", "immune boundary"],
    areas: [
      {
        id: "primary",
        label: `${site.organ} lesion`,
        value: ecosystem.tumor_like_burden,
        description: `The local disease focus in the selected tissue.`,
        emphasis: ecosystem.tumor_like_burden,
        kind: "ellipse",
        x: 148,
        y: 108,
        w: 120,
        h: 102,
        tone: "#d8eee2",
        accent: "#237457",
      },
      {
        id: "neighbor",
        label: "Neighboring tissue",
        value: ecosystem.inflammation,
        description: "Nearby tissue that is being affected around the lesion.",
        emphasis: ecosystem.inflammation,
        kind: "rect",
        x: 76,
        y: 76,
        w: 236,
        h: 144,
        tone: "#cfe1d5",
        accent: "#9fcbb8",
      },
      {
        id: "immune",
        label: "Immune boundary",
        value: ecosystem.immune_clearance,
        description: "The immune front that can suppress or contain spread.",
        emphasis: ecosystem.immune_clearance,
        kind: "rect",
        x: 70,
        y: 242,
        w: 248,
        h: 40,
        tone: "#d9e4f4",
        accent: "#8aa8cf",
      },
      {
        id: "stress",
        label: "Vascular stress",
        value: ecosystem.nutrient_stress,
        description: "Nutrient and oxygen delivery in the surrounding region.",
        emphasis: ecosystem.nutrient_stress,
        kind: "ellipse",
        x: 204,
        y: 224,
        w: 108,
        h: 82,
        tone: "#ead9a8",
        accent: "#b89443",
      },
    ],
  };
}

function EcosystemBackdrop({ sceneKey }: { sceneKey: string }) {
  if (sceneKey === "multisite") {
    return (
      <>
        <ellipse cx="202" cy="80" rx="44" ry="52" className="ecosystemBodyOutline" />
        <path d="M142 118 C 154 92, 176 78, 202 78 C 228 78, 250 92, 262 118 L 280 230 C 248 260, 224 276, 202 276 C 180 276, 156 260, 124 230 Z" className="ecosystemBodyOutline" />
        <path d="M136 230 C 150 266, 174 288, 202 288 C 230 288, 254 266, 268 230 L 284 292 C 248 312, 226 322, 202 322 C 178 322, 156 312, 120 292 Z" className="ecosystemBodyOutlineSoft" />
        <ellipse cx="202" cy="128" rx="68" ry="26" className="ecosystemBackdropOrgan" />
        <ellipse cx="202" cy="188" rx="78" ry="32" className="ecosystemBackdropLayer" />
        <ellipse cx="174" cy="236" rx="34" ry="22" className="ecosystemBackdropOrgan" />
        <ellipse cx="230" cy="236" rx="34" ry="22" className="ecosystemBackdropOrgan" />
        <rect x="184" y="244" width="36" height="42" rx="16" className="ecosystemBackdropLayer" />
      </>
    );
  }

  if (sceneKey === "head") {
    return (
      <>
        <ellipse cx="202" cy="152" rx="106" ry="124" className="ecosystemBodyOutline" />
        <path d="M148 246 C 156 276, 174 292, 202 292 C 230 292, 248 276, 256 246" className="ecosystemBodyOutlineSoft" />
        <ellipse cx="202" cy="150" rx="74" ry="66" className="ecosystemBackdropOrgan" />
        <path d="M144 152 C 144 118, 162 100, 202 100 C 242 100, 260 118, 260 152 C 260 188, 242 206, 202 206 C 162 206, 144 188, 144 152 Z" className="ecosystemBackdropLayer" />
      </>
    );
  }

  if (sceneKey === "thorax") {
    return (
      <>
        <path d="M100 58 C 120 40, 154 32, 202 32 C 250 32, 284 40, 304 58 L 324 220 C 304 252, 270 270, 202 270 C 134 270, 100 252, 80 220 Z" className="ecosystemBodyOutline" />
        <ellipse cx="160" cy="152" rx="52" ry="84" className="ecosystemBackdropOrgan" />
        <ellipse cx="244" cy="152" rx="52" ry="84" className="ecosystemBackdropOrgan" />
        <rect x="190" y="92" width="24" height="128" rx="12" className="ecosystemBackdropLayer" />
      </>
    );
  }

  if (sceneKey === "pelvis") {
    return (
      <>
        <path d="M106 58 C 132 42, 164 34, 202 34 C 240 34, 272 42, 298 58 L 314 228 C 302 260, 274 282, 202 282 C 130 282, 102 260, 90 228 Z" className="ecosystemBodyOutline" />
        <ellipse cx="202" cy="166" rx="84" ry="62" className="ecosystemBackdropOrgan" />
        <path d="M156 164 C 172 138, 232 138, 248 164 C 260 184, 260 214, 248 228 C 228 250, 176 250, 156 228 C 144 214, 144 184, 156 164 Z" className="ecosystemBackdropLayer" />
      </>
    );
  }

  if (sceneKey === "skin") {
    return (
      <>
        <rect x="74" y="64" width="256" height="52" rx="24" className="ecosystemBodyOutline" />
        <rect x="74" y="116" width="256" height="122" rx="24" className="ecosystemBackdropLayer" />
        <rect x="74" y="238" width="256" height="58" rx="22" className="ecosystemBackdropOrgan" />
      </>
    );
  }

  return (
    <>
      <path d="M104 54 C 126 38, 158 30, 202 30 C 246 30, 278 38, 300 54 L 316 222 C 306 252, 276 272, 202 272 C 128 272, 98 252, 88 222 Z" className="ecosystemBodyOutline" />
      <ellipse cx="202" cy="156" rx="72" ry="96" className="ecosystemBackdropOrgan" />
      <path d="M154 158 C 160 124, 174 104, 202 104 C 230 104, 244 124, 250 158 C 244 190, 228 210, 202 210 C 176 210, 160 190, 154 158 Z" className="ecosystemBackdropLayer" />
    </>
  );
}

function pickByName<T extends { id: string }>(items: T[], id: string) {
  return items.find((item) => item.id === id) ?? items[0];
}

export function ProteinEffectVisual({ protein }: { protein: ProteinEffectResult }) {
  const mutationPosition = parsePosition(protein.mutation_location) ?? 175;
  const proteinLabel = protein.protein_name || protein.gene;
  const accessUrl = protein.protein_id && !protein.protein_id.startsWith("unknown:")
    ? `https://alphafold.ebi.ac.uk/entry/${protein.protein_id}`
    : null;
  const mutationRatio = Math.max(0.08, Math.min(0.92, mutationPosition / 400));

  const domains = [
    { label: "N-terminus", start: 0.06, end: 0.22, tone: "#d6eee1" },
    { label: protein.domain_hit || "core fold", start: 0.30, end: 0.59, tone: "#cce8dc" },
    { label: "mutation site", start: Math.max(0.55, Math.min(0.78, mutationRatio)), end: Math.max(0.57, Math.min(0.80, mutationRatio + 0.03)), tone: "#f0d6d2" },
    { label: "C-terminus", start: 0.80, end: 0.95, tone: "#d9e4f4" },
  ];

  return (
    <div className="visualPanel proteinVisual">
      <div className="visualPanelHeader">
        <div>
          <p className="visualEyebrow">AlphaFold-style structure view</p>
          <h3>{proteinLabel}</h3>
          <p className="visualSubtext">{protein.gene} · {protein.mutation} · {protein.protein_id || "unknown accession"}</p>
        </div>
        <div className="visualMetaStack">
          <span className="visualMeta">Activity {fmt(protein.activity)} · {rangeLabel(protein.activity)}</span>
          <span className="visualMeta">Stability {fmt(protein.stability)} · {rangeLabel(protein.stability)}</span>
          <span className="visualMeta">Binding {fmt(protein.binding)} · {rangeLabel(protein.binding)}</span>
        </div>
      </div>

      <div className="proteinVisualGrid">
        <div className="proteinStructureFrame">
          <div className="proteinStructureLegend">
            <span>Residue map</span>
            <span>Mutation at position {mutationPosition}</span>
          </div>
          <svg viewBox="0 0 960 260" className="proteinStructureSvg" role="img" aria-label="AlphaFold-style protein structure view">
            <defs>
              <linearGradient id="protein-track" x1="0%" x2="100%">
                <stop offset="0%" stopColor="#dbece3" />
                <stop offset="55%" stopColor="#b7d9c7" />
                <stop offset="100%" stopColor="#9fcbb8" />
              </linearGradient>
              <linearGradient id="protein-halo" x1="0%" x2="100%">
                <stop offset="0%" stopColor="#f9efe6" />
                <stop offset="100%" stopColor="#efc0b4" />
              </linearGradient>
            </defs>
            <rect x="40" y="118" width="880" height="18" rx="9" fill="url(#protein-track)" />
            {domains.map((domain) => (
              <g key={domain.label}>
                <rect
                  x={40 + domain.start * 880}
                  y={88}
                  width={Math.max(6, (domain.end - domain.start) * 880)}
                  height="78"
                  rx="16"
                  fill={domain.tone}
                  opacity="0.92"
                />
                <text
                  x={40 + domain.start * 880 + 10}
                  y={82}
                  className="proteinSvgLabel"
                >
                  {domain.label}
                </text>
              </g>
            ))}
            <line x1={40 + mutationRatio * 880} y1="60" x2={40 + mutationRatio * 880} y2="188" stroke="#c84d4d" strokeDasharray="8 6" strokeWidth="4" />
            <circle cx={40 + mutationRatio * 880} cy="118" r="20" fill="url(#protein-halo)" stroke="#c84d4d" strokeWidth="4">
              <animate attributeName="r" values="18;24;18" dur="2.8s" repeatCount="indefinite" />
            </circle>
            <text x={40 + mutationRatio * 880} y="121" textAnchor="middle" className="proteinSvgMutation">MUT</text>
            <text x="40" y="36" className="proteinSvgTitle">AlphaFold-like folded chain with mutation overlay</text>
            <text x="40" y="238" className="proteinSvgAxis">N-terminus</text>
            <text x="860" y="238" textAnchor="end" className="proteinSvgAxis">C-terminus</text>
          </svg>
        </div>

        <div className="visualMetricsStack">
          <MetricGauge label="Remaining activity" value={protein.activity} />
          <MetricGauge label="Remaining stability" value={protein.stability} />
          <MetricGauge label="Remaining binding" value={protein.binding} />
          <MetricGauge label="Loss-of-function" value={protein.loss_of_function_score} highlight />
          <div className="visualCallout">
            <strong>Structural note</strong>
            <p>{protein.structural_impact_placeholder}</p>
          </div>
          {accessUrl && (
            <a className="alphaFoldLink" href={accessUrl} target="_blank" rel="noreferrer">
              Open AlphaFold entry
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricGauge({ label, value, highlight = false }: { label: string; value: number; highlight?: boolean }) {
  const help = buildScoreLabelHelp(label, value);
  return (
    <div className="metricGauge">
      <div className="metricGaugeTop">
        <span className="metricGaugeLabel">
          {label}
          <InfoTooltip label={label} help={help} />
        </span>
        <strong>{fmt(value)}</strong>
      </div>
      <div className="barOuter">
        <div className={highlight ? "barInner highlight" : "barInner"} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%`, background: highlight ? "linear-gradient(90deg, #c84d4d, #8a1f1f)" : undefined }} />
      </div>
    </div>
  );
}

export function CellPhenotypeVisual({
  cell,
  diseaseName,
}: {
  cell: CellPhenotypeResult;
  diseaseName?: string;
}) {
  const organelles = useMemo<CellOrganelle[]>(
    () => [
      {
        id: "membrane",
        label: "Cell membrane",
        x: 248,
        y: 180,
        r: 124,
        color: "#cfe1d5",
        description: "Controls incoming signals, adhesion, and transport into the cell.",
        emphasis: Math.max(cell.proliferation_rate, cell.secretion_signal),
      },
      {
        id: "nucleus",
        label: "Nucleus",
        x: 205,
        y: 178,
        r: 58,
        color: "#b7d9c7",
        description: "Holds the DNA program and responds to repair, arrest, and stress signals.",
        emphasis: Math.max(cell.repair_capacity, 1 - cell.genomic_instability),
      },
      {
        id: "mitochondria",
        label: "Mitochondria",
        x: 315,
        y: 150,
        r: 20,
        color: "#9fcbb8",
        description: "Couples metabolism with apoptosis and cellular energy state.",
        emphasis: cell.apoptosis_rate,
      },
      {
        id: "er",
        label: "ER / Golgi",
        x: 145,
        y: 126,
        r: 18,
        color: "#d9e4f4",
        description: "Processes protein traffic, secretion, and stress signaling.",
        emphasis: cell.secretion_signal,
      },
      {
        id: "ribosomes",
        label: "Ribosomes",
        x: 135,
        y: 226,
        r: 16,
        color: "#f0d6d2",
        description: "Builds proteins and amplifies proliferative programs when signaling is high.",
        emphasis: cell.proliferation_rate,
      },
      {
        id: "cytoskeleton",
        label: "Cytoskeleton",
        x: 288,
        y: 238,
        r: 18,
        color: "#ead9a8",
        description: "Shapes cell movement, division, and invasion-related remodeling.",
        emphasis: cell.genomic_instability,
      },
    ],
    [cell.apoptosis_rate, cell.genomic_instability, cell.proliferation_rate, cell.repair_capacity, cell.secretion_signal],
  );
  const [focused, setFocused] = useState(organelles[1].id);
  const selected = pickByName(organelles, focused);
  const diseaseSite = inferTissueSite(diseaseName);
  return (
    <div className="visualPanel">
      <div className="visualPanelHeader">
        <div>
          <p className="visualEyebrow">Live cell-state schematic</p>
          <h3>Cell phenotype model</h3>
          <p className="visualSubtext">{cell.computed_from_gene || "selected gene"} · {cell.computed_from_pathway || "selected pathway"} · activity {cell.computed_from_protein_activity || "—"} · {diseaseSite.tissue}</p>
        </div>
        <div className="visualMetaStack">
          <span className="visualMeta">Mapping: {cell.mapping_mode || "generic"}</span>
          <span className="visualMeta">Functional loss {fmt(cell.functional_loss_score ?? 0.5)}</span>
          <span className="visualMeta">Pathway disruption {fmt(cell.pathway_disruption_score ?? 0.5)}</span>
        </div>
      </div>

      <div className="cellVisualLayout">
        <svg viewBox="0 0 520 360" className="cellVisualSvg" role="img" aria-label="Cell anatomy visualization">
          <defs>
            <radialGradient id="cellCore" cx="50%" cy="50%" r="55%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="100%" stopColor="#d8eee2" />
            </radialGradient>
            <radialGradient id="cellGlow" cx="50%" cy="50%" r="55%">
              <stop offset="0%" stopColor="#f4fbf6" />
              <stop offset="100%" stopColor="#e5f3ea" />
            </radialGradient>
            <linearGradient id="cellFlux" x1="0%" x2="100%">
              <stop offset="0%" stopColor="#9fcbb8" />
              <stop offset="100%" stopColor="#237457" />
            </linearGradient>
          </defs>
          <circle cx="248" cy="180" r="145" fill="url(#cellGlow)" stroke="#cfe1d5" strokeWidth="2" />
          <circle cx="248" cy="180" r="108" fill="url(#cellCore)" stroke="#9fcbb8" strokeWidth="3" />
          <circle cx="248" cy="180" r="58" fill="#f3f7f4" stroke="#bfd3c7" strokeWidth="2" />
          <text x="248" y="170" textAnchor="middle" className="cellTitle">CELL</text>
          <text x="248" y="192" textAnchor="middle" className="cellTitleSmall">anatomy</text>

          {organelles.map((organelle) => {
            const isSelected = organelle.id === selected.id;
            return (
              <g
                key={organelle.id}
                className={isSelected ? "cellOrganelle selected" : "cellOrganelle"}
                onClick={() => setFocused(organelle.id)}
                role="button"
                tabIndex={0}
              >
                <circle
                  cx={organelle.x}
                  cy={organelle.y}
                  r={organelle.r + 8}
                  fill={organelle.color}
                  opacity={0.18 + organelle.emphasis * 0.24}
                  stroke={isSelected ? "#12201d" : "#9fcbb8"}
                  strokeWidth={isSelected ? 3 : 1.5}
                >
                  <animate attributeName="r" values={`${organelle.r + 6};${organelle.r + 12};${organelle.r + 6}`} dur={`${2.2 + organelle.emphasis}s`} repeatCount="indefinite" />
                </circle>
                <circle cx={organelle.x} cy={organelle.y} r={organelle.r} fill={organelle.color} opacity={0.9} />
                <text x={organelle.x} y={organelle.y + 4} textAnchor="middle" className="cellOrganelleLabel">{organelle.label}</text>
              </g>
            );
          })}

          <path d="M110 110 C 160 135, 185 148, 205 160" className="cellArrow" />
          <path d="M350 110 C 315 138, 295 150, 275 160" className="cellArrow" />
          <path d="M120 250 C 160 230, 188 220, 212 208" className="cellArrow" />
          <path d="M328 242 C 300 228, 288 218, 268 208" className="cellArrow" />
          <path d="M245 100 C 246 118, 246 130, 246 146" stroke="url(#cellFlux)" strokeWidth="4" fill="none" strokeLinecap="round" />
          <path d="M245 210 C 246 226, 246 238, 246 252" stroke="url(#cellFlux)" strokeWidth="4" fill="none" strokeLinecap="round" />
          <text x="44" y="50" className="cellMetricLabel">Selected site: {diseaseSite.organ}</text>
          <text x="44" y="72" className="cellNodeLabel">{diseaseSite.context}</text>
        </svg>

        <div className="visualMetricsStack">
          <MetricGauge label="Proliferation" value={cell.proliferation_rate} />
          <MetricGauge label="Apoptosis" value={cell.apoptosis_rate} />
          <MetricGauge label="Repair capacity" value={cell.repair_capacity} />
          <MetricGauge label="Genomic instability" value={cell.genomic_instability} highlight />
          <div className="visualCallout">
            <strong>{selected.label}</strong>
            <p>{selected.description}</p>
          </div>
          <div className="visualCallout">
            <strong>Cell model</strong>
            <p>{cell.explanation}</p>
          </div>
          <div className="cellPartList">
            {organelles.map((organelle) => (
              <button
                key={organelle.id}
                type="button"
                className={organelle.id === selected.id ? "cellPartButton active" : "cellPartButton"}
                onClick={() => setFocused(organelle.id)}
              >
                <span>{organelle.label}</span>
                <strong>{fmt(organelle.emphasis)}</strong>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function PopulationDynamicsVisual({ population, active }: { population: PopulationResult; active: boolean }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active || population.trajectory.length <= 1) return;
    const timer = window.setInterval(() => {
      setIndex((value) => (value + 1) % population.trajectory.length);
    }, 850);
    return () => window.clearInterval(timer);
  }, [active, population.trajectory.length]);

  const current = population.trajectory[Math.min(index, population.trajectory.length - 1)] ?? population.trajectory[population.trajectory.length - 1];
  const maxStep = Math.max(...population.trajectory.map((point) => point.step), 1);
  const points = useMemo(
    () =>
      population.trajectory
        .map((point: PopulationResult["trajectory"][number]) => {
          const x = 60 + (point.step / maxStep) * 820;
          const y = 220 - point.mutated_fraction * 170;
          return `${x},${y}`;
        })
        .join(" "),
    [population.trajectory, maxStep],
  );

  return (
    <div className="visualPanel">
      <div className="visualPanelHeader">
        <div>
          <p className="visualEyebrow">Live population simulation</p>
          <h3>Clone expansion over time</h3>
          <p className="visualSubtext">{population.computed_from_gene || "selected gene"} · {population.computed_from_pathway || "selected pathway"} · activity {population.computed_from_protein_activity || "—"}</p>
        </div>
        <div className="visualMetaStack">
          <span className="visualMeta">Final mutated fraction {fmt(population.final_mutated_fraction)}</span>
          <span className="visualMeta">Clonal expansion {fmt(population.clonal_expansion_score)}</span>
          <span className="visualMeta">Step {current?.step ?? 0}</span>
        </div>
      </div>
      <div className="populationVisualGrid">
        <svg viewBox="0 0 960 300" className="populationVisualSvg" role="img" aria-label="Population trajectory visualization">
          <line x1="60" y1="220" x2="900" y2="220" className="visualAxis" />
          <line x1="60" y1="40" x2="60" y2="220" className="visualAxis" />
          <polyline points={points} fill="none" className="populationLine" />
          {population.trajectory.map((point: PopulationResult["trajectory"][number], i: number) => {
            const x = 60 + (point.step / maxStep) * 820;
            const y = 220 - point.mutated_fraction * 170;
            return (
              <g key={point.step}>
                <circle cx={x} cy={y} r={i === index ? 9 : 6} className={i === index ? "populationNode active" : "populationNode"} />
                {i === index && (
                  <text x={x} y={y - 16} textAnchor="middle" className="populationNodeLabel">
                    step {point.step}
                  </text>
                )}
              </g>
            );
          })}
          <text x="60" y="28" className="populationAxisLabel">mutated fraction</text>
          <text x="824" y="284" className="populationAxisLabel">time steps</text>
        </svg>
        <div className="populationStats">
          <div className="populationBars">
            <MetricGauge label="Final mutated fraction" value={population.final_mutated_fraction} />
            <MetricGauge label="Clonal expansion score" value={population.clonal_expansion_score} highlight />
          </div>
          <div className="populationSnapshot">
            <div>
              <span>Normal cells</span>
              <strong>{current?.normal_cells ?? "—"}</strong>
            </div>
            <div>
              <span>Mutated cells</span>
              <strong>{current?.mutated_cells ?? "—"}</strong>
            </div>
            <div>
              <span>Current fraction</span>
              <strong>{current ? fmt(current.mutated_fraction) : "—"}</strong>
            </div>
          </div>
          <div className="visualCallout">
            <strong>Population model</strong>
            <p>{population.explanation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function EcosystemVisual({ ecosystem, diseaseName }: { ecosystem: EcosystemResult; diseaseName?: string }) {
  const site = useMemo(() => inferTissueSite(diseaseName), [diseaseName]);
  const scene = useMemo(() => buildEcosystemScene(site, ecosystem), [ecosystem, site]);
  const [focused, setFocused] = useState(scene.areas[0]?.id ?? "primary");
  useEffect(() => {
    setFocused(scene.areas[0]?.id ?? "primary");
  }, [scene.key]);
  const selected = pickByName(scene.areas, focused);
  return (
    <div className="visualPanel">
      <div className="visualPanelHeader">
        <div>
          <p className="visualEyebrow">Ecosystem-level model</p>
          <h3>{scene.title}</h3>
          <p className="visualSubtext">{ecosystem.computed_from_gene || "selected gene"} · {ecosystem.computed_from_pathway || "selected pathway"} · activity {ecosystem.computed_from_protein_activity || "—"} · {scene.subtitle}</p>
        </div>
        <div className="visualMetaStack">
          <span className="visualMeta">Risk score {fmt(ecosystem.ecosystem_risk_score)}</span>
          <span className="visualMeta">Immune clearance {fmt(ecosystem.immune_clearance)}</span>
          <span className="visualMeta">Nutrient stress {fmt(ecosystem.nutrient_stress)}</span>
        </div>
      </div>

      <div className="ecosystemVisualGrid ecosystemAnatomyGrid">
        <div className="ecosystemAnatomyFrame">
          <div className="ecosystemMapHeader">
            <div>
              <strong>{scene.bodyLabel}</strong>
              <p>{scene.bodyNote}</p>
            </div>
            <span>interactive tissue map</span>
          </div>
          <svg viewBox="0 0 420 340" className="ecosystemBodySvg" role="img" aria-label="Ecosystem anatomical body site">
            <defs>
              <linearGradient id="ecosystemSceneFill" x1="0%" x2="100%">
                <stop offset="0%" stopColor="#f7fbf8" />
                <stop offset="100%" stopColor="#edf7f1" />
              </linearGradient>
            </defs>
            <rect x="8" y="8" width="404" height="324" rx="28" fill="url(#ecosystemSceneFill)" stroke="#dce9df" />
            <EcosystemBackdrop sceneKey={scene.key} />
            {scene.areas.map((area) => {
              const isSelected = area.id === selected.id;
              const cx = area.x + area.w / 2;
              const cy = area.y + area.h / 2;
              return (
                <g
                  key={area.id}
                  className={isSelected ? "ecosystemArea selected" : "ecosystemArea"}
                  onClick={() => setFocused(area.id)}
                  role="button"
                  tabIndex={0}
                >
                  {area.kind === "ellipse" ? (
                    <ellipse cx={cx} cy={cy} rx={area.w / 2} ry={area.h / 2} fill={area.tone} opacity={0.82} stroke={isSelected ? "#12201d" : area.accent} strokeWidth={isSelected ? 3 : 1.6} />
                  ) : (
                    <rect x={area.x} y={area.y} width={area.w} height={area.h} rx="16" fill={area.tone} opacity={0.82} stroke={isSelected ? "#12201d" : area.accent} strokeWidth={isSelected ? 3 : 1.6} />
                  )}
                  <rect x={area.x + 8} y={area.y + 8} width={area.w - 16} height={area.h - 16} rx="12" fill="transparent" stroke={isSelected ? "#12201d" : "#ffffff"} strokeDasharray={isSelected ? "0" : "7 6"} strokeWidth={isSelected ? 2.5 : 1} />
                  <text x={cx} y={cy - 6} textAnchor="middle" className="ecosystemAreaLabel">{area.label}</text>
                  <text x={cx} y={cy + 16} textAnchor="middle" className="ecosystemAreaValue">{fmt(area.value)}</text>
                  {isSelected && <text x={cx} y={cy + 38} textAnchor="middle" className="ecosystemAreaHint">active region</text>}
                </g>
              );
            })}
            <text x="32" y="40" className="ecosystemMapTitle">{scene.title}</text>
            <text x="32" y="62" className="ecosystemMapSubtitle">{scene.subtitle}</text>
            {scene.axes.map((axis, index) => (
              <text key={axis} x="32" y={312 - index * 18} className="ecosystemAxisLabel">{axis}</text>
            ))}
          </svg>
        </div>

        <div className="ecosystemSidePanel">
          <div className="visualMetricsStack">
            <MetricGauge label="Tumor-like burden" value={ecosystem.tumor_like_burden} />
            <MetricGauge label="Immune clearance" value={ecosystem.immune_clearance} />
            <MetricGauge label="Inflammation" value={ecosystem.inflammation} />
            <MetricGauge label="Nutrient stress" value={ecosystem.nutrient_stress} />
            <MetricGauge label="Ecosystem risk" value={ecosystem.ecosystem_risk_score} highlight />
          </div>

          <div className="visualCallout">
            <strong>{selected.label}</strong>
            <p>{selected.description}</p>
          </div>
          <div className="visualCallout">
            <strong>Ecosystem model</strong>
            <p>{ecosystem.explanation}</p>
          </div>
          <div className="cellPartList">
            {scene.areas.map((area) => (
              <button
                key={area.id}
                type="button"
                className={area.id === selected.id ? "cellPartButton active" : "cellPartButton"}
                onClick={() => setFocused(area.id)}
              >
                <span>{area.label}</span>
                <strong>{fmt(area.emphasis)}</strong>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
