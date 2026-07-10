from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.services.utils import clamp, round4


Phenotype = dict[str, str]

LOCAL_PHENOTYPES: dict[str, Phenotype] = {
    "fever": {"id": "HP:0001945", "label": "Fever"},
    "fatigue": {"id": "HP:0012378", "label": "Fatigue"},
    "weight loss": {"id": "HP:0001824", "label": "Weight loss"},
    "shortness of breath": {"id": "HP:0002094", "label": "Dyspnea"},
    "chest pain": {"id": "HP:0100749", "label": "Chest pain"},
    "abdominal pain": {"id": "HP:0002027", "label": "Abdominal pain"},
    "diarrhea": {"id": "HP:0002014", "label": "Diarrhea"},
    "headache": {"id": "HP:0002315", "label": "Headache"},
    "seizure": {"id": "HP:0001250", "label": "Seizure"},
    "weakness": {"id": "HP:0025406", "label": "Weakness"},
    "rash": {"id": "HP:0000988", "label": "Skin rash"},
    "joint pain": {"id": "HP:0002829", "label": "Arthralgia"},
    "cough": {"id": "HP:0012735", "label": "Cough"},
    "jaundice": {"id": "HP:0000952", "label": "Jaundice"},
    "swelling": {"id": "HP:0000969", "label": "Edema"},
    "blood in urine": {"id": "HP:0012587", "label": "Hematuria"},
    "palpitations": {"id": "HP:0001962", "label": "Palpitations"},
    "depression": {"id": "HP:0000716", "label": "Depression"},
    "anxiety": {"id": "HP:0000739", "label": "Anxiety"},
    "developmental delay": {"id": "HP:0001263", "label": "Global developmental delay"},
}

