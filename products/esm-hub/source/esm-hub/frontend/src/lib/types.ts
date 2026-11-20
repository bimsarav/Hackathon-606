export interface Page<T> { items: T[]; total: number; page: number; size: number }

export interface Me { userId: number; companyId: number; name: string; email: string; roles: string[]; teamIds: number[] }

export interface Comment { id: number; authorId: number; authorName: string; body: string; internal: boolean; createdAt: string }
export interface Worklog { id: number; userId: number; userName: string; minutesSpent: number; workDescription: string; loggedAt: string }
export interface TicketEvent { eventType: string; fromValue?: string | null; toValue?: string | null; actorId?: number | null; occurredAt: string }
export interface ProblemRef { id: number; problemNo: string; title: string; status: string; knownError: boolean; workaround?: string }

export interface Incident {
  id: number; ticketNo: string; title: string; status: string; priority: string; priorityId: number; channel?: string
  serviceId?: number; assetId?: number; requesterId: number; requesterName?: string
  assignedTeamId?: number; teamName?: string; assignedUserId?: number; assigneeName?: string
  createdAt: string; updatedAt?: string; firstResponseAt?: string; resolvedAt?: string; closedAt?: string
  responseDueAt?: string; dueAt?: string; slaPaused: boolean; responseBreached: boolean; resolutionBreached: boolean
  reopenedCount: number; satisfactionScore?: number
  description?: string; resolutionCode?: string; resolutionNotes?: string
  comments?: Comment[]; worklogs?: Worklog[]; events?: TicketEvent[]; problems?: ProblemRef[]
  allowedTransitions?: string[]; canWork?: boolean
}

export interface IncidentRef { id: number; ticketNo: string; title: string; status: string; priority: string; createdAt: string }
export interface Problem {
  id: number; problemNo: string; title: string; description?: string; status: string; rootCause?: string; workaround?: string
  knownError: boolean; ownerTeamId?: number; createdAt: string; updatedAt?: string; incidentCount: number; incidents?: IncidentRef[]
}

export interface Office { officeId: number; name: string; city: string; country: string; timezone: string }
export interface Department { departmentId: number; name: string; costCentre?: string }
export interface Team { teamId: number; name: string; supportLevel: number; managerUserId?: number; active: boolean; memberIds: number[] }
export interface Category { categoryId: number; name: string; parentId?: number }
export interface ServiceRef { serviceId: number; name: string; description?: string; categoryId?: number; owningTeamId?: number; active: boolean }
export interface Reference { offices: Office[]; departments: Department[]; teams: Team[]; categories: Category[]; services: ServiceRef[]; roles: string[] }
export interface Member { userId: number; name: string; email: string; roles: string[] }
export interface UserView {
  userId: number; employeeNo: string; firstName: string; lastName: string; email: string; officeId?: number; departmentId?: number
  managerId?: number; employmentStatus: string; roles: string[]; teamIds: number[]
}

export interface Step { stepOrder: number; approverType: string; approverRole?: string; minCost?: number }
export interface CatalogueItem {
  itemId: number; serviceId: number; serviceName: string; name: string; description?: string; baseCost?: number
  fulfilmentTeamId?: number; active: boolean; steps?: Step[]
}
export interface ApprovalRow {
  approvalId: number; requestId?: number; changeId?: number; reference: string; title: string; stepOrder: number
  approverId?: number; approverRole?: string; decision?: string; comments?: string; createdAt?: string; decidedAt?: string
  changeType?: string; riskLevel?: string
}
export interface ServiceRequest {
  requestId: number; requestNo: string; title: string; details?: string; status: string; requesterId: number; requesterName?: string
  serviceId?: number; itemId?: number; estimatedCost?: number; assignedTeamId?: number; assignedUserId?: number
  requestedAt: string; approvedAt?: string; fulfilledAt?: string; approvals?: ApprovalRow[]; canFulfil: boolean
}

export interface Change {
  changeId: number; changeNo: string; title: string; description?: string; changeType: string; status: string
  riskLevel?: string; impact?: string; requesterId: number; requesterName?: string; ownerTeamId?: number
  plannedStart?: string; plannedEnd?: string; actualStart?: string; actualEnd?: string; rollbackPlan?: string
  createdAt: string; planLocked: boolean; assessmentComplete: boolean; missingAssessment?: string[]
  approvals?: ApprovalRow[]; canEdit: boolean; canImplement: boolean
}
export interface CalendarEntry {
  changeId: number; changeNo: string; title: string; changeType: string; status: string; riskLevel?: string
  ownerTeamId?: number; plannedStart?: string; plannedEnd?: string; collidesWith?: number[]
}

export interface HistoryEntry { userId: number; userName: string; assignedAt: string; returnedAt?: string; assignedBy?: number }
export interface Asset {
  assetId: number; assetTag: string; assetType: string; manufacturer?: string; model?: string; serialNumber?: string
  purchaseDate?: string; warrantyEnd?: string; officeId?: number; purchaseCost?: number; status: string
  assignedUserId?: number; assignedUserName?: string; warrantyState?: string; createdAt: string; history?: HistoryEntry[]
}

export interface Article {
  articleId: number; title: string; body?: string; snippet?: string; categoryId?: number; authorId?: number; authorName?: string
  status: string; viewCount: number; helpfulCount: number; notHelpfulCount: number; publishedAt?: string; updatedAt?: string
}

export interface Notification {
  id: number; channel: string; subject: string; body?: string; link?: string; reference?: string
  entityType?: string; entityId?: string; deliveryStatus: string; createdAt: string; sentAt?: string; readAt?: string
}

export interface AuditEntry {
  auditId: number; service: string; actorUserId?: number; entityType: string; entityId: string; action: string
  oldValues?: unknown; newValues?: unknown; sourceIp?: string; correlationId?: string; occurredAt: string
}

export interface SlaPolicy {
  id: number; name: string; priorityId: number; serviceId?: number; businessHoursOnly: boolean
  responseTargetMinutes: number; resolutionTargetMinutes: number; effectiveFrom: string; effectiveTo?: string; version: number
}
export interface Calendar { id: number; name: string; timezone: string; hours: { weekday: number; startTime: string; endTime: string }[]; holidays?: { holidayDate: string; name: string }[] }
export interface Rule { id: number; serviceId?: number; priorityId?: number; teamId: number; sortOrder: number; active: boolean }
export interface Priority { id: number; name: string; responseMinutes: number; resolutionMinutes: number }
