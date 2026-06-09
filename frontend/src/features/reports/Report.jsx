import { ItemReport } from './ItemReport'
import { OperationReport } from './OperationReport'
import { PlanReport } from './PlanReport'
import { SimReport } from './SimReport'
import { SnsReport } from './SnsReport'
import { SupportReport } from './SupportReport'

export const Report = ({ id, data, go }) => {
  if (id === 'item') return <ItemReport data={data} go={go} />
  if (id === 'simulator') return <SimReport data={data} />
  if (id === 'support') return <SupportReport data={data} go={go} />
  if (id === 'plan') return <PlanReport data={data} />
  if (id === 'operation') return <OperationReport data={data} go={go} />
  return <SnsReport data={data} />
}