DISEASE_LIBRARY: list[dict[str, Any]] = [
    {"name": "Viral respiratory infection", "category": "infectious", "mechanism": "Viral airway inflammation activates innate immune responses.", "symptoms": ["fever", "cough", "fatigue", "shortness of breath"], "key_missing": ["oxygen saturation", "exposure history"], "genes": [], "pathways": ["innate immune signaling"], "prevalence": 0.72},
    {"name": "Systemic lupus erythematosus", "category": "autoimmune", "mechanism": "Loss of immune tolerance can drive multi-organ inflammation.", "symptoms": ["fatigue", "rash", "joint pain", "fever"], "key_missing": ["ANA", "complement levels", "kidney involvement"], "genes": ["HLA"], "pathways": ["interferon signaling"], "prevalence": 0.18},
    {"name": "Type 2 diabetes mellitus", "category": "endocrine/metabolic", "mechanism": "Insulin resistance and impaired glucose handling alter metabolic homeostasis.", "symptoms": ["fatigue", "weight loss"], "key_missing": ["HbA1c", "fasting glucose", "polyuria"], "genes": ["TCF7L2"], "pathways": ["insulin signaling"], "prevalence": 0.45},
    {"name": "Migraine disorder", "category": "neurological", "mechanism": "Neurovascular excitability and sensory processing pathways become overactive.", "symptoms": ["headache", "fatigue", "nausea"], "key_missing": ["photophobia", "aura", "trigger pattern"], "genes": ["CACNA1A"], "pathways": ["neuronal excitability"], "prevalence": 0.33},
    {"name": "Chronic kidney disease", "category": "renal", "mechanism": "Reduced nephron function alters filtration, volume regulation, and toxin clearance.", "symptoms": ["fatigue", "swelling", "blood in urine"], "key_missing": ["creatinine", "eGFR", "urine protein"], "genes": ["APOL1"], "pathways": ["renal filtration"], "prevalence": 0.25},
    {"name": "Hepatitis or liver inflammation", "category": "hepatic", "mechanism": "Liver injury can impair detoxification, bile handling, and inflammatory balance.", "symptoms": ["fatigue", "jaundice", "abdominal pain", "fever"], "key_missing": ["ALT", "AST", "bilirubin"], "genes": [], "pathways": ["hepatic inflammation"], "prevalence": 0.24},
    {"name": "Iron-deficiency anemia", "category": "hematologic/nutritional", "mechanism": "Low iron availability limits hemoglobin production and oxygen carrying capacity.", "symptoms": ["fatigue", "shortness of breath", "palpitations", "weakness"], "key_missing": ["hemoglobin", "ferritin", "MCV"], "genes": [], "pathways": ["erythropoiesis"], "prevalence": 0.38},
    {"name": "Cystic fibrosis", "category": "genetic/rare disease", "mechanism": "CFTR channel dysfunction changes epithelial salt and mucus transport.", "symptoms": ["cough", "shortness of breath", "diarrhea", "weight loss"], "key_missing": ["sweat chloride", "CFTR variants", "pancreatic status"], "genes": ["CFTR"], "pathways": ["chloride transport"], "prevalence": 0.05},
    {"name": "Malignancy-associated systemic syndrome", "category": "oncologic", "mechanism": "Abnormal cell growth can produce systemic inflammation and tissue burden.", "symptoms": ["weight loss", "fatigue", "fever"], "key_missing": ["imaging", "biopsy", "CBC"], "genes": ["TP53", "BRCA1", "BRAF"], "pathways": ["cell cycle", "DNA repair"], "prevalence": 0.16},
    {"name": "Coronary artery disease", "category": "cardiovascular", "mechanism": "Atherosclerotic plaque can reduce oxygen delivery to heart muscle.", "symptoms": ["chest pain", "shortness of breath", "palpitations", "fatigue"], "key_missing": ["ECG", "troponin", "lipids"], "genes": ["LDLR"], "pathways": ["lipid transport"], "prevalence": 0.35},
    {"name": "Asthma or reactive airway disease", "category": "respiratory", "mechanism": "Airway inflammation and bronchoconstriction reduce airflow.", "symptoms": ["shortness of breath", "cough", "chest pain"], "key_missing": ["wheeze", "spirometry", "allergen exposure"], "genes": ["IL13"], "pathways": ["type 2 inflammation"], "prevalence": 0.31},
    {"name": "Inflammatory bowel disease", "category": "gastrointestinal/autoimmune", "mechanism": "Immune dysregulation injures intestinal mucosa.", "symptoms": ["abdominal pain", "diarrhea", "weight loss", "fatigue"], "key_missing": ["blood in stool", "CRP", "colonoscopy"], "genes": ["NOD2"], "pathways": ["gut immune barrier"], "prevalence": 0.12},
    {"name": "Atopic dermatitis", "category": "dermatologic", "mechanism": "Skin barrier disruption and type 2 inflammation cause chronic rash and itching.", "symptoms": ["rash"], "key_missing": ["itching", "trigger pattern", "allergy history"], "genes": ["FLG"], "pathways": ["skin barrier"], "prevalence": 0.29},
    {"name": "Major depressive episode", "category": "psychiatric/neurodevelopmental", "mechanism": "Stress, neurotransmitter, sleep, and inflammatory pathways can alter mood regulation.", "symptoms": ["depression", "fatigue", "anxiety"], "key_missing": ["sleep change", "appetite change", "suicidal intent"], "genes": [], "pathways": ["neuroendocrine stress"], "prevalence": 0.28},
    {"name": "Medication-related adverse effect", "category": "medication-related/toxic", "mechanism": "Drug exposure can perturb metabolism, immune response, or organ function.", "symptoms": ["fatigue", "rash", "abdominal pain", "jaundice"], "key_missing": ["medication timeline", "dose change", "liver enzymes"], "genes": ["CYP2D6"], "pathways": ["drug metabolism"], "prevalence": 0.22},
    {"name": "Vitamin B12 deficiency", "category": "nutritional/hematologic", "mechanism": "Reduced B12 impairs red blood cell production and nerve maintenance.", "symptoms": ["fatigue", "weakness", "palpitations"], "key_missing": ["B12 level", "MCV", "neuropathy"], "genes": [], "pathways": ["one-carbon metabolism"], "prevalence": 0.19},
    {"name": "Thyroid dysfunction", "category": "endocrine", "mechanism": "Abnormal thyroid hormone levels alter metabolic rate and cardiovascular tone.", "symptoms": ["fatigue", "weight loss", "palpitations", "anxiety"], "key_missing": ["TSH", "free T4", "neck findings"], "genes": ["TSHR"], "pathways": ["thyroid hormone signaling"], "prevalence": 0.26},
    {"name": "Seizure disorder", "category": "neurological", "mechanism": "Abnormal synchronized neuronal firing causes episodic neurologic symptoms.", "symptoms": ["seizure", "headache", "weakness"], "key_missing": ["EEG", "event description", "medication history"], "genes": ["SCN1A"], "pathways": ["ion channel signaling"], "prevalence": 0.09},
    {"name": "Hypertrophic cardiomyopathy", "category": "cardiovascular/genetic", "mechanism": "Sarcomere gene changes can thicken heart muscle and alter rhythm.", "symptoms": ["shortness of breath", "chest pain", "palpitations"], "key_missing": ["echocardiogram", "family sudden death", "sarcomere variants"], "genes": ["MYH7", "MYBPC3"], "pathways": ["sarcomere contraction"], "prevalence": 0.06},
    {"name": "Mitochondrial disease", "category": "genetic/rare disease", "mechanism": "Energy production defects affect high-demand tissues such as brain and muscle.", "symptoms": ["fatigue", "weakness", "seizure", "developmental delay"], "key_missing": ["lactate", "mtDNA testing", "multisystem involvement"], "genes": ["MT-ND1"], "pathways": ["oxidative phosphorylation"], "prevalence": 0.04},
]

