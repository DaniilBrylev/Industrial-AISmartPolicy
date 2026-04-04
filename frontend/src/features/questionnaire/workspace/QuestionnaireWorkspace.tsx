import type { ReactNode } from "react";
import { WORKSPACE_TABS, type WorkspaceTabId } from "./tabs";
import { WorkspaceHeader } from "./WorkspaceHeader";
import type { QuestionnaireRead, QuestionnaireWorkflowStateRead } from "@/shared/api/types";

type Props = {
  tab: WorkspaceTabId;
  onTabChange: (t: WorkspaceTabId) => void;
  questionnaire: QuestionnaireRead;
  departmentLabel: string;
  workflowState: QuestionnaireWorkflowStateRead | null;
  analysisStale: boolean;
  llmEnabledGlobally: boolean | null;
  lastAnalysisUsedLlm: boolean;
  busy: boolean;
  canEditResponses: boolean;
  onSave: () => void;
  onValidate: () => void;
  onAnalyze: () => void;
  onOpenDiff: () => void;
  onGeneratePolicy: () => void;
  onDownloadDocx: () => void;
  diffLoading: boolean;
  panels: Record<WorkspaceTabId, ReactNode>;
};

export function QuestionnaireWorkspace({
  tab,
  onTabChange,
  questionnaire,
  departmentLabel,
  workflowState,
  analysisStale,
  llmEnabledGlobally,
  lastAnalysisUsedLlm,
  busy,
  canEditResponses,
  onSave,
  onValidate,
  onAnalyze,
  onOpenDiff,
  onGeneratePolicy,
  onDownloadDocx,
  diffLoading,
  panels,
}: Props) {
  return (
    <>
      <WorkspaceHeader
        questionnaire={questionnaire}
        departmentLabel={departmentLabel}
        workflowState={workflowState}
        analysisStale={analysisStale}
        llmEnabledGlobally={llmEnabledGlobally}
        lastAnalysisUsedLlm={lastAnalysisUsedLlm}
        busy={busy}
        canEditResponses={canEditResponses}
        onSave={onSave}
        onValidate={onValidate}
        onAnalyze={onAnalyze}
        onOpenDiff={onOpenDiff}
        onGeneratePolicy={onGeneratePolicy}
        onDownloadDocx={onDownloadDocx}
        diffLoading={diffLoading}
      />
      <nav className="tabBar" aria-label="Разделы анкеты">
        {WORKSPACE_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tabBtn ${tab === t.id ? "tabBtnActive" : ""}`}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <div className="workspaceTabPanel">{panels[tab]}</div>
    </>
  );
}
