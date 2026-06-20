import { useId } from "react";
import type { PanelHelp, TooltipHelp } from "./helpContent";

type PanelHelpAccordionProps = {
  help: PanelHelp;
};

type InfoTooltipProps = {
  label: string;
  help: TooltipHelp;
};

export function PanelHelpAccordion({ help }: PanelHelpAccordionProps) {
  return (
    <details className="panelHelpAccordion">
      <summary>
        <span className="helpIcon" aria-hidden="true">?</span>
        <span>Help</span>
      </summary>
      <div className="panelHelpBody">
        <p className="panelHelpSummary">{help.summary}</p>
        {help.details.length > 0 && (
          <ul className="panelHelpList">
            {help.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}

export function InfoTooltip({ label, help }: InfoTooltipProps) {
  const tooltipId = useId();
  return (
    <span className="infoTooltip" tabIndex={0} aria-describedby={tooltipId}>
      <span className="helpIcon infoIcon" aria-hidden="true">i</span>
      <span className="infoTooltipBubble" role="tooltip" id={tooltipId}>
        <strong>{help.title ?? label}</strong>
        <span>{help.summary}</span>
        {help.details.length > 0 && (
          <span className="infoTooltipDetails">
            {help.details.map((detail) => (
              <span key={detail}>{detail}</span>
            ))}
          </span>
        )}
        {help.examples.length > 0 && (
          <span className="infoTooltipExamples">
            Examples: {help.examples.join(", ")}
          </span>
        )}
      </span>
    </span>
  );
}