RED_FLAGS = {
    "chest pain": "Chest pain can require urgent medical evaluation, especially if severe, new, or associated with shortness of breath, sweating, or fainting.",
    "severe breathing difficulty": "Severe breathing difficulty can be an emergency and should not be evaluated only by this simulator.",
    "stroke": "Stroke-like symptoms such as facial droop, one-sided weakness, or sudden speech trouble may require emergency care.",
    "loss of consciousness": "Loss of consciousness can require urgent medical evaluation.",
    "suicidal": "Suicidal intent or self-harm thoughts require immediate support from emergency or crisis services.",
    "severe allergic reaction": "Severe allergic reaction can be life-threatening and may need urgent medical care.",
    "severe acute pain": "Severe acute pain can signal an emergency condition and should be assessed promptly.",
}


class DigitalTwinRequest(BaseModel):
    disease: str = ""
    gene: str = ""
    mutation: str = ""
    protein: Optional[str] = None
    pathway: Optional[str] = None
    mode: Literal["known", "unknown"] = "known"
    symptoms: str = ""
    normalized_symptoms: list[dict[str, str]] = Field(default_factory=list)
    age: int = Field(default=40, ge=0, le=120)
    sex: Literal["female", "male", "intersex", "unspecified"] = "unspecified"
    ethnicity: Optional[str] = None
    ancestry: Optional[str] = None
    weight_kg: float = Field(default=70, ge=2, le=400)
    height_cm: float = Field(default=170, ge=40, le=250)
    medical_conditions: list[str] = Field(default_factory=list)
    family_history: list[str] = Field(default_factory=list)
    known_diagnoses: list[str] = Field(default_factory=list)
    smoking: Literal["never", "former", "current"] = "never"
    alcohol_units_week: float = Field(default=0, ge=0, le=100)
    exercise_minutes_week: int = Field(default=150, ge=0, le=3000)
    diet_quality: float = Field(default=0.65, ge=0, le=1)
    lifestyle_factors: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    genes: list[str] = Field(default_factory=list)
    mutations: list[str] = Field(default_factory=list)
    variants: list[str] = Field(default_factory=list)
    laboratory_values: dict[str, float] = Field(default_factory=dict)
    baseline: dict[str, Any] = Field(default_factory=dict)


class DigitalTwinResult(BaseModel):
    mode: Literal["known", "unknown"] = "known"
    patient_profile: dict[str, Any]
    normalized_symptoms: list[dict[str, str]] = Field(default_factory=list)
    safety_warnings: list[str] = Field(default_factory=list)
    disease_risk_profile: list[dict[str, Any]]
    differential_diagnosis: list[dict[str, Any]] = Field(default_factory=list)
    graph: dict[str, Any] = Field(default_factory=dict)
    category_distribution: dict[str, Any] = Field(default_factory=dict)
    known_disease_panels: dict[str, Any] = Field(default_factory=dict)
    intervention_scenarios: list[dict[str, Any]] = Field(default_factory=list)
    mutation_interpretation: dict[str, Any]
    protein_effects: dict[str, Any]
    pathway_effects: list[dict[str, Any]]
    cell_state: dict[str, float]
    population_behaviour: dict[str, float]
    predicted_biological_state: dict[str, Any]
    affected_systems: list[str]
    potential_mechanisms: list[str]
    missing_data: list[str] = Field(default_factory=list)
    confidence: float
    evidence: list[dict[str, str]]
    reasoning: list[str]
    disclaimer: str = "Research prototype only; not a clinical diagnosis, triage system, or treatment recommendation."


def _list_risk(values: list[str], term: str) -> float:
    return min(0.18, sum(0.04 for value in values if term.lower() in value.lower()))


