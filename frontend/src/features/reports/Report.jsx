import { ItemReport } from './ItemReport'
import { OperationReport } from './OperationReport'
import { PlanReport } from './PlanReport'
import { SimReport } from './SimReport'
import { SnsReport } from './SnsReport'
import { SupportReport } from './SupportReport'

export const Report = ({
  id,
  data,
  setData,
  go,
  workspace,
  setWorkspace,
  onCreateWorkspace,
  selectedIdeaRank,
  onSelectIdea,
  selectedSupportTitle,
  onSelectSupport,
  selectedOperationSuggestionTitle,
  onSelectOperationSuggestion,
  supportSearchMode,
  onChangeSupportSearchMode,
  supportUserGoal,
  onChangeSupportUserGoal,
  supportRegionBasis,
  onChangeSupportRegionBasis,
  supportSearchLoading,
  supportHasSearched,
  onRunSupportSearch,
  savedSupportPrograms,
  onSaveSupportProgram,
  onDeleteSavedSupportProgram,
  focusedSectionTitle,
  onFocusSection,
  planGoal,
  onChangePlanGoal,
  announcement,
  onSubmitAnnouncement,
  announcementLoading,
  applicationForm,
  onRequestOperationFeedback,
  operationFeedbackSaving,
  onCampaignControlChange,
}) => {
  if (id === 'item') {
    return (
      <ItemReport
        data={data}
        go={go}
        workspace={workspace}
        setWorkspace={setWorkspace}
        onCreateWorkspace={onCreateWorkspace}
        selectedIdeaRank={selectedIdeaRank}
        onSelectIdea={onSelectIdea}
      />
    )
  }
  if (id === 'simulator') return <SimReport data={data} />
  if (id === 'support') {
    return (
      <SupportReport
        data={data}
        go={go}
        selectedSupportTitle={selectedSupportTitle}
        onSelectSupport={onSelectSupport}
        supportSearchMode={supportSearchMode}
        onChangeSupportSearchMode={onChangeSupportSearchMode}
        supportUserGoal={supportUserGoal}
        onChangeSupportUserGoal={onChangeSupportUserGoal}
        supportRegionBasis={supportRegionBasis}
        onChangeSupportRegionBasis={onChangeSupportRegionBasis}
        supportSearchLoading={supportSearchLoading}
        supportHasSearched={supportHasSearched}
        onRunSupportSearch={onRunSupportSearch}
        savedSupportPrograms={savedSupportPrograms}
        onSaveSupportProgram={onSaveSupportProgram}
        onDeleteSavedSupportProgram={onDeleteSavedSupportProgram}
      />
    )
  }
  if (id === 'plan') {
    return (
      <PlanReport
        data={data}
        focusedSectionTitle={focusedSectionTitle}
        onFocusSection={onFocusSection}
        planGoal={planGoal}
        onChangePlanGoal={onChangePlanGoal}
        announcement={announcement}
        onSubmitAnnouncement={onSubmitAnnouncement}
        announcementLoading={announcementLoading}
        applicationForm={applicationForm}
      />
    )
  }
  if (id === 'operation') {
    return (
      <OperationReport
        data={data}
        setData={setData}
        go={go}
        selectedOperationSuggestionTitle={selectedOperationSuggestionTitle}
        onSelectOperationSuggestion={onSelectOperationSuggestion}
        onRequestOperationFeedback={onRequestOperationFeedback}
        operationFeedbackSaving={operationFeedbackSaving}
      />
    )
  }
  return <SnsReport data={data} setData={setData} onCampaignControlChange={onCampaignControlChange} />
}
