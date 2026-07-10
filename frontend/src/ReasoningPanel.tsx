import type { BiologicalReasoning } from "./types";
import { SimulatorPanel } from "./SimulatorUI";
import { InfoTooltip } from "./Help";

export function ReasoningPanel({ reasoning }: { reasoning: BiologicalReasoning }) {
  return <SimulatorPanel title="Biological Reasoning Engine" eyebrow="Why these changes occur">
    <div className="reasoningChain">
      {reasoning.steps.map((step, index) => <div className="reasoningStep" key={step.layer}>
        <div className="reasoningStepHeader">
          <span>{index + 1}</span>
          <h3>{step.layer}</h3>
          <b>
            {Math.round(step.confidence * 100)}% confidence
            <InfoTooltip
              label={`${step.layer} confidence`}
              help={{
                title: `${step.layer} confidence`,
                summary: `This confidence is ${(step.confidence * 100).toFixed(0)}% for this reasoning step.`,
                details: [
                  "It reflects evidence availability, mutation confidence, and how directly this layer is connected to upstream outputs.",
                  `For this layer, the model used provenance from ${step.provenance}.`,
                ],
                examples: [],
              }}
            />
          </b>
        </div>
        <dl><div><dt>Evidence</dt><dd>{step.evidence}</dd></div><div><dt>Reasoning</dt><dd>{step.reasoning}</dd></div><div><dt>Downstream consequence</dt><dd>{step.consequence}</dd></div></dl>
        <small>Provenance: {step.provenance}</small>
      </div>)}
    </div>
    <div className="causalGraph" aria-label="Biological causal graph">{reasoning.causal_graph.nodes.map((node, index) => <div className="causalGraphItem" key={node.id}><div><b>{node.label}</b><span>{Math.round(node.confidence * 100)}%</span></div>{index < reasoning.causal_graph.nodes.length - 1 && <span className="causalArrow">→</span>}</div>)}</div>
  </SimulatorPanel>;
}