def _tokens(value: str) -> list[str]:
    text = value.lower().replace(";", ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def normalize_symptoms(raw: str, provided: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for item in provided or []:
      label = str(item.get("label") or item.get("name") or "").strip()
      if label and label.lower() not in seen:
          normalized.append({"id": str(item.get("id") or "LOCAL:FALLBACK"), "label": label, "raw": label, "source": str(item.get("source") or "user supplied")})
          seen.add(label.lower())
    for symptom in _tokens(raw):
        match_key = next((key for key in LOCAL_PHENOTYPES if key in symptom or symptom in key), None)
        phenotype = LOCAL_PHENOTYPES.get(match_key or "", {"id": "LOCAL:UNMAPPED", "label": symptom.title()})
        label = phenotype["label"]
        if label.lower() in seen:
            continue
        normalized.append({"id": phenotype["id"], "label": label, "raw": symptom, "source": "local fallback HPO dictionary"})
        seen.add(label.lower())
    return normalized


def red_flag_warnings(raw_symptoms: str) -> list[str]:
    text = raw_symptoms.lower()
    return [warning for term, warning in RED_FLAGS.items() if term in text]


def _intervention_categories(category: str, genes: list[str], evidence_sources: list[str]) -> list[str]:
    categories = ["monitoring/supportive care", "specialist evaluation/research follow-up"]
    cat = category.lower()
    if "infectious" in cat:
        categories.insert(0, "drug therapy")
    if "autoimmune" in cat or "inflammatory" in cat:
        categories.insert(0, "immune modulation")
    if "metabolic" in cat or "nutritional" in cat or "endocrine" in cat:
        categories.insert(0, "lifestyle/environmental modification")
        categories.insert(1, "nutritional intervention")
    if "oncologic" in cat or genes:
        categories.insert(0, "targeted therapy")
        categories.insert(1, "pathway modulation")
    if genes:
        categories.append("gene/variant-focused intervention")
    if any(source in {"ChEMBL", "CIViC", "Open Targets"} for source in evidence_sources):
        categories.append("evidence-backed searchable drug option")
    return list(dict.fromkeys(categories))


def _score_disease(req: DigitalTwinRequest, disease: dict[str, Any], normalized: list[dict[str, str]]) -> dict[str, Any]:
    symptom_labels = {symptom["label"].lower() for symptom in normalized}
    raw_terms = {symptom["raw"].lower() for symptom in normalized}
    disease_symptoms = set(disease["symptoms"])
    matched = sorted(symptom for symptom in disease_symptoms if symptom in raw_terms or any(symptom in label for label in symptom_labels))
    specificity = sum(0.08 for symptom in matched if symptom in {"seizure", "jaundice", "blood in urine", "developmental delay", "chest pain"})
    symptom_score = len(matched) / max(len(disease_symptoms), 1)
    family_score = 0.1 if any(gene.lower() in " ".join(req.family_history).lower() for gene in disease.get("genes", [])) else 0.0
    variant_pool = " ".join(req.variants + req.mutations + req.genes).lower()
    variant_score = 0.18 if any(gene.lower() in variant_pool for gene in disease.get("genes", [])) else 0.0
    lab_score = 0.0
    if "glucose" in req.laboratory_values and ("diabetes" in disease["name"].lower() or "thyroid" in disease["name"].lower()):
        lab_score += 0.08
    if "crp" in req.laboratory_values and any(word in disease["category"].lower() for word in ["autoimmune", "infectious", "inflammatory"]):
        lab_score += 0.08
    age_score = 0.05 if req.age > 55 and any(word in disease["category"].lower() for word in ["cardiovascular", "oncologic", "renal"]) else 0.03
    prevalence_score = float(disease["prevalence"]) * 0.12
    missing_penalty = max(0, len(disease["key_missing"]) - len(matched)) * 0.015
    score = clamp(symptom_score * 0.48 + specificity + family_score + variant_score + lab_score + age_score + prevalence_score - missing_penalty)
    evidence_sources = ["local fallback HPO dictionary", "local fallback disease mechanism library"]
    if variant_score:
        evidence_sources.append("ClinVar/Open Targets adapter context when available")
    intervention_categories = _intervention_categories(disease["category"], disease.get("genes", []), evidence_sources)
    return {
        "rank": 0,
        "disease": disease["name"],
        "disease_category": disease["category"],
        "real_world_causes_mechanism": disease["mechanism"],
        "matching_symptoms": matched,
        "missing_or_unconfirmed_key_symptoms": disease["key_missing"],
        "patient_risk_factors_that_support_it": _risk_factor_text(req, variant_score, family_score, lab_score),
        "evidence_sources": evidence_sources,
        "confidence": round4(score),
        "why_ranked_here": f"Ranked by deterministic symptom overlap ({len(matched)} matches), phenotype specificity, patient risk factors, lab/variant support, and penalties for missing key features.",
        "genes": disease.get("genes", []),
        "pathways": disease.get("pathways", []),
        "intervention_categories": intervention_categories,
        "suggested_drug_options": [],
        "intervention_note": "Simulation categories only; not treatment advice. More clinical and molecular data are needed before any real-world decision.",
    }


def _risk_factor_text(req: DigitalTwinRequest, variant_score: float, family_score: float, lab_score: float) -> list[str]:
    factors: list[str] = []
    if req.age > 55:
        factors.append(f"age {req.age}")
    if req.smoking != "never":
        factors.append(f"{req.smoking} smoking history")
    if req.family_history:
        factors.append("family history provided")
    if req.medications:
        factors.append("medication exposure provided")
    if variant_score:
        factors.append("gene/variant input overlaps disease biology")
    if lab_score:
        factors.append("entered lab values support this category")
    return factors or ["symptom pattern is the main support in this run"]


def rank_diseases(req: DigitalTwinRequest) -> DigitalTwinResult:
    normalized = normalize_symptoms(req.symptoms, req.normalized_symptoms)
    rows = [_score_disease(req, disease, normalized) for disease in DISEASE_LIBRARY]
    rows = sorted(rows, key=lambda row: (-row["confidence"], row["disease"]))[:20]
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    graph = _build_unknown_graph(normalized, rows[:8])
    category_distribution = _category_distribution(rows)
    profile = _profile(req, normalized)
    risks = [{"name": row["disease"], "score": row["confidence"], "provenance": "local fallback differential ranking"} for row in rows[:6]]
    evidence = [
        {"source": "Local fallback HPO dictionary", "category": "local fallback", "detail": "Normalizes typed symptoms into HPO-style phenotype terms where possible."},
        {"source": "Local fallback disease mechanism library", "category": "local fallback", "detail": "Ranks diseases when live MONDO/MedGen/Orphanet/Open Targets access is unavailable."},
    ]
    return DigitalTwinResult(
        mode="unknown",
        patient_profile=profile,
        normalized_symptoms=normalized,
        safety_warnings=red_flag_warnings(req.symptoms),
        disease_risk_profile=risks,
        differential_diagnosis=rows,
        graph=graph,
        category_distribution=category_distribution,
        intervention_scenarios=[_scenario_from_row(row) for row in rows],
        mutation_interpretation={"gene": req.gene or "unknown", "mutation": req.mutation or "unknown", "interpretation": "Unknown illness mode does not require a selected disease, gene, or mutation."},
        protein_effects={"protein": req.protein or "unknown", "remaining_activity": 0.5, "confidence": 0.35},
        pathway_effects=[{"pathway": pathway, "risk": rows[0]["confidence"], "status": "candidate mechanism"} for pathway in rows[0].get("pathways", [])],
        cell_state={"phenotype_match": rows[0]["confidence"], "laboratory_support": _lab_support(req), "variant_support": _variant_support(req, rows[0])},
        population_behaviour={"ranked_candidate_count": float(len(rows)), "top_confidence": rows[0]["confidence"] if rows else 0.0},
        predicted_biological_state={"overall_risk": rows[0]["confidence"] if rows else 0.0, "status": "differential ranking only"},
        affected_systems=sorted({row["disease_category"] for row in rows[:6]}),
        potential_mechanisms=[row["real_world_causes_mechanism"] for row in rows[:5]],
        missing_data=["clinical exam", "confirmatory diagnostic tests", "longitudinal symptoms", "review by qualified clinician"],
        confidence=round4(max((row["confidence"] for row in rows), default=0.0)),
        evidence=evidence,
        reasoning=[
            "Unknown illness mode ranks possible diseases; it does not diagnose.",
            "Scores combine symptom overlap, HPO-style phenotype match, prevalence priors, age/sex fit, family history, labs, variants, tissue/pathway plausibility, and penalties for missing key features.",
            "Rows are intentionally diverse across infectious, autoimmune, endocrine, neurological, renal, hepatic, hematologic, genetic, oncologic, cardiovascular, respiratory, gastrointestinal, dermatologic, psychiatric, toxic, nutritional, and medication-related categories.",
        ],
    )


def build_known_disease_model(req: DigitalTwinRequest) -> DigitalTwinResult:
    normalized = normalize_symptoms(req.symptoms, req.normalized_symptoms)
    base = build_digital_twin(req)
    symptom_match = _known_symptom_match(req, normalized)
    tissue_burden = clamp(base.predicted_biological_state["overall_risk"] * 0.55 + symptom_match * 0.25 + _lab_support(req) * 0.20)
    missing = [
        "confirmed phenotype frequencies for this patient",
        "disease-specific longitudinal progression data",
        "complete variant interpretation" if not (req.mutation or req.variants or req.mutations) else "functional validation of variant effect",
        "tissue-specific expression or imaging context",
    ]
    panels = {
        "Patient Profile Summary": f"{req.age}-year-old {req.sex} profile with {len(normalized)} normalized phenotype terms and {len(req.family_history)} family-history entries.",
        "Known Disease Mechanism": f"{req.disease or 'selected disease'} is modeled through patient symptoms, pathway burden, baseline BioScale outputs, and entered risk factors.",
        "Patient-Specific Symptom Match": f"Current symptom-to-known-disease alignment is {symptom_match:.2f}; unmatched symptoms remain uncertainty drivers.",
        "Variant/Genetic Evidence": "Variant context is connected when gene/mutation or additional variants are provided; otherwise this panel remains phenotype-driven.",
        "Tissue and Pathway Burden": f"Modeled pathway/tissue burden is {tissue_burden:.2f}, derived from BioScale risk, symptom match, and lab support.",
        "Cell Phenotype State": f"Cell state retains proliferation {base.cell_state.get('proliferation', 0.5):.2f}, repair {base.cell_state.get('repair_capacity', 0.5):.2f}, and immune clearance {base.cell_state.get('immune_clearance', 0.5):.2f}.",
        "Population/Ecosystem State": f"Population pressure is {base.population_behaviour.get('personalized_pressure', 0.5):.2f}; this is patient-specific model logic, not clinical staging.",
        "Patient-Specific Risk Drivers": "; ".join(_risk_factor_text(req, 0.12 if req.gene or req.variants else 0.0, 0.08 if req.family_history else 0.0, _lab_support(req))) or "No strong risk drivers entered.",
        "What Data Is Missing": "; ".join(missing),
        "Digital Twin Reasoning Summary": "The known-disease twin personalizes a known condition rather than re-diagnosing it. It explains how this profile may differ from a generic textbook case.",
    }
    row = {
        "rank": 1,
        "disease": req.disease or "Known disease",
        "disease_category": _category_from_text(req.disease),
        "real_world_causes_mechanism": panels["Known Disease Mechanism"],
        "matching_symptoms": [item["raw"] for item in normalized],
        "missing_or_unconfirmed_key_symptoms": missing,
        "patient_risk_factors_that_support_it": _risk_factor_text(req, 0.12 if req.gene else 0.0, 0.08 if req.family_history else 0.0, _lab_support(req)),
        "evidence_sources": ["Patient-entered profile", "Shared BioScale simulation", "local fallback HPO dictionary"],
        "confidence": base.confidence,
        "why_ranked_here": "Known disease mode does not re-rank diagnosis; this row carries the known condition into intervention simulation.",
        "genes": [req.gene] if req.gene else req.genes,
        "pathways": [req.pathway] if req.pathway else [],
        "intervention_categories": _intervention_categories(_category_from_text(req.disease), [req.gene] if req.gene else req.genes, ["Shared BioScale simulation"]),
        "suggested_drug_options": [],
        "intervention_note": "Simulation categories only; not treatment advice.",
    }
    base.mode = "known"
    base.normalized_symptoms = normalized
    base.safety_warnings = red_flag_warnings(req.symptoms)
    base.known_disease_panels = panels
    base.graph = _build_known_graph(req, normalized)
    base.category_distribution = _category_distribution([row])
    base.differential_diagnosis = [row]
    base.intervention_scenarios = [_scenario_from_row(row)]
    base.missing_data = missing
    base.evidence.extend([
        {"source": "Local fallback HPO dictionary", "category": "local fallback", "detail": "Normalizes typed symptoms into HPO-style phenotype terms where possible."},
        {"source": "MONDO/MedGen/Orphanet adapters", "category": "missing evidence", "detail": "Live disease ontology adapters are stubbed locally in this run."},
    ])
    base.reasoning.insert(0, "Known disease mode personalizes a known condition; it does not re-diagnose or provide treatment advice.")
    return base


def build_digital_twin(req: DigitalTwinRequest) -> DigitalTwinResult:
    bmi = req.weight_kg / max((req.height_cm / 100) ** 2, 0.1)
    age_factor = clamp((req.age - 25) / 80)
    smoking_factor = {"never": 0.0, "former": 0.08, "current": 0.18}[req.smoking]
    alcohol_factor = clamp(req.alcohol_units_week / 70) * 0.10
    activity_protection = clamp(req.exercise_minutes_week / 300) * 0.10
    bmi_factor = clamp(abs(bmi - 22.5) / 25) * 0.10
    history_factor = min(0.18, len(req.family_history) * 0.04 + len(req.known_diagnoses) * 0.05)

    baseline_risk = float(req.baseline.get("ecosystem_risk", 0.35))
    baseline_fraction = float(req.baseline.get("mutated_fraction", 0.02))
    activity = float(req.baseline.get("protein_activity", 0.5))
    repair = float(req.baseline.get("repair_capacity", 0.5))
    proliferation = float(req.baseline.get("proliferation", 0.5))
    immune = float(req.baseline.get("immune_clearance", 0.5))

    lifestyle_modifier = smoking_factor + alcohol_factor + bmi_factor - activity_protection - req.diet_quality * 0.06
    personalized_risk = clamp(baseline_risk * 0.62 + age_factor * 0.12 + history_factor + lifestyle_modifier)
    cardiovascular = clamp(age_factor * 0.30 + smoking_factor + bmi_factor + alcohol_factor - activity_protection)
    metabolic = clamp(bmi_factor * 2.2 + (1 - req.diet_quality) * 0.18 - activity_protection)
    inflammatory = clamp(personalized_risk * 0.45 + smoking_factor + _list_risk(req.medical_conditions, "inflamm"))

    lab_deviation = _lab_support(req)
    confidence = clamp(0.48 + (0.12 if req.baseline else 0) + min(0.14, len(req.laboratory_values) * 0.02)
                       + min(0.10, len(req.genes) * 0.02 + len(req.mutations) * 0.02 + len(req.variants) * 0.02))
    affected = [req.pathway or "selected molecular pathway"]
    if cardiovascular > 0.35:
        affected.append("cardiovascular regulation")
    if metabolic > 0.35:
        affected.append("metabolic homeostasis")
    if inflammatory > 0.35:
        affected.append("immune and inflammatory signaling")

    mechanisms = [
        f"{req.gene or 'entered gene'} {req.mutation or 'entered variant'} changes modeled protein activity to {activity:.2f}.",
        f"Repair capacity of {repair:.2f} and proliferation of {proliferation:.2f} shape cell persistence.",
        f"Lifestyle and history adjust the baseline ecosystem risk from {baseline_risk:.2f} to {personalized_risk:.2f}.",
    ]
    evidence = [
        {"source": "Shared BioScale simulation", "category": "computed", "detail": "Molecular and ecosystem baseline"},
        {"source": "Patient-entered profile", "category": "assumption", "detail": "Demographic and lifestyle modifiers"},
    ]
    if req.laboratory_values:
        evidence.append({"source": "Patient-entered laboratory values", "category": "user input", "detail": "Optional normalized laboratory context"})

    return DigitalTwinResult(
        mode=req.mode,
        patient_profile=_profile(req, normalize_symptoms(req.symptoms, req.normalized_symptoms)),
        normalized_symptoms=normalize_symptoms(req.symptoms, req.normalized_symptoms),
        safety_warnings=red_flag_warnings(req.symptoms),
        disease_risk_profile=[
            {"name": req.disease or "known disease", "score": round4(personalized_risk), "provenance": "computed model"},
            {"name": "cardiovascular stress", "score": round4(cardiovascular), "provenance": "profile assumption"},
            {"name": "metabolic stress", "score": round4(metabolic), "provenance": "profile assumption"},
            {"name": "inflammatory stress", "score": round4(inflammatory), "provenance": "computed model"},
        ],
        mutation_interpretation={"gene": req.gene or "unknown", "mutation": req.mutation or "unknown", "additional_genes": req.genes,
                                 "additional_mutations": req.mutations + req.variants, "interpretation": "Shared variant context applied to the patient profile when available."},
        protein_effects={"protein": req.protein or req.gene or "unknown", "remaining_activity": round4(activity), "confidence": round4(confidence)},
        pathway_effects=[{"pathway": req.pathway or "inferred pathway", "risk": round4(personalized_risk), "status": "priority pathway"}],
        cell_state={"proliferation": round4(proliferation), "repair_capacity": round4(repair),
                    "immune_clearance": round4(immune), "laboratory_deviation": round4(lab_deviation)},
        population_behaviour={"mutated_fraction": round4(baseline_fraction), "personalized_pressure": round4(personalized_risk)},
        predicted_biological_state={"overall_risk": round4(personalized_risk),
                                    "status": "higher modeled pressure" if personalized_risk >= 0.55 else "moderate modeled pressure" if personalized_risk >= 0.3 else "lower modeled pressure"},
        affected_systems=affected, potential_mechanisms=mechanisms, confidence=round4(confidence), evidence=evidence,
        reasoning=[f"Age contributes {age_factor:.2f} normalized pressure.",
                   f"Lifestyle contributes a net {lifestyle_modifier:+.2f} modifier.",
                   f"Family history and diagnoses contribute {history_factor:.2f}.", *mechanisms],
    )


def _profile(req: DigitalTwinRequest, normalized: list[dict[str, str]]) -> dict[str, Any]:
    bmi = req.weight_kg / max((req.height_cm / 100) ** 2, 0.1)
    return {
        "age": req.age,
        "sex": req.sex,
        "ethnicity": req.ethnicity or req.ancestry,
        "bmi": round4(bmi),
        "conditions": req.medical_conditions,
        "diagnoses": req.known_diagnoses,
        "medications": req.medications,
        "raw_symptoms": req.symptoms,
        "normalized_symptom_count": len(normalized),
    }


def _lab_support(req: DigitalTwinRequest) -> float:
    return round4(clamp(sum(abs(value) for value in req.laboratory_values.values()) / max(len(req.laboratory_values), 1) / 100))


def _variant_support(req: DigitalTwinRequest, row: dict[str, Any]) -> float:
    pool = " ".join(req.variants + req.mutations + req.genes).lower()
    return round4(0.8 if any(gene.lower() in pool for gene in row.get("genes", [])) else 0.0)


def _known_symptom_match(req: DigitalTwinRequest, normalized: list[dict[str, str]]) -> float:
    disease_text = req.disease.lower()
    row = next((item for item in DISEASE_LIBRARY if item["name"].lower() in disease_text or disease_text in item["name"].lower()), None)
    if not row:
        return round4(min(0.7, len(normalized) * 0.08))
    raw_terms = {item["raw"].lower() for item in normalized}
    matches = [symptom for symptom in row["symptoms"] if symptom in raw_terms]
    return round4(len(matches) / max(len(row["symptoms"]), 1))


def _category_from_text(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["cancer", "tumor", "carcinoma", "melanoma"]):
        return "oncologic"
    if any(term in lower for term in ["diabetes", "thyroid", "metabolic"]):
        return "endocrine/metabolic"
    if any(term in lower for term in ["infection", "viral", "bacterial"]):
        return "infectious"
    if any(term in lower for term in ["lupus", "arthritis", "autoimmune"]):
        return "autoimmune"
    return "known disease"


def _category_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, float] = {}
    for row in rows:
        counts[row["disease_category"]] = counts.get(row["disease_category"], 0.0) + float(row.get("confidence", 0.1))
    return {
        "name": "Disease category distribution",
        "children": [{"name": category, "value": round4(value), "type": "category"} for category, value in sorted(counts.items())],
    }


def _build_unknown_graph(normalized: list[dict[str, str]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for symptom in normalized:
        raw_id = f"symptom:{symptom['raw']}"
        hpo_id = f"hpo:{symptom['id']}"
        nodes.extend([
            {"id": raw_id, "label": symptom["raw"], "type": "symptom", "value": 0.35, "source": "user input", "description": "Raw symptom entered by the user."},
            {"id": hpo_id, "label": symptom["label"], "type": "HPO-style phenotype", "value": 0.45, "source": symptom["source"], "description": f"Normalized phenotype term {symptom['id']}."},
        ])
        links.append({"source": raw_id, "target": hpo_id, "relation": "normalizes to", "weight": 0.7})
    for row in rows:
        disease_id = f"disease:{row['disease']}"
        nodes.append({"id": disease_id, "label": row["disease"], "type": row["disease_category"], "value": row["confidence"], "source": ", ".join(row["evidence_sources"]), "description": row["real_world_causes_mechanism"]})
        for symptom in row["matching_symptoms"]:
            links.append({"source": f"hpo:{LOCAL_PHENOTYPES.get(symptom, {'id': symptom})['id']}", "target": disease_id, "relation": "matches", "weight": row["confidence"]})
        for gene in row.get("genes", [])[:2]:
            gene_id = f"gene:{gene}"
            nodes.append({"id": gene_id, "label": gene, "type": "gene", "value": 0.35, "source": "local fallback mechanism", "description": f"{gene} is listed as a relevant gene or pathway-context marker for this candidate."})
            links.append({"source": disease_id, "target": gene_id, "relation": "may involve", "weight": 0.45})
    unique_nodes = {node["id"]: node for node in nodes}
    return {"nodes": list(unique_nodes.values()), "links": links}


def _build_known_graph(req: DigitalTwinRequest, normalized: list[dict[str, str]]) -> dict[str, Any]:
    disease_id = f"disease:{req.disease or 'known disease'}"
    nodes = [{"id": disease_id, "label": req.disease or "Known disease", "type": "known disease", "value": 0.7, "source": "user input", "description": "Known condition being personalized, not re-diagnosed."}]
    links: list[dict[str, Any]] = []
    for symptom in normalized:
        node_id = f"hpo:{symptom['id']}"
        nodes.append({"id": node_id, "label": symptom["label"], "type": "HPO-style phenotype", "value": 0.45, "source": symptom["source"], "description": f"Patient phenotype term from {symptom['raw']}."})
        links.append({"source": node_id, "target": disease_id, "relation": "patient feature", "weight": 0.55})
    if req.gene:
        nodes.append({"id": f"gene:{req.gene}", "label": req.gene, "type": "gene", "value": 0.5, "source": "user input/BioScale", "description": "Selected gene or variant context for the known disease twin."})
        links.append({"source": disease_id, "target": f"gene:{req.gene}", "relation": "mechanistic context", "weight": 0.65})
    if req.pathway:
        nodes.append({"id": f"pathway:{req.pathway}", "label": req.pathway, "type": "pathway", "value": 0.5, "source": "BioScale", "description": "Selected or inferred pathway burden."})
        links.append({"source": disease_id, "target": f"pathway:{req.pathway}", "relation": "affects", "weight": 0.55})
    return {"nodes": nodes, "links": links}


def _scenario_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_disease": row["disease"],
        "disease_category": row["disease_category"],
        "matching_symptoms": row.get("matching_symptoms", []),
        "suspected_mechanisms": [row["real_world_causes_mechanism"]],
        "relevant_genes": row.get("genes", []),
        "relevant_pathways": row.get("pathways", []),
        "evidence_sources": row.get("evidence_sources", []),
        "confidence_score": row.get("confidence", 0.0),
        "suggested_intervention_categories": row.get("intervention_categories", []),
        "suggested_drug_options": row.get("suggested_drug_options", []),
        "note": row.get("intervention_note", "Simulation categories only; not treatment advice."),
    }
