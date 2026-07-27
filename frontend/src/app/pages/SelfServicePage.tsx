import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Calendar, Leaf, MapPin, IdCard } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/layout/PageContainer';
import { Skeleton } from '../../components/layout/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';
import { useAuthContext } from '../../auth/hooks/useAuthContext';
import { useMyLeaveBalances, useMyLeaveRequests } from '../../api/hooks/useEmployeeSelfService';
import { useRequests } from '../../api/hooks/useRequests';
import { RequestSummaryCard } from '../../components/request/RequestSummaryCard';
import { formatDate } from '../../lib/formatters';
import type { LeaveBalanceResponse, LeaveRequestResponse } from '../../api/types';

type Tab = 'overview' | 'leave' | 'requests';

export function SelfServicePage() {
  const { user } = useAuthContext();
  const [tab, setTab] = useState<Tab>('overview');
  if (!user) return null;
  const externalUser = user.actor_type === 'external_user';

  return (
    <PageContainer>
      <PageHeader title="My Workplace" description="View your information, leave balances, and requests" />

      <div className="mb-4 flex gap-1 border-b border-neutral-200 dark:border-neutral-800">
        <TabButton label="Overview" active={tab === 'overview'} onClick={() => setTab('overview')} />
        {!externalUser && <TabButton label="Leave" active={tab === 'leave'} onClick={() => setTab('leave')} />}
        <TabButton label="My Requests" active={tab === 'requests'} onClick={() => setTab('requests')} />
      </div>

      {tab === 'overview' && <OverviewTab user={user} />}
      {tab === 'leave' && !externalUser && <LeaveTab />}
      {tab === 'requests' && <RequestsTab />}
    </PageContainer>
  );
}

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
        active
          ? 'border-primary-500 text-primary-600 dark:border-primary-400 dark:text-primary-400'
          : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-300'
      }`}
    >
      {label}
    </button>
  );
}

/* ================= Overview ================= */
function OverviewTab({ user }: { user: { email: string; actor_type: string; employee_id: string | null; department_id: string | null } }) {
  const { data: requests, isLoading } = useRequests({ limit: 10 });
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
              <User size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Personal Info</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">{user.email}</p>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success-100 text-success-600 dark:bg-success-900 dark:text-success-300">
              <IdCard size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Role</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 capitalize">{user.actor_type.replace(/_/g, ' ')}</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="mb-3 text-sm font-semibold text-neutral-800 dark:text-neutral-200">Recent Requests</h3>
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : !requests || requests.length === 0 ? (
          <EmptyState title="No requests yet" description="Submit your first request through the Assistant or New Request page." />
        ) : (
          <div className="space-y-3">
            {requests.slice(0, 4).map((req) => (
              <RequestSummaryCard key={req.id} request={req} onClick={() => navigate(`/app/requests/${req.id}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ================= Leave ================= */
function LeaveTab() {
  const { data: balances, isLoading: bLoading } = useMyLeaveBalances();
  const { data: leaveRequests, isLoading: rLoading } = useMyLeaveRequests();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-3 text-sm font-semibold text-neutral-800 dark:text-neutral-200">Leave Balances</h3>
        {bLoading ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </div>
        ) : !balances || balances.length === 0 ? (
          <EmptyState title="No leave balances" description="Your leave balances will appear after onboarding." />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {balances.map((b) => (
              <LeaveBalanceCard key={b.id} balance={b} />
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-3 text-sm font-semibold text-neutral-800 dark:text-neutral-200">Leave Requests</h3>
        {rLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : !leaveRequests || leaveRequests.length === 0 ? (
          <EmptyState title="No leave requests" description="You have not submitted any leave requests yet." />
        ) : (
          <div className="space-y-3">
            {leaveRequests.map((lr) => (
              <LeaveRequestItem key={lr.request_id} request={lr} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function LeaveBalanceCard({ balance }: { balance: LeaveBalanceResponse }) {
  const remaining = Number(balance.remaining_days);
  const allocated = Number(balance.allocated_days);
  const used = Number(balance.used_days);
  const pct = allocated > 0 ? Math.round((used / allocated) * 100) : 0;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
      <div className="mb-2 flex items-center gap-2">
        <Leaf size={16} className="text-success-500" />
        <p className="text-sm font-semibold capitalize text-neutral-800 dark:text-neutral-200">{balance.leave_type.replace(/_/g, ' ')}</p>
      </div>
      <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{remaining} <span className="text-sm font-normal text-neutral-500">days</span></p>
      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Used: {used} / {allocated}</p>
      <div className="mt-2 h-2 w-full rounded-full bg-neutral-100 dark:bg-neutral-700">
        <div
          className="h-2 rounded-full bg-success-500 transition-all"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

function LeaveRequestItem({ request }: { request: LeaveRequestResponse }) {
  const colorMap: Record<string, string> = {
    approved: 'bg-success-50 text-success-700 dark:bg-success-900/20 dark:text-success-300',
    rejected: 'bg-danger-50 text-danger-700 dark:bg-danger-900/20 dark:text-danger-300',
    pending: 'bg-warning-50 text-warning-700 dark:bg-warning-900/20 dark:text-warning-300',
  };
  const decisionLabel = request.decision.toLowerCase();
  const chip = colorMap[decisionLabel] || colorMap.pending;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-800">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {request.leave_type.replace(/_/g, ' ')} leave
          </p>
          <div className="mt-1 flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
            <span className="inline-flex items-center gap-1">
              <Calendar size={12} />
              {formatDate(request.start_date)} — {formatDate(request.end_date)}
            </span>
            <span className="inline-flex items-center gap-1">
              <MapPin size={12} />
              {request.requested_days} days
            </span>
          </div>
        </div>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${chip}`}>{decisionLabel}</span>
      </div>
      {request.approval_required && (
        <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
          Approval status: <span className="font-medium capitalize">{request.approval_status.replace(/_/g, ' ')}</span>
        </div>
      )}
    </div>
  );
}

/* ================= My Requests ================= */
function RequestsTab() {
  const { data: requests, isLoading } = useRequests({ limit: 50 });
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (!requests || requests.length === 0) {
    return <EmptyState title="No requests" description="Requests you submit through the Assistant or New Request page will appear here." />;
  }

  return (
    <div className="space-y-3">
      {requests.map((req) => (
        <RequestSummaryCard key={req.id} request={req} onClick={() => navigate(`/app/requests/${req.id}`)} />
      ))}
    </div>
  );
}
